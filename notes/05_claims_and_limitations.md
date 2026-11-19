# 05 — Claims (with evidence) and limitations — 2026-11-19

> สำหรับ Nat: เขียนภาษาอังกฤษเพื่อใช้เป็น appendix ของ article ได้ตรง ๆ. ทุก claim ระบุ **status**:
> **PRE-REG** = pre-registered test/rule (confirmatory) · **DESC** = descriptive fact from data · **EXPL** = exploratory (not pre-registered) ·
> **ILLUS** = illustrative / in-sample only. An article sentence should never upgrade a claim's status.

## Claims

| # | Claim (article wording) | Number(s) | Status | Evidence (file → section) |
|---|---|---|---|---|
| C1 | The 2007–08 crisis cohort is too small to test a "2007 → 2008" model. | 603 + 2,393 loans of 2,260,668 | DESC | notes/01_data_audit.md §2; reports/audit/audit_tables.md "Volume by issue year" |
| C2 | 36-month vintages after 2015 are unfinished; naive bad rates on resolved loans are biased. | resolved: 2015 99.9%, 2016 71.8%, 2017 40.1%, 2018 12.0%; 2016Q1 vs Q2 bad-among-resolved 16.1% vs 22.4% | DESC | 01_data_audit.md §3; audit_tables.md "Matured check by issue quarter" |
| C3 | A quarter of the columns leak post-origination information. | 38 POST + 9 LC-decision of 151 | DESC | 01_data_audit.md §4; reports/audit/column_catalogue.md; src/audit/leakage_map.py |
| C4 | The free-text description field vanishes in 2014. | desc present 25% in 2014-03, 0.3% in 2014-04, 0 after | DESC | 01_data_audit.md §7; audit_tables.md "7b" |
| C5 | Monotone LightGBM beats the WoE scorecard out of time (pre-registered rule met). | Gini 36.8 [36.3, 37.3] vs 33.7 [33.1, 34.2]; ΔGini +3.1 [2.8, 3.4] | PRE-REG | notes/02_phase1_results.md §4; reports/phase1/evaluation.md; metrics.json |
| C6 | The champion beats LendingClub's own sub-grade on 2015. | 36.8 vs 35.7 [35.2, 36.3] (benchmark, not a pre-registered test) | DESC (benchmark) | evaluation.md (LC_subgrade row) |
| C7 | At the same bad-rate target the champion approves more applicants. | 82.1% vs 77.4% on 2014 (11% target) | PRE-REG (cutoff rule) | 02_phase1_results.md §5; evaluation.md "Cutoff rule" |
| C8 | Ranking did not degrade on matured 2014–15 quarters. | KS (champion) 25.9–27.1, never < 0.9 × 26.4 | PRE-REG (monitoring threshold) | reports/phase1/monitoring.md §3 |
| C9 | Calibration drifted: 2015 PD under-predicted and the 2014 cutoff breached appetite. | CITL −1.75 pp [−1.87, −1.63]; approved bad 11.91% [11.78, 12.04] vs 11% target | PRE-REG | evaluation.md; 02_phase1_results.md §4–5 |
| C10 | Score PSI never alarmed for the champion. | PSI ≤ 0.058 all quarters 2014Q1–2018Q4 (amber 0.10) | PRE-REG (threshold) | monitoring.md §1 |
| C11 | The only PSI amber (scorecard, 2018) came from applicants getting better. | PSI 0.11–0.12; % below cutoff 21% → 10% | DESC | monitoring.md §1 |
| C12 | CSI alerts pointed to "safer" applicants. | median revol_util 59% → 41%; Source Verified 16% → 35–47% (2014–18 quarters) | DESC | 02_phase1_results.md §7; monitoring.md §5–6 |
| C13 | The drift was concept drift: defaults rose in every score band. | band 1 @MOB12 7.0% → 10.8%; band 5 1.1% → 2.3% (2013Q4 → 2016Q3) | DESC (vintage, pre-registered method) | reports/phase1/vintage.md |
| C14 | The first pre-registered label alarm came 18 months after the first worse vintage; ~545k loans booked meanwhile. | month-12 A/E amber for 2015Q2, knowable Dec 2016; red Sep 2017 (champion) / Jun 2017 (scorecard); 544,642 loans 2015Q2–2016Q4 | PRE-REG (signal + truth definitions) | monitoring.md §2, §4; 02_phase1_results.md §7 |
| C15 | Month-6 A/E would have flagged 2015Q2 six months earlier. | amber knowable Jun 2016 | EXPL (discovered here) | reports/phase1/exploratory_early_signal.md |
| C16 | Month-6 A/E caught every deteriorated quarter in unseen 2016–17 vintages, 6 months ahead. | 7/7, lead 6 months; specificity untestable | PRE-REG (thresholds fixed before test) | reports/phase2/mob6_test.md |
| C17 | Ignoring prepayment overstates lifetime PD by about a third. | 18.2% vs 13.6% (2015 portfolio; actual 14.9%) | PRE-REG (demo specified in prereg) | notes/03_phase2_results.md §A; reports/phase2/survival_A.md |
| C18 | The competing-risks model is well calibrated in time but inherits the drift out of time. | A/E 1.01 train, 0.98–1.02 (2014), 1.07–1.11 (2015), 1.26–1.39 (2016), 1.44 (2017) | PRE-REG (evaluation spec) | survival_A.md |
| C19 | State unemployment failed the pre-registered macro rule; the adverse scenario lowered PD. | (a) θ −0.038 [−0.088, −0.005] FAIL; (b) −27.1% PASS; (c) 0.91 FAIL | PRE-REG | reports/phase2/macro_B.md |
| C20 | The (b) pass is spurious time-trend confounding. | level coefficient −0.062 (SE 0.0035); unemployment fell while defaults rose | Interpretation of PRE-REG output | macro_B.md; 03_phase2_results.md §B |
| C21 | Lifetime ECL under-provisioned the 2015 vintage by 17%. | predicted EL $234.9m vs realised $273.8m (×1.17) | PRE-REG (backtest spec) | reports/phase2/ecl.md |
| C22 | Under-provision is concentrated in the safest borrowers. | ×1.52 (safest band) → ×1.00 (riskiest) | PRE-REG (by-band backtest) | ecl.md |
| C23 | ECL size at origination. | 12m $100.7m (2.8%); lifetime $202.7m (5.6%); LGD 88.8% [88.6, 89.0] | PRE-REG | ecl.md |
| C24 | A month-12 early-performance overlay closes 54% of the gap (month-6: 6%). | $256.0m / $237.3m vs $273.8m | ILLUS | reports/phase2/overlay.md |
| C25 | The pre-registered profit metric was wrong; under it approve-all "wins". | undiscounted: approve-all $230.3m vs MILP $222.3m | PRE-REG (result) + our admission | reports/phase2/policy_C.md |
| C26 | With funding cost, a simple PD cutoff ≈ the MILP optimum. | NPV@5%: cutoff $47.4m, MILP $45.6m, approve-all $28.4m | EXPL | policy_C.md |

## Limitations

**Data**
- Accepted loans only; no reject inference (decision 4) → every model is conditioned on LendingClub's own screening (also why IVs are low: max 0.12).
- One platform (US, unsecured P2P, 2012–2018); Thai bank portfolios (NCB bureau, secured products, different regulation) may behave differently.
- Data cut ≈ March 2019; 2016–2018 outcomes are partially censored.
- `member_id` empty → no repeat-borrower or customer-level view.
- License: Kaggle CC0 is the uploader's tag; LendingClub's own terms may restrict redistribution → only aggregates are published.
- Data dictionary is a third-party Figshare copy (CC BY 4.0), as the original LendingClub page is gone.
- BLS LAUS figures are today's revised series, not the real-time vintages a lender would have seen.

**Labels and timing**
- No monthly payment history: default month ≈ last payment + 1; charge-off lag assumed 6 months for observability; stage 3 timing is ex post.
- 36-month loans only; 60-month loans (≈ 30% of volume) excluded from headline models.
- "Does not meet the credit policy" loans (2,749; 2007–10) excluded.
- Development outcomes for 2013 vintages would not have been fully visible to a lender in 2014 (standard development-sample simplification).
- Prepayment defined as payoff ≥ 3 months before maturity (convention).

**Features and models**
- Application-time features only; geography deliberately excluded (fair-lending), LC grade excluded (benchmark only).
- Single training window (Sep 2012 – Dec 2013) — chosen by bureau-field availability.
- Small hyper-parameter grid (12 configs); results insensitive to it (≤ 0.0006 log loss spread) but not exhaustively searched.
- Calibration-slope bootstrap uses a truncated Newton solve (8 iterations).
- In the macro test, loans before Sep 2012 were scored by the frozen champion with missing bureau fields (degraded score), as the rule required.

**Monitoring**
- PSI/CSI/A/E thresholds are industry conventions, not optimised; "deterioration" truth (≥ 1.2× training month-12 default rate) is a pre-registered but arbitrary line.
- Month-6 signal: specificity (false-alarm rate) untested — no non-deteriorated quarter in the out-of-discovery window.
- Detection dates assume the 6-month charge-off lag.

**Macro (B)**
- One downturn (2008–09) with almost no LendingClub lending; 24 issue quarters for the block bootstrap; state unemployment only; contemporaneous effect only.

**ECL**
- Score-only PD with no forward-looking component (because B failed) — not a TFRS 9-compliant ECL.
- Stage 2 cannot be allocated (no delinquency history or refreshed scores); only an upper bound is shown.
- LGD pooled from 2012–13 defaults; recoveries for the latest defaults may be incomplete; EAD ignores partial prepayments.
- Backtest compares undiscounted expected loss with undiscounted realised net principal loss.

**Overlay (illustrative)**
- In-sample: no unseen vintage remains for MOB-6; scaling whole-life expected loss by an early A/E is crude.

**Policy (C)**
- Pre-registered profit metric omitted cost of funds (our error); the corrected metric is exploratory with approximate cash timing.
- 30 coarse cells; the bad-rate constraint uses model PD, which under-predicted after the drift; 5% funding rate is an assumption (3% and 8% shown).

**Process notes (fixed issues, for transparency)**
- Audit: `desc` SQL keyword and `avg()` skipping NULLs inflated text shares in the first run — fixed before reporting.
- Overlay: a nullable-integer comparison produced A/E ≈ 7 in the first run — caught as implausible, fixed before reporting.
