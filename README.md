# EM Daily

Five new emergency medicine papers, picked every morning (Asia/Jerusalem) by a scheduled agent.

- `data/digest.json` — the published digest, read by Maggie's Planner:
  https://raw.githubusercontent.com/JonyMeta/em-daily/main/data/digest.json
- `data/seen.json` — PubMed IDs already reviewed (prevents repeats)
- `scripts/fetch_candidates.py` — pulls new papers from PubMed (E-utilities)
- `scripts/publish.py` — writes the day's picks into the digest
- `AGENT.md` — the instructions the daily agent follows
