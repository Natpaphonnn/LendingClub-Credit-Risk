# 04 — Story (article narrative, in order) — 2026-11-19

> หมายเหตุสำหรับ Nat: ไฟล์นี้เขียนเป็นภาษาอังกฤษเพื่อใช้เป็น draft ของ Medium article ได้ตรง ๆ; ทุกตัวเลขมี source file กำกับ.
> Claims + limitations แบบครบอยู่ใน `notes/05_claims_and_limitations.md`. Figures: `reports/figures/article/fig1–8`.

**Working title:** *Would your 2014 credit model have survived 2015–16 — and would you have noticed in time?*

**One-line answer:** It kept ranking borrowers well (and beat LendingClub's own grades), but actual defaults drifted up to 47% above what it expected;
the standard stability alarm never fired, label-based checks caught it 12–18 months late, macro data could not explain it, and
provisions came in 17% short.

**How the work was done (one paragraph in the article):** time-based splits only; every model comparison and every rule was
pre-registered and committed to git *before* fitting (Phase 1: commit 652b889; Phase 2: commit 1203ada); out-of-time data
touched once; exploratory analyses labelled as such. Raw data is never published — only code, aggregates and figures.

---

## 1. Before any model: three data traps
*Figure 1 — `fig1_data_traps.png`*
- **The crisis cohort is tiny.** 2,260,668 accepted loans in total, but only **603 issued in 2007 and 2,393 in 2008**. The
  original "2007 model vs 2008" story is untestable → pivot to 2014 → 2015–16. *(notes/01_data_audit.md §2; reports/audit/audit_tables.md)*
- **Recent vintages are unfinished.** 36-month loans are ≥ 99.8% resolved only up to issue year 2015; 2016 = 72%, 2017 = 40%, 2018 = 12%.
  Naive bad rates on resolved loans are biased upward: 2016Q1 vs 2016Q2 shows 16.1% vs 22.4% just because Q2 is less resolved. *(01_data_audit.md §3)*
- **Leakage hides in plain sight.** 38 of 151 columns are post-origination (e.g. `last_fico_range_*` looks like FICO but is refreshed
  after funding; `next_pymnt_d` being empty reveals a closed loan); 9 more are LendingClub's own decisions (`int_rate`, `grade`, `sub_grade`).
  *(01_data_audit.md §4; reports/audit/column_catalogue.md)*
- Bonus traps: the free-text `desc` field disappears after March 2014; `member_id` is 100% empty. *(01_data_audit.md §2, §7)*

## 2. The champion beats LendingClub's grades
*Figure 2 — `fig2_champion_vs_lc.png`*
- Trained on 36-month loans issued Sep 2012 – Dec 2013 (120,683), tuned on 2014, tested once on 2015 (282,787), application data only.
- **Out-of-time Gini: monotone LightGBM 36.8 [36.3, 37.3] vs WoE scorecard 33.7 [33.1, 34.2] vs LC sub-grade 35.7 [35.2, 36.3].**
  Paired ΔGini (LightGBM − scorecard) **+3.1 [2.8, 3.4]**, above the pre-registered bar of +2.0 with CI > 0 → LightGBM is champion.
  *(notes/02_phase1_results.md §4; reports/phase1/evaluation.md; reports/phase1/metrics.json)*
- Business translation: at the same 11% bad-rate target set on 2014, the champion approves **82.1% vs 77.4%** (+4.7 pp). *(02_phase1_results.md §5)*
- Both models are shown side by side: the scorecard (14 characteristics, PDO 20) is the explainable one; reason codes for declines
  exist for both ("points below max" vs TreeSHAP; top reason agrees 48% of the time, the scorecard's top reason sits in LightGBM's top 4 90% of the time). *(02_phase1_results.md §6)*

## 3. Ranking survives, calibration drifts
*Figure 3 — `fig3_ranking_vs_level.png`*
- KS of the champion on every matured quarter 2014Q1–2015Q4 stays **25.9–27.1** (validation 26.4) — never near its alarm. *(reports/phase1/monitoring.md §3)*
- But the level breaks: on 2015 the model **under-predicts PD by 1.75 pp** (mean PD 13.1% vs 14.9% observed); the cutoff tuned to an
  11% bad rate on 2014 delivers **11.9%** on 2015. *(02_phase1_results.md §4–5)*
- Actual/expected defaults by month 12 climb from 0.93 (2014Q1) to **1.47 (2016Q3)**. *(monitoring.md §2)*

## 4. Population stability is the wrong alarm — 18 months late, ~545k loans
*Figure 4 — `fig4_alarm_timeline.png`; Figure 5 — `fig5_bands_mob12.png`*
- The champion's score PSI stays **≤ 0.06 in every quarter 2014–2018** (amber line 0.10). The scorecard's PSI is ≤ 0.03 through 2017Q3 and
  only goes amber in 2018 — because applicants got *better*, not worse. *(monitoring.md §1)*
- Characteristic-level alerts (CSI) did fire, but in the reassuring direction: revolving utilisation fell (median 59% → 41%) and LendingClub
  verified more incomes (Source Verified 16% → 35–47% per quarter). *(02_phase1_results.md §7)*
- Why: this was **concept drift**, not population shift. Defaults by month 12 rose in **every** score band (riskiest band 7.0% → 10.8%,
  safest 1.1% → 2.3%, 2013Q4 → 2016Q3). *(reports/phase1/vintage.md; fig 5)*
- The first worse vintage was issued Apr–Jun 2015; the first pre-registered label-based alarm (month-12 A/E amber) could only be known in
  **Dec 2016**; red in Sep 2017 for the champion (Jun 2017 for the scorecard). Meanwhile **~545k loans** (36-month, 2015Q2–2016Q4) were booked. *(02_phase1_results.md §7)*

## 5. An earlier signal: defaults by month 6
*Figure 4 (green lines)*
- Discovered exploratorily on 2015 vintages: the month-6 A/E would have gone amber for 2015Q2 by **Jun 2016** — 6 months earlier. *(reports/phase1/exploratory_early_signal.md)*
- Thresholds then pre-registered and tested **only on 2016–17 vintages**: flagged **7/7** deteriorated quarters, always **6 months** ahead of
  month-12. Specificity is untestable — every quarter in that window was deteriorated — so it is an early warning, not a verdict. *(reports/phase2/mob6_test.md)*

## 6. Lifetime PD needs prepayment as a competing risk
*Figure 6 — `fig6_prepayment_competing_risk.png`*
- Prepayment is the dominant exit: 57% of fully paid 36-month loans repaid > 3 months early. *(01_data_audit.md §8)*
- A discrete-time competing-risks hazard (default vs prepayment, open loans censored) calibrates to A/E 1.00 in training and 0.98–1.02 on 2014.
  **Ignoring prepayment overstates lifetime PD by a third: 18.2% vs 13.6%** on the 2015 portfolio (actual 14.9%). *(notes/03_phase2_results.md §A; reports/phase2/survival_A.md)*
  (Figure 6 uses Jan–Sep 2015 loans, observable to month 36: 18.4% vs 13.7% vs actual 14.7%.)
- Out of time it inherits the drift: A/E 1.07–1.11 on 2015, 1.26–1.39 on 2016, 1.44 on 2017 (censoring handled by comparing at equal months on book).

## 7. Macro data could not explain it — and the rule caught a fake pass
*(table in article; reports/phase2/macro_B.md)*
- Rule written before Phase 1, before any macro data: macro goes in only if (a) the unemployment effect is positive with CI > 0, (b) it cuts
  out-of-time calibration error ≥ 10%, and (c) a 2008–09 stress gives a 1.1×–3× PD multiplier.
- Result with BLS state unemployment: **(a) FAIL** θ = −0.038 [−0.088, −0.005] (significantly the *wrong* sign); **(b) PASS** (−27.1%); **(c) FAIL** multiplier **0.91** —
  the "adverse" scenario *lowered* PD.
- The (b) pass is spurious: unemployment fell 2009–2014 while LendingClub's defaults rose, so the model learned "lower unemployment = more
  default" (level coefficient −0.062). Requiring all three tests blocked it → Plan B (survival + profit policy). *(03_phase2_results.md §B)*

## 8. Provisions fell 17% short; an early-performance overlay closes about half
*Figure 7 — `fig7_ecl_backtest_overlay.png`*
- TFRS 9-style ECL = PD (competing-risks) × LGD × EAD (amortising), discounted at the loan rate. LGD = **88.8%** of exposure at default.
- 2015 portfolio ($3.62bn funded): day-1 12-month ECL **$101m (2.8%)**, lifetime ECL **$203m (5.6%)**.
- Backtest: predicted lifetime loss **$235m vs actual $274m (×1.17)**; worst in the safest band (×1.52). *(reports/phase2/ecl.md)*
- Illustrative, in-sample overlay (scale expected loss by observed A/E): **month-12 overlay closes 54%** of the gap ($256m), knowable
  Sep 2016 – Jun 2017; the month-6 version closes only 6%. *(reports/phase2/overlay.md)*
- Stage 2 cannot be allocated — the data has no monthly delinquency history — stated plainly. *(ecl.md)*

## 9. A good PD cutoff is enough
*Figure 8 — `fig8_policy_cutoff_vs_milp.png`*
- A MILP chose approval cells (PD decile × amount) to maximise expected NPV under approval ≥ 75% and expected bad ≤ 11%.
- On the pre-registered metric (undiscounted realised profit), **approve-everyone wins ($230m vs MILP $222m)** — the metric was wrong: it
  charges no cost of funds. *(reports/phase2/policy_C.md)*
- With a 5% funding cost (exploratory, approximate timing): **simple champion cutoff $47.4m ≈ MILP $45.6m ≫ approve-everyone $28.4m**.
  Business conclusion: a good PD cutoff is enough. *(policy_C.md)*

## Closing (what a Thai bank should take from this)
1. Monitor **level** (A/E by vintage, early months-on-book), not just stability (PSI) and ranking (KS).
2. Lifetime PD must model prepayment; otherwise TFRS 9 lifetime ECL is overstated by about a third.
3. Pre-register rules for adding macro overlays; one recession is not enough to estimate one.
4. When the model drifts, an early-performance overlay is a practical stop-gap — validate it on vintages you have not seen.
