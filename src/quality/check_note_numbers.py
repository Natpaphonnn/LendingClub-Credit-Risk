"""Number provenance for hand-written notes: every number in notes/02–05 must be traceable to a generated report.

For each numeric token in the notes, search all values in reports/**/*.md|json (excluding reports/quality) for one that
rounds to it at the token's precision under a scale in {1, 100, 0.01, 1e-6, 1e-3}. Unmatched tokens are listed for manual
review (they can be legitimate: thresholds, sums/differences computed in the text, counts of things).
Output: reports/quality/note_numbers_check.md
Usage: .venv/bin/python -I src/quality/check_note_numbers.py
"""
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NOTES = ["02_phase1_results.md", "03_phase2_results.md", "04_story.md", "05_claims_and_limitations.md"]
NUM = re.compile(r"(?<![\w.])([−\-+]?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[−\-+]?\$?\d+(?:\.\d+)?)(?![\w])")


def report_values():
    vals = []
    for p in (ROOT / "reports").rglob("*"):
        if "quality" in p.parts or p.suffix not in (".md", ".json"):
            continue
        txt = p.read_text(errors="ignore")
        if p.suffix == ".json":
            def walk(o):
                if isinstance(o, dict):
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
                elif isinstance(o, (int, float)) and not isinstance(o, bool) and o == o:
                    vals.append(float(o))
            walk(json.loads(txt))
        for m in re.finditer(r"-?\d[\d,]*\.?\d*(?:e-?\d+)?", txt):
            try:
                vals.append(float(m.group(0).replace(",", "")))
            except ValueError:
                pass
    return np.unique(np.array(vals))


def parse(tok):
    t = tok.replace("−", "-").replace("$", "").replace(",", "")
    d = len(t.split(".")[1]) if "." in t else 0
    return float(t), d


def is_skip(tok, line, x, d):
    if d == 0 and 2007 <= abs(x) <= 2026:
        return True                                       # years
    if re.search(rf"{re.escape(tok)}(Q\d|-\d\d)", line) or re.search(rf"\d-{re.escape(tok)}\b", line):
        return True                                       # quarter labels / dates
    if re.search(r"(commit|C\d+|§|step|Phase|phase|figure|Figure|fig|#)\s*" + re.escape(tok), line):
        return True
    return False


V = report_values()


def recomputed_counts():
    """Counts that build scripts print but no report stores — re-derived here so they also have a source."""
    import duckdb
    import pandas as pd
    i = ROOT / "data" / "interim"
    b = pd.read_parquet(i / "p1_base.parquet", columns=["issue_dt", "issue_q"])
    p2 = pd.read_parquet(i / "p2_loans.parquet", columns=["yr"])
    sc = pd.read_parquet(i / "p1" / "scores_m1.parquet", columns=["score_m1"])
    acc = i / "accepted_2007_to_2018Q4.parquet"
    dnm = duckdb.connect().execute(f"SELECT count(*) FROM '{acc}' WHERE loan_status LIKE 'Does not meet%'").fetchone()[0]
    return {"1,485,240": len(b), "1,364,557": int((pd.to_datetime(b.issue_dt) >= "2014-01-01").sum()),
            "1,433,835": len(p2), "473": int(sc.score_m1.min()), "620": int(sc.score_m1.max()),
            "544,642": int(((b.issue_q >= "2015Q2") & (b.issue_q <= "2016Q4")).sum()), "2,749": int(dnm)}


KNOWN = recomputed_counts()
scales = np.array([1, 100, 0.01, 1e-6, 1e-3, -1, -100])
rows, n_tok, verified = [], 0, []
for note in NOTES:
    for ln, line in enumerate((ROOT / "notes" / note).read_text().splitlines(), 1):
        line = re.sub(r"(\d)([mk])\b", r"\1 \2", line)            # "$234.9m" -> "$234.9 m"
        for m in NUM.finditer(line):
            tok = m.group(1)
            x, d = parse(tok)
            if is_skip(tok, line, x, d):
                continue
            n_tok += 1
            tol = 0.5 * 10 ** -d + 1e-9
            hit = np.any(np.abs(np.outer(V, scales) - x) <= tol) or np.any(np.abs(np.outer(V, scales) + x) <= tol)
            if not hit and tok in KNOWN and float(tok.replace(",", "")) == KNOWN[tok]:
                verified.append((note, ln, tok))
                continue
            if not hit:
                rows.append((note, ln, tok, line.strip()[:140]))
md = [f"# Note number provenance — {n_tok} numeric tokens checked; {n_tok - len(rows) - len(verified)} matched a report value, "
      f"{len(verified)} matched an independently re-derived count, {len(rows)} unmatched\n",
      "Re-derived counts: " + ", ".join(f"{k} ✓" for k in sorted({v[2] for v in verified})) + "\n",
      "Unmatched tokens need a manual verdict (threshold / arithmetic in text / count of items / error).\n",
      "| note | line | token | context |", "|---|---:|---|---|"]
md += [f"| {a} | {b} | `{c}` | {d.replace('|', '¦')} |" for a, b, c, d in rows]
(ROOT / "reports" / "quality" / "note_numbers_check.md").write_text("\n".join(md) + "\n")
print(md[0])
