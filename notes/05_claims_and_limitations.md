# 05 — Claims (with evidence) and limitations — 2026-11-19 (revised after independent validation; see notes/06_quality_report.md)

> สำหรับ Nat: เขียนภาษาอังกฤษเพื่อใช้เป็น appendix ของ article ได้ตรง ๆ. ทุก claim ระบุ **status**:
> **PRE-REG** = pre-registered test/rule (confirmatory) · **DESC** = descriptive fact from data · **EXPL** = exploratory (not pre-registered) ·
> **ILLUS** = illustrative / in-sample only. An article sentence should never upgrade a claim's status.

## Claims

| # | Claim (article wording) | Number(s) | Status | Evidence (file → section) |
|---|---|---|---|---|
| C1 | The 2007–08 crisis cohort is too small to test a "2007 → 2008" model. | 603 + 2,393 loans of 2,260,668 | DESC | notes/01_data_audit.md §2; reports/audit/audit_tables.md "Volume by issue year" |
| C2 | 36-month vintages after 2015 are unfinished; naive bad rates on resolved loans are biased. | resolved: 2015 99.9%, 2016 71.8%, 2017 40.1%, 2018 12.0%; 2016Q1 vs Q2 bad-among-resolved 16.1% vs 22.4% | DESC | 01_data_audit.md §3; audit_tables.md "Matured check by issue quarter" |
| C3 | 31% of the columns must not enter an application model: post-origination leakage or LendingClub's own decisions. | 38 POST + 9 LC-decision of 151 | DESC | 01_data_audit.md §4; reports/audit/column_catalogue.md; src/audit/leakage_map.py |
| C4 | The free-text description field vanishes in 2014. | desc present 25% in 2014-03, 0.3% in 2014-04, 0 after | DESC | 01_data_audit.md §7; audit_tables.md "7b" |
| C5 | Monotone LightGBM beats the WoE scorecard out of time (pre-registered rule met). | Gini 36.7 [36.3, 37.3] vs 33.7 [33.1, 34.2]; ΔGini +3.1 [2.8, 3.3] | PRE-REG | notes/02_phase1_results.md §4; reports/phase1/evaluation.md; metrics.json |
| C6 | The champion beats LendingClub's own sub-grade on 2015. | 36.7 vs 35.7 [35.2, 36.3]; paired difference +1.01 [0.52, 1.46] (benchmark, not a pre-registered test) | DESC (benchmark) | evaluation.md (LC_subgrade row, OOT note) |
| C7 | At the same bad-rate target the champion approves more applicants. | 82.1% vs 77.4% on 2014 (11% target; the integer-score cutoff stops below 11%); at a matched approved bad rate (unrounded scorecard) 82.1% vs 79.1% = 3.0 pp (gate R4-1) | PRE-REG (cutoff rule) | 02_phase1_results.md §5; evaluation.md "Cutoff rule" |
| C8 | Ranking did not degrade on quarters with complete, knowable outcomes (2014Q1–2015Q3); later vintages cannot be judged on final outcomes. | KS (champion) 25.8–27.2, never < 0.9 × 26.2 (2014 rows are the reference period); descriptive month-12 KS dips to 0.87–0.89× the 2014 level for 2016Q2–Q4 (monitoring.md §3b) | PRE-REG (monitoring threshold) | reports/phase1/monitoring.md §3 |
| C9 | Calibration drifted: 2015 PD under-predicted and the 2014 cutoff breached appetite. | CITL −1.70 pp [−1.82, −1.58] (i.i.d.; wider with clustering, see Statistics); about −0.57 pp of it already on 2014 validation (no recalibration, as pre-registered); approved bad 11.88% [11.75, 12.01] vs 11% target | PRE-REG | evaluation.md; 02_phase1_results.md §4–5 |
| C10 | Score PSI never alarmed for the champion. | PSI ≤ 0.057 all quarters 2014Q1–2018Q4 (amber 0.10) | PRE-REG (threshold) | monitoring.md §1 |
| C11 | The only PSI amber (scorecard, 2018) came from applicants getting better. | PSI 0.11–0.12; % below cutoff 21% → 10% | DESC | monitoring.md §1 |
| C12 | CSI alerts pointed to "safer" applicants. | median revol_util 59% → 41%; Source Verified 16% → 35–47% (2014–18 quarters) | DESC | 02_phase1_results.md §7; monitoring.md §5–6 |
| C13 | The drift was concept drift: defaults rose in every score band. | band 1 @MOB12 7.0% → 10.8%; band 5 1.1% → 2.3% (2013Q4 → 2016Q3) | DESC (vintage, pre-registered method) | reports/phase1/vintage.md |
| C14 | Relative to a counterfactual 2015 deployment, the first pre-registered label alarm came 18 months after the first worse vintage; ~545k loans booked meanwhile. | month-12 A/E amber for 2015Q2, knowable Dec 2016; red Sep 2017 (champion) / Jun 2017 (scorecard); 544,642 loans 2015Q2–2016Q4 | PRE-REG (signal + truth definitions) | monitoring.md §2, §4; 02_phase1_results.md §7 |
| C15 | Month-6 A/E would have flagged 2015Q2 six months earlier. | amber knowable Jun 2016 | EXPL (discovered here) | reports/phase1/exploratory_early_signal.md |
| C16 | Month-6 A/E is red in every 2016–17 quarter; in the discovery period the champion's version caught 1 of 2 deteriorated quarters with no false alarms. Not a confirmatory test (values seen before thresholds were registered; lead time 6 months by construction). | 7/7; discovery M2 1/2 sensitivity, 6/6 specificity | DESC / EXPL (relabelled after review CR-1) | reports/phase2/mob6_test.md |
| C17 | Treating prepayment as censoring (same hazards) overstates lifetime PD by about a third. | 18.2% vs 13.6% for loans issued Jan–Sep 2015 (observable to month 36); actual cumulative default by month 36: 14.7% | PRE-REG (demo specified in prereg) | notes/03_phase2_results.md §A; reports/phase2/survival_A.md |
| C18 | The competing-risks model is well calibrated in time at portfolio level (not by band, C22) but inherits the drift out of time. | A/E 1.01 train, 0.98–1.03 (2014), 1.09–1.12 (2015), 1.27–1.39 (2016), 1.43 (2017) | PRE-REG (evaluation spec) | survival_A.md |
| C19 | State unemployment failed the pre-registered macro rule; the adverse scenario lowered PD. | (a) θ −0.045 [−0.099, −0.009] FAIL (not positive; subsample redrawn per bootstrap replicate; earlier runs −0.019 and −0.038, all negative); (b) −28.0% PASS; (c) 0.89 FAIL | PRE-REG | reports/phase2/macro_B.md |
| C20 | The (b) pass is spurious time-trend confounding. | level coefficient −0.066; unemployment fell while defaults rose | Interpretation of PRE-REG output | macro_B.md; 03_phase2_results.md §B |
| C21 | Lifetime expected loss at origination under-predicted the 2015 vintage's realised loss (a backtest, not a booked provision). | predicted EL $232.4m vs realised $273.8m (×1.18; 15% of realised loss missed); in-sample on the development window ×1.03 (EAD understated ≈ 2.4%) | PRE-REG (backtest spec) | reports/phase2/ecl.md |
| C22 | The realised/predicted ratio is highest for the safest borrowers — a gradient already present on 2014 validation (score slope fitted in-sample), amplified by the drift. | ×1.44 (safest band) → ×1.03 (riskiest); validation 2014 A/E@36 1.30 → 0.92 | PRE-REG (by-band backtest) | ecl.md |
| C23 | ECL size at origination. | 12m $99.6m (2.7%); lifetime $200.6m (5.5%); LGD 88.8% [88.6, 89.0] | PRE-REG | ecl.md |
| C24 | An in-sample month-12 early-performance overlay closes 57% of the gap (month-6: 11%). | $255.8m / $237.1m vs $273.8m | ILLUS | reports/phase2/overlay.md |
| C25 | The pre-registered profit metric was wrong; under it approve-all "wins". | undiscounted: approve-all $230.3m vs MILP $222.3m | PRE-REG (result) + our admission | reports/phase2/policy_C.md |
| C26 | With funding cost, the MILP cell policy adds nothing over a single PD threshold; the threshold level depends on funding cost *and* PD calibration — tuned to NPV on the under-predicting PD it over-approved (single threshold $44.9m < appetite cutoff $47.5m). Levels depend on the cash-timing assumption; differences are the evidence. | realised NPV@5%: cutoff $47.5m, MILP $45.8m, approve-all $28.4m; MILP − cutoff −1.74 [−2.66, −0.82] (paired bootstrap); +0.98 [−0.07, 2.05] at 3%; a single threshold tuned to the same objective matches the MILP at 3/5/8% | EXPL | policy_C.md |
| C27 | The month-6 early-warning signal FAILED its confirmatory test on 60-month loans: specificity not demonstrated. | sensitivity 9/9; specificity 4/6 = 67% (< 80%; CI 22–96%, only 6 negative quarters) | PRE-REG (E1, pushed before computing) | reports/phase4/mob6_60m_test.md |
| C28 | A model built only with information available at 31 Dec 2014 ranks worse than the reference model. | as-of Gini 33.0 [32.5, 33.5] vs 36.7; ΔGini −3.76 [−4.05, −3.46] | PRE-REG (E2, descriptive comparison) | reports/phase4/asof_model.md |
| C29 | With the realistic as-of model the first alarm comes about two years after the first worse vintage (≥ 1.2× the 2012-09..2013-12 month-12 rate), 6 months after that vintage's truth was knowable. | amber 2015Q4 knowable Jun 2017; red 2016Q1 knowable Sep 2017; PSI max 0.075 | PRE-REG (E2) | reports/phase4/asof_model.md |
| C30 | Refitting the hazard at the reporting date on outcomes knowable then (MOB 1–21; tail borrowed from the reference model) does not close the gap — it widens it (the knowable outcomes come from better vintages). Replaces the withdrawn "closes a third" claim (gate R7-1 / R2-1). | refit MOB 1–21 + reference tail 1.27× (a lower bound: the tail uses post-2014 outcomes) vs reference 1.18×; with a knowable tail 1.41×; over MOB 1–21 1.33× vs 1.19×; 2009-start sensitivity 1.69× | PRE-REG (E5, descriptive) + bug-driven deviation | reports/phase2/ecl_benchmark.md |
| C31 | Discounting recoveries raises LGD; a later default definition lowers 12-month ECL but not lifetime loss. | LGD 90.4% vs 88.8%; 12m ECL $79.2m vs $101.3m with default at the 3rd missed instalment (≈ 60 DPD; pre-registered as "90-DPD", relabelled after gate R8-2), $67.8m at the 4th (≈ 90 DPD, post-hoc); backtest 1.18× / 1.19× | PRE-REG (E5) | reports/phase2/ecl_benchmark.md |
| C32 | Ex-post staging at Dec-2015 (illustration, 2015-vintage sub-portfolio): stage 2 = 1–2 missed instalments (≈ 0–60 DPD), stage 3 = ≥ 3 (≈ ≥ 60 DPD) as pre-registered; the 30/90-DPD-backstop-consistent variant (2–3 / ≥ 4 missed) is post-hoc. | stage 2 1,571 loans; stage 3 2,300 loans (682 with ≥ 6 missed, likely already written off; 439 more with 5); stage 1 $111.0m (3.71%); backstop variant: stage 2 1,521, stage 3 1,640 | PRE-REG (E4, illustration) | reports/phase2/ecl.md |

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
- 36-month loans only; 60-month loans (≈ 30% of volume) excluded from headline models (used only in the E1 confirmatory test).
- Individual applications only: joint applications are excluded everywhere (≈ 0 before 2016, 1.6% of 36m originations in 2016Q1, 11–13% from
  2017Q4); monitoring therefore covers a shrinking scorable share. Gate reviewers re-scored joint applications with the frozen champion: including them lowers 2018 PSI, so the conclusion is unchanged (gate R1-2).
- "Does not meet the credit policy" loans (2,749; 2007–10) excluded. The sensitivity promised in 01_data_audit was not run; it matters only for
  the macro fit window (36-month such loans in 2009–10: 565 + 690, ≈ 0.4% of the macro sample) (gate R1-3, round 2 R1-2).
- Development outcomes for 2013 vintages would not have been fully visible to a lender in 2014 (standard development-sample simplification);
  the 2014 validation outcomes (used for early stopping, config choice, the 11% cutoff and the KS reference) were complete only around 2018 —
  C7–C9 are counterfactual-timeline results (gate R2-3 / R3-3).
- Default month = last payment + 1: a few charge-offs record payments after MOB 36 (105 in train → censored as survivors; 0.7% of defaults) (gate R8-7);
  more generally, payments recorded after charge-off (debt settlements: ≈ 7% of charge-offs in 2013, 15–17% in 2015–16) date some defaults
  late — this slightly understates MOB-6/12 defaults on later vintages (conservative for the drift direction) (gate round 2 R2-2 / R3-4).
- Prepayment defined as payoff ≥ 3 months before maturity (convention).

**Features and models**
- Application-time features only; geography deliberately excluded (fair-lending), LC grade excluded (benchmark only). `loan_amnt` may reflect
  a credit-department reduction and `verification_status` is an underwriting-process output — both are LC-process influenced (gate R1-4).
- LightGBM missing values: NaN routing of `mths_since_*` fields is learned, not constrained by the monotone constraints (gate R5-3), and it can
  break monotonicity in *other* features: M2 has one residual reversal (annual_inc at one split near $41k for rows with mths_since_recent_bc missing;
  max 0.03 pp PD). tests/test_monotone.py sweeps every split threshold on a NaN-enriched sample with a 0.05 pp tolerance (gate round 2 R5-1 / R10-3).
- Cost of the constraints: the unconstrained twin of the champion config scores ≈ 0.4 Gini higher on OOT (reports/quality/grid_sensitivity.md).
- WoE bins: the 5% minimum share was applied on non-missing rows, so a few bins hold 4.6–5.0% of all rows; no significance-based merge step (gate R4-3/R4-4). Some fine bins in flat ranges lose strict bad-rate order out of time
  (4 of 13 numeric characteristics on 2015; near-identical points) — bin-level shares, bad rates and WoE by period in
  reports/phase1/scorecard_stability.md (descriptive); merging such bins would be a spec change (gate round 2 R4-2).
- Reason codes are characteristic names: MISSING bins can produce reasons (e.g. no instalment account → mo_sin_old_il_acct); `purpose`
  appears in 12.7% of top-4 reasons (fair-lending not checked); M1 uses a best-attribute baseline and M2 TreeSHAP a mean baseline, so part of
  their disagreement is the reference point (gate round 2 R4-4).
- Single training window (Sep 2012 – Dec 2013) — chosen by bureau-field availability.
- Small hyper-parameter grid (12 configs); results insensitive to it (≤ 0.0006 log loss spread) but not exhaustively searched.
- Calibration-slope bootstrap uses a truncated Newton solve (8 iterations).
- In the macro test, loans before Sep 2012 were scored by the frozen champion with missing bureau fields (degraded score), as the rule required.

**Monitoring**
- PSI/CSI/A/E thresholds are industry conventions, not optimised; "deterioration" truth (≥ 1.2× training month-12 default rate) is a pre-registered but arbitrary line.
- Month-6 signal: the 36m result is descriptive; the 60m confirmatory test (C27) failed on specificity, but with 6 negative quarters the
  specificity CI is wide and A/E6 mixes default level and timing (earlier defaults) (gate R6-4).
- Month-12 A/E vs the deterioration truth share the same numerator and knowable date (they differ by PD-mix normalisation only), so the
  MOB-12 alarm is close to a restatement of the truth; the 18-month lag is the observation window itself (gate R6-2).
- "First worse vintage" depends on the reference window: against the as-of model's own development window, 2015Q2 is below 1.2× and the
  first ≥ 1.2× quarter is 2016Q1 (gate R6-3 / R2-5).
- Detection dates assume the 6-month charge-off lag.

**Macro (B)**
- One downturn (2008–09) with almost no LendingClub lending; 24 issue quarters for the block bootstrap, but ≈ 85% of loans sit in the 10 quarters
  from 2012Q3, so the effective number of clusters is smaller and the CI may be anti-conservative (gate round 2 R9-5); state unemployment only;
  contemporaneous effect only.

**ECL**
- Score-only PD with no forward-looking component (because B failed) — not a TFRS 9-compliant ECL.
- Stage 2 is only an ex-post 30-DPD-backstop proxy (E4); no PD-based SICR test is possible (no refreshed scores / monthly DPD); cured
  delinquencies are invisible. Stage 3 includes loans with ≥ 6 missed instalments that LC had probably already written off (memo row) (gate R8-3/R8-4).
- Scheduled-balance EAD understates exposure at default by ≈ 2–3% (arrears before the last payment, timing): part of the backtest gap
  exists in-sample (gate R8-1).
- Stage-1 12-month ECL is backtested only descriptively (ecl_benchmark.md) (gate R8-6).
- LGD pooled from 2012–13 defaults; recoveries for the latest defaults may be incomplete; EAD ignores partial prepayments. LGD transferred well
  to 2015 (by default year 0.86–0.90 vs 0.87–0.91 in train) although the zero-recovery share rose from 6.8% to 28.0% — offsetting effects, not
  a stable process (gate round 2 R8-6).
- Prepayment hazard: the smooth spline cannot reach the structural zero at MOB 34–36 (payoffs there are maturity, coded as censored); no effect
  on lifetime PD (13.43% → 13.42% with a t ≥ 34 term) but late prepayment timing is mis-shaped (gate round 2 R7-3).
- Calibration of A is portfolio-level: by risk band it is off already on 2014 (C22) (gate round 2 R7-4).
- Backtest compares undiscounted expected loss with undiscounted realised net principal loss.

**Overlay (illustrative)**
- In-sample: no unseen vintage remains for MOB-6; scaling whole-life expected loss by an early A/E is crude.

**Policy (C)**
- Pre-registered profit metric omitted cost of funds (our error); the corrected metric is exploratory with approximate cash timing, and its
  dollar levels depend heavily on that timing (an alternative timing roughly halves them); signs and rankings of the differences hold —
  quote differences, not levels (gate round 2 R9-3). Policy CIs condition on the selected policies and on one vintage (R9-4).
- 30 coarse cells; the bad-rate constraint uses model PD, which under-predicted after the drift; 5% funding rate is an assumption (3% and 8% shown).

**Added after independent validation (notes/06_quality_report.md)**
- **Timeline look-ahead (MA-1):** the reference model's labels (full 36-month outcomes of 2012–13 vintages) were complete only around 2017; its alarm
  dates are relative to a counterfactual 2015 deployment. The as-of model (C28–C29) removes this for ranking and monitoring; the hazard / ECL
  reference model keeps it. The refit benchmark (C30) recalibrates the hazard on outcomes known at the reporting date, but its score covariate
  (M2) and LGD still use post-2014 outcomes; (c') replaces both and is shown as a sensitivity (gate R3-1 / R8-2 / R2-2).
- **Re-run and selection noise (MA-2):** a deterministic re-run changed the selected LightGBM config (num_leaves 15 → 63), and the R5-1 retrain
  changed it again (→ 31); the grid's validation log-loss spread is ≤ 0.0006, so selection is near-noise. All 12 configs keep the conclusions (reports/quality/grid_sensitivity.md).
- **Macro CI fragility (MA-3):** θ moved −0.019 → −0.038 → −0.045 across runs and fixes; since E3 every bootstrap replicate redraws the 25%
  subsample; both the percentile and the normal-approximation CI exclude 0 on the negative side (reports/phase2/macro_B.md).
- **MOB-6:** the 36m result is descriptive (C16); the confirmatory 60m test failed on specificity (C27).
- **Staging uses hindsight (MA-5):** stages come from missed instalments inferred from the final status (E4); cured delinquencies are invisible.
- **ECL design (MA-6):** headline ECL uses the reference (not refit) hazard and undiscounted LGD; benchmark refit / discounted LGD / 90-DPD in C30–C31.
  Still: no downturn LGD adjustment; recoveries include debt-sale proceeds; EAD excludes accrued interest; refit once per reporting date.
- **Pre-registration evidence (MA-10):** Phase 1–2 pre-registrations are local, self-timestamped commits (first push 2026-11-19 23:34, after
  their results) — order is self-attested. E1–E5 (commit 4562602) and the gate rubric (9a493da) were pushed before computing (gate R1-1).
- **Statistics:** bootstrap CIs resample loans i.i.d. (no quarter clustering); for level metrics this understates uncertainty — e.g. the M2 OOT
  CITL CI is [−1.82, −1.58] i.i.d. but ≈ [−1.96, −1.44] by issue month and ≈ [−2.10, −1.16] by state (gate round 2 R5-3); KS percentile CIs
  are biased upward (R5-5); A/E thresholds have no binomial/traffic-light bounds.
- **Not checked:** fair-lending / disparate impact (e.g. `purpose` as a decline reason); unseen categorical values are mapped to missing and counted at scoring (src/lib/scoring.py; counts in
  reports/phase1/lgbm_grid.md) but have no alarm threshold.
- **Monotonicity (gate R5-1):** the first build used LightGBM `monotone_constraints_method="advanced"`, which violated the constraints;
  now `"intermediate"` with a post-training sweep test (tests/test_monotone.py).
- **Data dictionary text** is quoted from a third-party Figshare copy whose CC BY 4.0 tag is the uploader's claim (same caveat as Kaggle CC0) (gate R1-7).
- **Provenance check is lenient:** it accepts any report value that rounds to the token; the claim checker is the strict test.

**Process notes (fixed issues, for transparency)**
- Audit: `desc` SQL keyword and `avg()` skipping NULLs inflated text shares in the first run — fixed before reporting.
- Overlay: a nullable-integer comparison produced A/E ≈ 7 in the first run — caught as implausible, fixed before reporting.
