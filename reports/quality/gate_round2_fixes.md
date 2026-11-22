# Gate round 2 — post-gate fixes (gate PASSED at 330f9d2, mean 8.22; fixes per rubric: majors fixed where possible without spec changes)

No pre-registered threshold, window, population or decision criterion was changed. "post-hoc" = descriptive addition, labelled as such.

| finding | severity | outcome |
|---|---|---|
| R2-1 / R6-1 ranking "held" beyond KS coverage | major | **fixed**: wording scoped to 2014Q1–2015Q3 (README, 04, 05 C8, 07, fig3); post-hoc month-12 KS/Gini by quarter (monitoring.md §3b): 0.87–0.89× for 2016Q2–Q4 |
| R7-1 / R3-1 / R8-3 E5 (c) tail not knowable | major / minor | **fixed**: 1.27× stated as a lower bound; post-hoc (c'') knowable tail 1.41× (ecl_benchmark.md) |
| R8-1 missed instalments ↔ DPD | major | **fixed**: relabel (1–2 missed ≈ 0–60 DPD, ≥ 3 ≈ ≥ 60 DPD); post-hoc backstop-consistent staging (2–3 / ≥ 4 missed): 1,521 / 1,640 loans |
| R8-2 "90-DPD" = 3rd missed ≈ 60 DPD | major | **fixed**: relabel; post-hoc (d') 4th missed ≈ 90 DPD: 12m ECL $67.8m, ×1.19 |
| R9-1 hard-coded CI sentence false | major | **fixed**: computed in rule_B.py (percentile and normal CIs both exclude 0) |
| R9-2 policy takeaway overstated | major | **fixed**: "level depends on funding cost and PD calibration"; fig8 shows the NPV-tuned single threshold and the paired CI |
| R10-1 rerun reused parquet | major | **fixed**: run_all deletes data/interim and rebuilds from raw |
| R10-2 06 stale | major | **fixed**: marked chronological, stale rows annotated, round-2 + final-state sections; 06 added to provenance check |
| R10-3 / R5-1 residual monotonicity (NaN routing) | major / minor | **disclosed + tested**: threshold sweep on NaN-enriched rows, max reversal 2.6e-4 PD (tolerance 5e-4); not retrained (immaterial; retraining would move every number) |
| R10-4 / R1-3 BLS checksum blocks outside rerun | major / minor | **fixed**: pin on parsed values (bls_values.sha256), `ALLOW_REVISED_BLS=1` override; BLS files not committed (project rule: no raw data in git) |
| R10-5 checks not in run_all | minor | fixed (pytest, check_claims, check_note_numbers fail-fast) |
| R10-6 stale logs | minor | fixed (old logs removed; runA/runB = final runs) |
| R10-8 fig7 title clipped | minor | fixed (shorter title) |
| R10-9 / R6-3 A/E ≥ vs > | minor | fixed (strict > as pre-registered; no flag changed) |
| R10-11 / R1-4 article pre-registration caveat; sub-grade remark | minor | fixed |
| R6-4 / R3-2 "PSI never alarmed" | minor | fixed ("the champion's PSI") |
| R6-5 fig4 month-6 legend | minor | fixed |
| R6-6 / R2-5 (r1) 18-month window in README | minor | fixed |
| R1-1 stale joint-app PSI numbers | minor | fixed (numbers removed; conclusion stated) |
| R1-2 565 + 1,001 includes 60m | minor | fixed (565 + 690) |
| R1-5 fig1 subtitle | minor | fixed |
| R2-2 / R3-4 settlement payments date defaults late | minor | disclosed (notes/05) |
| R2-3 story as-of A/E 1.01 | minor | fixed (1.02) |
| R2-4 article KS scope | minor | fixed |
| R2-5 / R7-2 docstrings / identifiability wording | minor | fixed |
| R2-6 memo ≥ 6 vs ≥ 5 | minor | fixed (both memo rows shown) |
| R4-1 story CI [2.8, 3.4] | minor | fixed |
| R4-2 bin stability | minor | fixed: reports/phase1/scorecard_stability.md (4 of 13 numeric characteristics reverse on OOT; descriptive) |
| R4-3 scorecard scaling tests | minor | fixed (tests/test_scorecard_scaling.py) |
| R4-4 reason-code caveats | minor | disclosed (notes/05) |
| R5-2 cost of constraints | minor | fixed (unconstrained twin in grid_sensitivity.md: OOT Gini 37.16 vs 36.74) |
| R5-3 CITL i.i.d. CI | minor | disclosed with reviewer's cluster CIs |
| R5-4 CITL already −0.57 on 2014 | minor | fixed (C9, 02) |
| R5-5 / R10-7 two Gini CIs; KS CI bias | minor | disclosed |
| R7-3 prepay structural zero | minor | disclosed |
| R7-4 calibration portfolio-level | minor | fixed (C18) |
| R7-5 C17 horizon | minor | fixed (14.7% by month 36) |
| R8-4 "provision" wording | minor | fixed (article §8 title, STATUS) |
| R8-5 sub-portfolio scope, EIR | minor | fixed (ecl.md) |
| R8-6 LGD stability | minor | disclosed |
| R9-3 NPV timing sensitivity | minor | disclosed ("quote differences, not levels") |
| R9-4 bootstrap conditions | minor | fixed (wording) |
| R9-5 unequal clusters | minor | disclosed |
| R9-6 stale CI in 03 deviations | minor | fixed |
| R3-3 tests of extension information sets | minor | fixed: tests/test_asof_information_set.py (+ src/phase4/asof_info.py, asserted in asof_model.py) and the fit_hazard_asof window test |
| R10-10 "read" claims are self-consistency | minor | fixed: src/quality/rederive_ecl_policy.py re-derives every ECL and policy claim of the article from the raw file with separate code (reports/quality/rederive_ecl_policy.md), run by run_all |
| R10-12 duplicated scoring block | minor | fixed: src/lib/scoring.py used by every stage; unseen categories counted; tests/test_scoring_helper.py |
