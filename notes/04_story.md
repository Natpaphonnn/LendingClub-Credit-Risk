# 04 — Story (article narrative, in order) — 2026-11-19 (revised after independent validation, see notes/06_quality_report.md)

> หมายเหตุสำหรับ Nat: ไฟล์นี้เขียนเป็นภาษาอังกฤษเพื่อใช้เป็น draft ของ Medium article ได้ตรง ๆ; ทุกตัวเลขมี source file กำกับ.
> Claims + status (PRE-REG / DESC / EXPL / ILLUS) อยู่ใน `notes/05_claims_and_limitations.md`. Figures: `reports/figures/article/fig1–8`.
> ฉบับนี้แก้ตาม independent review: timeline framing (MA-1), MOB-6 ไม่ใช่ confirmatory test (CR-1), wording ของ ECL / macro / prepayment.

**Working title:** *A credit model built on 2012–13 loans and used from 2015: did it survive — and would you have noticed in time?*

**Timeline caveat (state it up front in the article).** The model is trained on the *full* 36-month outcomes of loans issued
Sep 2012 – Dec 2013. In reality those outcomes were only complete around 2017, so no lender could have had this exact model in 2015.
We therefore report two models: the **reference** model (full labels; alarms dated relative to a counterfactual 2015 deployment) and an
**as-of** model built only from what a lender knew on 31 Dec 2014 (12-month bad window, outcomes to Jun 2014). *(notes/10_extensions_results.md E2)*

**One-line answer:** It kept ranking borrowers well (and beat LendingClub's own grades), but actual defaults drifted up to 47% above
what it expected; the standard stability alarm never fired, label-based checks fired 12–18 months after the first worse loans were
issued (about two years with the realistic as-of model), macro data could not explain it, and the lifetime expected loss came in below the loss actually realised (realised = 1.17× predicted).

**How the work was done (one paragraph in the article):** time-based splits only; model comparisons and decision rules were written
down and committed to git before fitting (Phase 1: commit 652b889; Phase 2: commit 1203ada — local commits only, so the order is
self-attested); out-of-time (OOT) data is evaluated once per pipeline run. One deterministic re-run (after fixing non-deterministic
row order) changed the selected LightGBM configuration; this is disclosed, and the conclusions hold for all 12 pre-registered configs.
Exploratory analyses are labelled. Raw data is never published — only code, aggregates and figures.

---

## 1. Before any model: three data traps
*Figure 1 — `fig1_data_traps.png`*
- **The crisis cohort is tiny.** 2,260,668 accepted loans in total, but only **603 issued in 2007 and 2,393 in 2008**. The
  original "2007 model vs 2008" story is untestable → pivot. *(notes/01_data_audit.md §2; reports/audit/audit_tables.md)*
- **Recent vintages are unfinished.** 36-month loans are ≥ 99.8% resolved only up to issue year 2015; 2016 = 72%, 2017 = 40%, 2018 = 12%.
  Naive bad rates on resolved loans are biased upward: 2016Q1 vs 2016Q2 shows 16.1% vs 22.4% just because Q2 is less resolved. *(01_data_audit.md §3)*
- **Leakage hides in plain sight.** 38 of 151 columns are post-origination (e.g. `last_fico_range_*` looks like FICO but is refreshed
  after funding; `next_pymnt_d` being empty reveals a closed loan); 9 more are LendingClub's own decisions (`int_rate`, `grade`, `sub_grade`),
  which must not be features of "our" model either. *(01_data_audit.md §4; reports/audit/column_catalogue.md)*
- Bonus traps: the free-text `desc` field disappears after March 2014; `member_id` is 100% empty. *(01_data_audit.md §2, §7)*

## 2. The champion beats LendingClub's grades
*Figure 2 — `fig2_champion_vs_lc.png`*
- Trained on 36-month loans issued Sep 2012 – Dec 2013 (120,683), tuned on 2014, tested on 2015 (282,787), application data only.
- **Out-of-time Gini: monotone LightGBM 36.8 [36.3, 37.3] vs WoE scorecard 33.7 [33.1, 34.2] vs LC sub-grade 35.7 [35.2, 36.3].**
  Paired ΔGini (LightGBM − scorecard) **+3.1 [2.8, 3.4]**, above the pre-registered bar of +2.0 with CI > 0 → LightGBM is champion.
  Against LC's sub-grade (descriptive benchmark, not pre-registered): **++1.05 [0.56, 1.48]**. Every one of the 12 grid configs beats the scorecard by ≥ 2.8. The realistic as-of model (12-month bad, data to Jun 2014) scores
  **33.1 [32.6, 33.7]** — 3.65 below the reference: part of the reference's edge is labels a 2014 lender could not have had. *(10_extensions_results.md E2)*
  *(notes/02_phase1_results.md §4; reports/phase1/evaluation.md; reports/quality/grid_sensitivity.md)*
- Business translation: at the same 11% bad-rate target set on 2014, the champion approves **82.1% vs 77.4%** (+4.7 pp). *(02_phase1_results.md §5)*
- Both models are shown side by side: the scorecard (14 characteristics, PDO 20) is the explainable one; reason codes for declines
  exist for both ("points below max" vs TreeSHAP; top reason agrees 48% of the time, the scorecard's top reason sits in LightGBM's top 4 90% of the time). *(02_phase1_results.md §6)*

## 3. Ranking survives, calibration drifts
*Figure 3 — `fig3_ranking_vs_level.png`*
- KS of the champion on every matured quarter 2014Q1–2015Q4 stays **25.9–27.1** (validation 26.4) — never near its alarm. *(reports/phase1/monitoring.md §3)*
- But the level breaks: on 2015 the model **under-predicts PD by 1.75 pp** (mean PD 13.1% vs 14.9% observed); the cutoff tuned to an
  11% bad rate on 2014 delivers **11.9%** on 2015. *(02_phase1_results.md §4–5)*
- Actual/expected defaults by month 12 climb from 0.93 (2014Q1) to **1.47 (2016Q3)**. *(monitoring.md §2)*

## 4. Population stability is the wrong alarm
*Figure 4 — `fig4_alarm_timeline.png`; Figure 5 — `fig5_bands_mob12.png`*
- The champion's score PSI stays **≤ 0.06 in every quarter 2014–2018** (amber line 0.10). The scorecard's PSI is ≤ 0.03 through 2017Q3 and
  only goes amber in 2018 — because applicants got *better*, not worse. *(monitoring.md §1)*
- Characteristic-level alerts (CSI) did fire, but in the reassuring direction: revolving utilisation fell (median 59% → 41%) and LendingClub
  verified more incomes (Source Verified 16% → 35–47% per quarter). *(02_phase1_results.md §7)*
- Why: this was **concept drift**, not population shift. Defaults by month 12 rose in **every** score band (riskiest band 7.0% → 10.8%,
  safest 1.1% → 2.3%, 2013Q4 → 2016Q3). *(reports/phase1/vintage.md; fig 5)*
- Relative to a 2015 deployment (see timeline caveat): the first worse vintage was issued Apr–Jun 2015; the first pre-registered
  label-based alarm (month-12 A/E amber) could only be known in **Dec 2016**; red in Sep 2017 for the champion (Jun 2017 for the scorecard).
  Meanwhile **~545k loans** (36-month, 2015Q2–2016Q4) were booked. A/E thresholds are conventions without statistical bounds. *(02_phase1_results.md §7)*
- With the **as-of model** a lender really could have had in Jan 2015 (PD12 well calibrated at first, A/E 1.01 for 2015Q1), the first amber is for
  2015Q4 vintages, knowable **Jun 2017**; red for 2016Q1, knowable **Sep 2017**; its PSI never left green (max 0.079). *(reports/phase4/asof_model.md)*

## 5. An earlier signal? Defaults by month 6 — sensitive, but failed the confirmatory test
*Figure 4 (green line)*
- Found exploratorily: the month-6 A/E would have gone amber for 2015Q2 by **Jun 2016**, 6 months before the month-12 alarm.
  *(reports/phase1/exploratory_early_signal.md)*
- In the discovery period (2014Q1–2015Q4) the champion's month-6 signal caught **1 of 2** deteriorated quarters (missed 2015Q4) with no
  false alarms (6/6); the scorecard's caught 2/2. *(reports/phase2/mob6_test.md)*
- 2016–17: every quarter is red. This is **descriptive, not a confirmatory test** — those values had already been computed before the
  thresholds were registered, every quarter was deteriorated (so any always-on alarm would also "catch" them all), and the 6-month lead is
  true by construction. The signal level also depends on how "expected" is built (0.91–1.09 for 2015 under the lifetime model). A genuine
  test needs a new pre-registration on unseen data. *(mob6_test.md; 06_quality_report.md CR-1, MA-7)*
- **That test was then run** (pre-registered and pushed to the remote before computing): on 60-month loans, never analysed before, the month-6
  signal caught **9/9** deteriorated quarters but raised **2 false alarms in 6** (specificity 67% < 80%) → **FAIL** by the pre-registered criterion.
  The false alarms were quarters at 1.13–1.14× the reference default rate, just under the 1.2× truth line. *(reports/phase4/mob6_60m_test.md)*

## 6. Lifetime PD needs prepayment as a competing risk
*Figure 6 — `fig6_prepayment_competing_risk.png`*
- Prepayment is the dominant exit: 57% of fully paid 36-month loans repaid > 3 months early. *(01_data_audit.md §8)*
- A discrete-time competing-risks hazard (default vs prepayment, open loans censored) calibrates to A/E 1.01 in training and 0.98–1.02 on 2014.
  **Treating prepayment as censoring (same hazards) overstates lifetime PD by about a third: 18.2% vs 13.6%** on the 2015 portfolio
  (actual 14.9%). A binary 36-month PD already reflects prepayment; the error appears when a hazard/survival model censors prepayments.
  *(notes/03_phase2_results.md §A; reports/phase2/survival_A.md)* (Figure 6 uses Jan–Sep 2015 loans, observable to month 36: 18.4% vs 13.7% vs actual 14.7%.)
- Out of time it inherits the drift: A/E 1.07–1.11 on 2015, 1.26–1.39 on 2016, 1.44 on 2017 (censoring handled by comparing at equal months on book).

## 7. Macro data could not explain it — and the rule caught a fake pass
*(table in article; reports/phase2/macro_B.md)*
- Rule written before Phase 1, before any macro data: macro goes in only if (a) the unemployment effect is positive with CI > 0, (b) it cuts
  out-of-time calibration error ≥ 10%, and (c) a 2008–09 stress gives a 1.1×–3× PD multiplier.
- Result with BLS state unemployment: **(a) FAIL** — θ is not positive (−0.038 [−0.094, −0.004] with the subsample redrawn in every bootstrap replicate;
  −0.019 [−0.063, 0.011] before the deterministic re-run, so the CI's exact position is fragile); **(b) PASS** (−27.1%); **(c) FAIL** multiplier **0.91** —
  the "adverse" scenario *lowered* PD.
- The (b) pass is spurious: unemployment fell 2009–2014 while LendingClub's defaults rose, so the model learned "lower unemployment = more
  default" (level coefficient −0.062). Requiring all three tests blocked it → Plan B (survival + profit policy). *(03_phase2_results.md §B)*

## 8. Lifetime expected loss under-predicted realised loss; an early-performance overlay closes about half the gap
*Figure 7 — `fig7_ecl_backtest_overlay.png`*
- TFRS 9-style ECL = PD (competing-risks) × LGD × EAD (amortising), discounted at the loan rate. LGD = **88.8%** of exposure at default.
- 2015 portfolio ($3.62bn funded): day-1 12-month ECL **$101m (2.8%)** — the Stage 1 allowance at origination — and lifetime ECL **$203m (5.6%)**.
- Backtest (not a booked provision): undiscounted lifetime expected loss at origination **$235m vs realised net loss $274m (realised = 1.17×
  predicted; the model missed 14% of realised loss)**; the ratio is highest in the safest band (×1.52), while the largest dollar gaps sit in the
  middle bands. *(reports/phase2/ecl.md)*
- The gap mixes two things: the drift, and the fact that the PD was not re-fitted at the reporting date. **Refitting at 31 Dec 2014** (outcomes to
  Jun 2014) raises predicted lifetime loss to $249m and moves the ratio to **1.10×** — about a third of the gap was missing recalibration.
  Discounting recoveries at the loan rate raises LGD from 88.8% to 90.4%; a 90-DPD default definition lowers 12-month ECL ($80m vs $102m) but
  barely changes lifetime loss (1.17×). *(reports/phase2/ecl_benchmark.md; 10_extensions_results.md E5)*
- Illustrative, in-sample overlay (scale expected loss by observed A/E): **month-12 overlay closes 54%** of the gap ($256m), knowable
  Sep 2016 – Jun 2017; the month-6 version closes only 6%. *(reports/phase2/overlay.md)*
- Staging is shown only as an **ex-post illustration** (monthly DPD is not in the data): at Dec-2015, 1,571 loans with 1–2 missed instalments
  (≈ ≥ 30 DPD) go to Stage 2 and 2,300 with ≥ 3 (≈ 90 DPD) to Stage 3; delinquencies that later cured are invisible. *(ecl.md; 10 E4)*

## 9. A good PD cutoff is enough
*Figure 8 — `fig8_policy_cutoff_vs_milp.png`*
- A MILP chose approval cells (PD decile × amount) to maximise expected NPV under approval ≥ 75% and expected bad ≤ 11%.
- On the pre-registered metric (undiscounted realised profit), **approve-everyone wins ($230m vs MILP $222m)** — the metric was wrong: it
  charges no cost of funds. *(reports/phase2/policy_C.md)*
- On an exploratory metric with a 5% funding cost (approximate timing, no CIs): **simple champion cutoff $47.4m ≈ MILP $45.6m ≫ approve-everyone $28.4m**.
  Business reading: a good PD cutoff is enough; the optimiser adds nothing here. *(policy_C.md)*

## Closing (what a Thai bank should take from this)
1. Monitor **level** (A/E by vintage, early months-on-book, with statistical bounds), not just stability (PSI) and ranking (KS).
2. If lifetime PD comes from a hazard/survival model, model prepayment as a competing risk; censoring it overstates lifetime PD by about a third.
3. Pre-register rules for adding macro overlays; one recession is not enough to estimate one.
4. When the model drifts, re-fit/recalibrate at each reporting date and consider an early-performance overlay — and validate any early
   signal on vintages whose values you have not yet looked at.
