# LendingClub Credit Risk

**A credit model built on 2012–13 loans and used from 2015: did it survive — and would you have noticed in time?**

A bank-style credit-risk project on public LendingClub data: WoE scorecard vs monotone LightGBM, monitoring (PSI/CSI, KS,
actual/expected by vintage), vintage analysis, competing-risks lifetime PD, a pre-registered macro test, a TFRS 9-style ECL backtest with a
refit benchmark, and a profit-based approval policy. Headline population: 36-month individual loans 2012–2018; the macro test uses 36-month
loans 2009–2014 and the confirmatory early-warning test uses 60-month loans 2012–2017. Time-based splits, leakage controls, deterministic
reruns, and pre-registered decision rules — Phase 1–2 pre-registrations are local, self-timestamped commits (order self-attested); the
extension pre-registration (E1–E5, commit 4562602) and the review-gate rubric (9a493da) were pushed to the remote before computing.

## Headline results (status of every claim: `notes/05_claims_and_limitations.md`)
- Out-of-time Gini (2015): monotone LightGBM **36.7**, WoE scorecard 33.7, LendingClub sub-grade 35.7. A realistic **as-of** model that only uses
  information available on 31 Dec 2014 (12-month bad window) scores 33.0.
- Ranking held on every quarter with complete outcomes (2014Q1–2015Q3), calibration drifted: actual/expected defaults by month 12 rose to 1.46
  (2016Q3), where month-12 ranking also softened (KS 0.87–0.89× its 2014 level). The champion's PSI never alarmed (the scorecard's went amber in
  2018, as applicants improved). With the as-of model the first alarm would have been knowable in **Jun 2017**, about two years after the first
  vintage ≥ 1.2× the 2012–13 month-12 default rate — 18 months of that is the month-12 observation window itself.
- A month-6 early-warning signal caught 9/9 deteriorated quarters but **failed** its pre-registered confirmatory test on 60-month loans
  (specificity 4/6 = 67% < 80%; with 6 negative quarters, specificity is not demonstrated).
- Treating prepayment as censoring overstates lifetime PD by about a third (18.0% vs 13.4%).
- State unemployment failed the pre-registered macro rule (the "adverse" scenario lowered PD) → no forward-looking macro overlay.
- Lifetime expected loss under-predicted the 2015 vintage's realised loss (realised = 1.18× predicted). Refitting at the reporting date on
  outcomes knowable then (months 1–21, tail from the reference model) makes it worse — 1.27×, a lower bound (1.41× with a knowable tail):
  the observable outcomes came from better vintages.
- Approval policy: an optimised cell policy (MILP) adds nothing over a single PD threshold; the right threshold level depends on funding cost and
  on PD calibration (tuned to NPV on an under-predicting PD, it over-approved).

Known limitations: `notes/05_claims_and_limitations.md`; validation history: `notes/06_quality_report.md`; review gate: `reports/quality/gate_round*.md`.

## Reproduce
1. **Data (not included — never redistributed).** Accept the terms of the Kaggle dataset "All Lending Club loan data" (wordsforthewise) and download:
   ```
   kaggle datasets download wordsforthewise/lending-club -f accepted_2007_to_2018Q4.csv.gz -p data/raw
   kaggle datasets download wordsforthewise/lending-club -f rejected_2007_to_2018Q4.csv.gz -p data/raw
   ```
   Data dictionary: `curl -L -o data/raw/dictionary/LCDataDictionary.xlsx https://ndownloader.figshare.com/files/35685971`.
   Checksums: `raw_inputs.sha256` (verified by `run_all.sh`). BLS unemployment is fetched by the pipeline (`src/phase2/fetch_bls.py`, public API,
   no key) and checked against `bls_values.sha256` (parsed values, not response bytes). If BLS has revised the series since, the fetch stops;
   `ALLOW_REVISED_BLS=1 bash scripts/run_all.sh` continues with a warning (results then differ slightly).
2. **Environment** (Python 3.12, pinned):
   ```
   uv venv --python 3.12 .venv
   uv pip install --python .venv/bin/python -r requirements.lock.txt
   ```
3. **Run** (deterministic; ~9 min on a laptop, `nice 19`): `bash scripts/run_all.sh` deletes `data/interim`, rebuilds everything from
   `data/raw`, then runs the tests, the strict claim re-check (`src/quality/check_claims.py`: re-derived where possible, otherwise a consistency
   check against the cited report) and the number-provenance check (`src/quality/check_note_numbers.py`), failing fast on any error.
   Two fresh runs produce byte-identical `reports/` and `demo/` (hash manifest: `reports/quality/reports_manifest.sha256`).
4. **Demo:** open `demo/index.html` (static, aggregates only). **Article draft:** `notes/07_article_draft.md`.

## Layout
| path | content |
|---|---|
| `src/audit` | Phase 0 data audit (parquet conversion, leakage map, profiling) |
| `src/phase1` | scorecard, LightGBM, evaluation, monitoring, vintage |
| `src/phase2` | competing-risks hazard, macro rule, ECL (+ benchmark), profit policy, overlay |
| `src/phase4` | as-of model, confirmatory 60m early-warning test |
| `src/lib/riskutils.py` | small tested helpers for error-prone logic |
| `src/quality` | claim re-check, number provenance, leakage/split proof, grid sensitivity |
| `src/report` | article figures, demo builder |
| `notes/` | plan, pre-registrations (02, 03, 08), results (01–03, 10), story, claims, quality report, gate rubric, article draft |
| `reports/` | aggregates and figures only · `demo/` static dashboard (aggregates only) |

## Data and credits
Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise). Unemployment data: U.S. Bureau of Labor Statistics, LAUS (public domain).
Data dictionary: Figshare copy, doi:10.6084/m9.figshare.20016077.v1 (CC BY 4.0). Raw and row-level data are not included in this repository and
are never published; see `notes/data_sources.md`.
