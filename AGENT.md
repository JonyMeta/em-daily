# EM Daily — instructions for the daily run

You are curating a daily digest of new emergency medicine papers for a practicing
emergency physician. Her local app (Maggie's Planner) downloads data/digest.json from this
repo every hour; your job is to add today's entry and push it. Everything is in English.
Keep the JSON format exactly as publish.py writes it — the app depends on it.

## Steps
1. From the repo root: `python3 scripts/fetch_candidates.py --days 3`
   - It queries PubMed, drops PMIDs already in data/seen.json, and writes candidates.json
     sorted by a rough heuristic score. If PubMed fails, retry once after 60 s; if it still
     fails, stop without committing anything.
2. Read candidates.json (titles + abstracts). Choose **up to 5** papers, best first.
   Selection criteria, in order:
   - Would this change or sharpen what an EM physician does on shift? (diagnosis, treatment,
     disposition, procedures, resuscitation). Practice relevance beats prestige.
   - Strength of design: RCT > meta-analysis / systematic review > guideline / consensus >
     large multicenter cohort or diagnostic-accuracy study > everything else.
   - Breadth: avoid more than 2 papers on the same topic in one day.
   - Exclude: ICU-only or ward-only care with no ED decision, residency/match/education
     logistics, pure simulation studies, animal or bench studies, narrow single-center
     audits, protocols with no results.
   - The heuristic score is a hint, not a ranking. Override it freely.
   - If fewer than 5 papers qualify, publish fewer. Never pad. If none qualify, stop without
     committing (the same candidates are reconsidered tomorrow).
3. Write picks.json, e.g.
   `[{"pmid": "43019972", "topic": "Analgesia & Sedation"}, ...]`
   Allowed topics: Resuscitation, Cardiology, Neurology, Trauma, Sepsis & Infection,
   Airway & Respiratory, Toxicology, Pediatrics, Analgesia & Sedation, Ultrasound,
   Prehospital & EMS, Diagnostics, ED Operations, Geriatrics, Obstetrics, Psychiatry, Other.
   Optionally add "study_type" to correct the automatic label (e.g. "RCT (pilot)").
   Then run `python3 scripts/publish.py picks.json --date <today in Asia/Jerusalem, YYYY-MM-DD>`.
   publish.py refuses any PMID that PubMed did not return — never invent or edit titles.
4. Commit only data/digest.json and data/seen.json with message
   `Digest YYYY-MM-DD (N papers)` and push to the default branch (main).
   Do not commit candidates.json or picks.json.
