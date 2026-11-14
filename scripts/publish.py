#!/usr/bin/env python3
"""Publish today's picks into data/digest.json and mark all reviewed candidates as seen.

Usage:
  python3 scripts/publish.py picks.json [--date YYYY-MM-DD]

picks.json is a list (max 5) of objects: {"pmid": "...", "topic": "...", "study_type": "..."}
("study_type" optional — overrides the automatic label). Every PMID must exist in
candidates.json: nothing can be published that PubMed did not return.
"""
import argparse, datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS = {"Resuscitation", "Cardiology", "Neurology", "Trauma", "Sepsis & Infection", "Airway & Respiratory",
          "Toxicology", "Pediatrics", "Analgesia & Sedation", "Ultrasound", "Prehospital & EMS",
          "Diagnostics", "ED Operations", "Geriatrics", "Obstetrics", "Psychiatry", "Other"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("picks")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()

    cand = json.load(open(os.path.join(ROOT, "candidates.json")))["candidates"]
    by_id = {a["pmid"]: a for a in cand}
    picks = json.load(open(args.picks))
    if not 1 <= len(picks) <= 5:
        sys.exit("picks must contain 1-5 articles")

    articles = []
    for p in picks:
        a = by_id.get(str(p["pmid"]))
        if a is None:
            sys.exit(f"PMID {p['pmid']} is not in candidates.json - refusing to publish it")
        if p.get("topic") not in TOPICS:
            sys.exit(f"topic for {p['pmid']} must be one of: {sorted(TOPICS)}")
        articles.append(dict(pmid=a["pmid"], title=a["title"].rstrip("."), journal=a["journal"],
                             journal_full=a["journal_full"], study_type=p.get("study_type") or a["study_type"],
                             topic=p["topic"], doi=a["doi"], url=a["url"]))

    dpath = os.path.join(ROOT, "data", "digest.json")
    digest = json.load(open(dpath)) if os.path.exists(dpath) else {"days": []}
    digest["days"] = [d for d in digest["days"] if d["date"] != args.date]
    digest["days"].insert(0, dict(date=args.date, reviewed=len(cand), articles=articles))
    digest["days"].sort(key=lambda d: d["date"], reverse=True)
    digest["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    json.dump(digest, open(dpath, "w"), indent=1, ensure_ascii=False)

    spath = os.path.join(ROOT, "data", "seen.json")
    seen = set(json.load(open(spath))) if os.path.exists(spath) else set()
    seen |= set(by_id)
    json.dump(sorted(seen), open(spath, "w"))
    print(f"Published {len(articles)} articles for {args.date}; {len(seen)} PMIDs marked as seen.")


if __name__ == "__main__":
    main()
