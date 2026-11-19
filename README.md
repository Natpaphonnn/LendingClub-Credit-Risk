# LendingClub Credit Risk

**A credit model built on 2012–13 loans and used from 2015: did it survive — and would you have noticed in time?**

Application scorecard vs monotone LightGBM, monitoring (PSI/CSI, KS, actual/expected by vintage), vintage analysis, competing-risks
lifetime PD, a pre-registered macro test, a TFRS 9-style ECL backtest and a profit-based approval policy — on public LendingClub data
(36-month loans, 2012–2018), with time-based splits, leakage controls and pre-registered decision rules.

Headline results (details and status of each claim: `notes/05_claims_and_limitations.md`):
- Out-of-time Gini (2015): monotone LightGBM 36.8, WoE scorecard 33.7, LendingClub sub-grade 35.7.
- Ranking held, calibration drifted: actual/expected defaults by month 12 rose to 1.47; population stability (PSI) never alarmed.
- Treating prepayment as censoring overstates lifetime PD by about a third (18.2% vs 13.6%).
- State unemployment failed the pre-registered macro rule (the "adverse" scenario lowered PD).
- Lifetime expected loss at origination under-predicted the 2015 vintage's realised loss (realised = 1.17× predicted).

Known limitations (look-ahead in the development sample, hindsight in staging, no refit at the reporting date, exploratory-only
early-warning evidence) are listed in `notes/05_claims_and_limitations.md` and `notes/06_quality_report.md`.

## Reproduce
Requires the raw Kaggle files in `data/raw/` (not included) and the BLS responses fetched by `src/phase2/fetch_bls.py`.
```
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.lock.txt
bash scripts/run_all.sh            # full pipeline from data/raw, deterministic (~6–7 min)
.venv/bin/python -m pytest -q tests
.venv/bin/python -I src/quality/check_claims.py
```

## Layout
`src/audit` (Phase 0) · `src/phase1` (scorecard, LightGBM, monitoring, vintage) · `src/phase2` (hazard, macro rule, ECL, policy) ·
`src/lib/riskutils.py` (tested helpers) · `src/quality` (claim / provenance / leakage checks) · `notes/` (plans, pre-registrations,
results, story, quality report) · `reports/` (aggregates and figures only).

## Data
Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise). Unemployment data: U.S. Bureau of Labor Statistics, LAUS.
Data dictionary: Figshare copy, doi:10.6084/m9.figshare.20016077.v1 (CC BY 4.0). Raw and row-level data are not included in this
repository and are never published; see `notes/data_sources.md`.
