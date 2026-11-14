#!/usr/bin/env python3
"""Fetch recent emergency-medicine candidate articles from PubMed (E-utilities).

Usage: python3 scripts/fetch_candidates.py [--days 3] [--out candidates.json]

Why journal-based and keyword-based instead of MeSH: brand-new PubMed records
have no MeSH terms yet (indexing lags weeks), so a MeSH query misses exactly
the newest papers. We query (a) everything new in core EM journals and
(b) EM-relevant title/abstract hits in high-impact general/adjacent journals.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE_EM = [
    "Ann Emerg Med", "Acad Emerg Med", "Emerg Med J", "Resuscitation", "Resusc Plus",
    "Am J Emerg Med", "J Emerg Med", "J Am Coll Emerg Physicians Open", "West J Emerg Med",
    "Eur J Emerg Med", "Scand J Trauma Resusc Emerg Med", "Emerg Med Australas", "CJEM",
    "Prehosp Emerg Care", "Pediatr Emerg Care", "BMC Emerg Med", "Intern Emerg Med",
    "Clin Toxicol (Phila)", "J Trauma Acute Care Surg", "Injury", "Air Med J",
]
HIGH_IMPACT = [
    "N Engl J Med", "JAMA", "Lancet", "BMJ", "JAMA Intern Med", "JAMA Netw Open",
    "Ann Intern Med", "Intensive Care Med", "Crit Care Med", "Crit Care", "Circulation",
    "Stroke", "Chest", "Am J Respir Crit Care Med", "Lancet Respir Med", "JAMA Pediatr",
    "Pediatrics", "Eur Heart J", "J Am Coll Cardiol", "Neurology", "Br J Anaesth",
]
EM_TERMS = [
    "emergency department*", "emergency medicine", "prehospital", "pre-hospital",
    "out-of-hospital cardiac arrest", "emergency medical services", "paramedic*",
    "resuscitation", "trauma", "triage", "sepsis", "septic shock", "intubation",
    "acute chest pain", "pulmonary embolism", "anaphylaxis", "overdose", "poisoning",
]
EXCLUDE_PT = ["Case Reports", "Editorial", "Letter", "Comment", "News", "Erratum",
              "Published Erratum", "Retraction of Publication", "Biography", "Interview"]

STRONG_PT = {
    "Randomized Controlled Trial": 6, "Meta-Analysis": 5, "Practice Guideline": 5,
    "Guideline": 5, "Systematic Review": 4, "Multicenter Study": 2,
    "Clinical Trial": 3, "Comparative Study": 1, "Observational Study": 1,
}
TITLE_SIGNALS = [
    (r"randomi[sz]ed|\btrial\b", 5), (r"meta-analys|systematic review", 4),
    (r"guideline|consensus|recommendation", 3), (r"multicent|nationwide|cohort", 1),
    (r"diagnostic accuracy|validation", 1),
]
TIER = {j: 3 for j in ["N Engl J Med", "JAMA", "Lancet", "BMJ"]}
TIER.update({j: 2 for j in ["Ann Emerg Med", "Acad Emerg Med", "Emerg Med J", "Resuscitation",
                             "JAMA Intern Med", "Ann Intern Med", "Intensive Care Med",
                             "Crit Care Med", "JAMA Netw Open", "Lancet Respir Med"]})


def call(endpoint, params, retries=3):
    data = urllib.parse.urlencode(params).encode()
    for i in range(retries):
        try:
            with urllib.request.urlopen(EUTILS + endpoint, data=data, timeout=60) as r:
                return r.read()
        except Exception as e:  # network hiccup or 429
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def build_query():
    ta = lambda js: "(" + " OR ".join(f'"{j}"[ta]' for j in js) + ")"
    tiab = "(" + " OR ".join(f'"{t}"[tiab]' if "*" not in t else f"{t}[tiab]" for t in EM_TERMS) + ")"
    excl = " OR ".join(f'"{p}"[pt]' for p in EXCLUDE_PT)
    return f"({ta(CORE_EM)} OR ({ta(HIGH_IMPACT)} AND {tiab})) NOT ({excl}) AND english[la] AND hasabstract"


def text(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def parse(xml_bytes):
    out = []
    for art in ET.fromstring(xml_bytes).iter("PubmedArticle"):
        mc = art.find("MedlineCitation")
        pmid = text(mc.find("PMID"))
        a = mc.find("Article")
        title = re.sub(r"\s+", " ", text(a.find("ArticleTitle")))
        journal = text(a.find("Journal/ISOAbbreviation")) or text(a.find("Journal/Title"))
        jfull = text(a.find("Journal/Title"))
        pts = [text(p) for p in a.findall("PublicationTypeList/PublicationType")]
        abstract = " ".join(text(x) for x in a.findall("Abstract/AbstractText"))
        doi = ""
        for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = text(aid)
        out.append(dict(pmid=pmid, title=title, journal=journal, journal_full=jfull,
                        pub_types=pts, doi=doi, abstract=abstract[:1500],
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"))
    return out


def score(a):
    s = max([STRONG_PT.get(p, 0) for p in a["pub_types"]] + [0])
    for pat, w in TITLE_SIGNALS:
        if re.search(pat, a["title"], re.I):
            s = max(s, w)
    return s + TIER.get(a["journal"], 0)


def study_type(a):
    pts, t = a["pub_types"], a["title"].lower()
    if "Meta-Analysis" in pts or "meta-analys" in t: return "Meta-analysis"
    if "Systematic Review" in pts or "systematic review" in t: return "Systematic review"
    if "Randomized Controlled Trial" in pts or re.search(r"randomi[sz]ed", t): return "RCT"
    if any(p in pts for p in ("Practice Guideline", "Guideline")) or "guideline" in t: return "Guideline"
    if "Clinical Trial" in pts or re.search(r"\btrial\b", t): return "Clinical trial"
    if re.search(r"cohort", t): return "Cohort study"
    if "Review" in pts or re.search(r"\breview\b", t): return "Review"
    if re.search(r"diagnostic accuracy|validation", t): return "Diagnostic study"
    return "Original research"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--out", default=os.path.join(ROOT, "candidates.json"))
    ap.add_argument("--max", type=int, default=400)
    args = ap.parse_args()

    seen_path = os.path.join(ROOT, "data", "seen.json")
    seen = set(json.load(open(seen_path))) if os.path.exists(seen_path) else set()

    res = json.loads(call("esearch.fcgi", dict(db="pubmed", term=build_query(), datetype="edat",
                                                reldate=args.days, retmax=args.max, retmode="json")))
    ids = [i for i in res["esearchresult"]["idlist"] if i not in seen]
    arts = []
    for k in range(0, len(ids), 150):
        arts += parse(call("efetch.fcgi", dict(db="pubmed", id=",".join(ids[k:k + 150]), retmode="xml")))
        time.sleep(0.4)
    for a in arts:
        a["score"], a["study_type"] = score(a), study_type(a)
    arts.sort(key=lambda a: -a["score"])
    json.dump(dict(total_found=int(res["esearchresult"]["count"]), new_after_dedup=len(arts),
                   candidates=arts), open(args.out, "w"), indent=1)
    print(f"PubMed hits: {res['esearchresult']['count']} | new (not yet published): {len(arts)} -> {args.out}")
    for a in arts[:40]:
        print(f"{a['score']:>2} | {a['pmid']} | {a['study_type']:<17} | {a['journal'][:22]:<22} | {a['title'][:110]}")


if __name__ == "__main__":
    sys.exit(main())
