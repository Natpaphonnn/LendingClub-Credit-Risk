# 10 — Extensions results (E1–E5, Nat's decisions after the quality review) — 2026-11-19, updated 2026-11-20 after bank gate round 1

Pre-registration: `notes/08_prereg_extensions.md` (commit 4562602, **pushed to the private remote before anything below was computed**).
Code: `src/phase4/`, `src/phase2/{rule_B,ecl,ecl_lib,ecl_benchmark}.py`. Outputs: `reports/phase4/`, `reports/phase2/{macro_B,ecl,ecl_benchmark}.md`.

> **Update after gate round 1 (2026-11-20).** Two verified bugs were fixed and everything below was recomputed: (1) LightGBM used
> `monotone_constraints_method="advanced"`, which violated the pre-registered monotone constraints (R5-1) → `"intermediate"`; this re-trains
> M2 and the as-of model, so E1–E5 numbers moved slightly (E1 verdict unchanged). (2) The E5 refit at 2014-12-31 observed at most MOB 21, so its
> late-MOB hazards were unidentified extrapolation (R7-1 / R2-1); the earlier "1.10× / a third of the gap" result is **withdrawn**.
> Prior exposure note (R6-7): the Phase 0 audit had shown quarterly bad-among-final rates for 60m loans (confounded by resolution, not MOB-6/12)
> before E1 was pre-registered; E1 thresholds were carried over from Phase 1, not tuned.

## TL;DR
1. **E1 — MOB-6 confirmatory test on 60-month loans: FAIL** (pre-registered criterion). Sensitivity 9/9 (95% CI 66–100%), specificity **4/6 = 67%**
   (CI 22–96%) < 80%. Specificity is *not demonstrated* rather than disproven (6 negative quarters). The two false alarms (2015Q1, 2015Q2) were quarters
   at 1.14× and 1.13× the reference MOB-12 rate — just under the 1.2× truth line — where defaults arrived earlier: A/E6 mixes timing and level.
   The 36m 2016–17 result stays "descriptive".
2. **E2 — As-of model (realistic deployment, data to 2014-06, 12-month bad):** OOT 2015 Gini vs final outcome **33.0 [32.5, 33.5]**, i.e. **−3.76 [−4.05, −3.46]**
   vs the reference model (36.7) that used labels a 2014 lender could not have had. Its PD12 starts well calibrated (A/E 1.02 for 2015Q1).
   **Realistic alarm timing: first amber for 2015Q4, knowable Jun 2017; first red for 2016Q1, knowable Sep 2017** — about two years after the
   first vintage ≥ 1.2× the 2012-09..2013-12 MOB-12 rate (2015Q2); against the as-of model's own development window the first such vintage is
   2016Q1, whose truth is knowable the same month as the red alarm (R6-3). PSI never left green (max 0.075).
3. **E3 — Macro rule (a) with the subsample redrawn in every bootstrap replicate:** θ = −0.0452, **95% CI [−0.0990, −0.0095]** → (a) FAIL; (b) PASS, (c) FAIL
   → **B still fails; Plan B (A + C) stands** (rule applied as written).
4. **E4 — Staging illustration (ex-post, monthly DPD not in the data):** at 2015-12-31 with the reference hazard: stage 1 263,610 loans ($111.0m, 3.71%),
   stage 2 (1–2 missed instalments) 1,571 loans ($1.5m), stage 3 (≥ 3 missed) 2,300 loans ($22.3m; 682 of them with ≥ 6 missed — probably already
   written off by LC, memo row).
5. **E5 — ECL benchmark:** refitting the hazard at 2014-12-31 on outcomes a lender could see (to 2014-06) **does not close the gap — it widens it**:
   realised = **1.27×** predicted (refit for MOB 1–21 + reference-A tail) vs 1.18× for the reference; over the months the refit identifies (MOB 1–21)
   1.33× vs 1.19×; a full-horizon refit on vintages from 2009 gives 1.69× (degraded pre-2012-09 score, sensitivity only). The knowable outcomes
   come from vintages that performed better than 2015 — a refit cannot see drift that has not happened yet. Discounted LGD (recoveries 12 months
   after default, at EIR) = **90.4%** (88.8% undiscounted). 90-DPD default definition: 12m ECL $79.2m vs $101.3m, lifetime ECL $198.8m vs $204.1m
   (both discounted LGD), backtest ratio 1.18×. Descriptive additions: in-sample backtest of reference A 1.03× (scheduled-balance EAD understates
   exposure at default by 2.4%); 12-month backtest 1.14×.

---

## E1 — Confirmatory MOB-6 A/E test on 60-month loans — `reports/phase4/mob6_60m_test.md`
Reference 60m loans issued 2012-09..2013-12: n = 38,929, MOB-12 default rate 5.75%, r6 (M2) = 0.1219.
| score | truth YES / no | sensitivity | specificity | verdict |
|---|---|---|---|---|
| M2 (primary) | 9 / 6 | 9/9 = 100% (66–100%) | 4/6 = 67% (22–96%) | **FAIL** |
| M1 (secondary) | 9 / 6 | 9/9 = 100% (66–100%) | 4/6 = 67% (22–96%) | FAIL |
- False alarms: 2015Q1 (A/E6 1.14, truth 1.14×), 2015Q2 (1.18, 1.13×). First MOB-6 flag 2015Q1 (knowable 2016-03); first truth YES 2015Q3 (knowable 2017-03).
- Lead time 6 months by construction (not a criterion). Any future test should pre-register binomial bounds and an amber line consistent with the truth line (R6-4).

## E2 — As-of model — `reports/phase4/asof_model.md`, `reports/figures/p4_asof_monitoring.png`
- Train 2012-09..2013-03 (38,249 loans, bad12 4.14%), validation 2013-04..2013-06 (23,136, 3.99%); every bad12 event used occurred by 2014-06 (asserted in code).
  Selected config: num_leaves 31, min_child_samples 1000, lambda_l2 10. bad12 is defined from the final status (cured delinquencies invisible) (R3-4).
| OOT 2015 | as-of model | reference M2 |
|---|---|---|
| Gini vs final 36m bad | 33.0 [32.5, 33.5] | 36.7 [36.2, 37.3] |
| Gini vs bad12 | 37.4 [36.4, 38.2] | 38.7 [37.7, 39.5] |
| mean PD12 vs observed bad12 | 4.24% vs 4.66% (CITL12 −0.42 pp [−0.51, −0.35]) | – |
- Realistic monitoring (A/E12 = Σ bad12 / Σ PD12): 2015Q1 1.02 → 2015Q4 1.16 (amber, Jun 2017) → 2016Q1 1.30 (red, Sep 2017) → peak 1.41.
- The gap to the reference mixes a shorter training window (7 vs 16 months of vintages) and a shorter label horizon (12 vs 36 months); it is not decomposed (R5-4).

## E3 — Macro rule, corrected bootstrap — `reports/phase2/macro_B.md`
| | θ | 95% CI |
|---|---|---|
| primary 2009–2014 (rule) | −0.0452 | [−0.0990, −0.0095] |
| sensitivity 2012-09..2014 (not in rule) | +0.0296 | [−0.0106, 0.0616] |
(b) −28.0% PASS, (c) 0.89 FAIL. Decision: B FAILS → A + C. The bootstrap distribution sits below the point estimate (zero-exclusion depends on the CI
method; the rule outcome does not, since θ is not positive). Test (b) is out-of-time by vintage, not by calendar (R3-5).

## E4 / E5 — ECL — `reports/phase2/ecl.md`, `reports/phase2/ecl_benchmark.md`
| scenario | 12m PD | lifetime PD | day-1 12m ECL | lifetime ECL | backtest pred EL (undisc.) | realised / predicted |
|---|---:|---:|---:|---:|---:|---:|
| (a) reference A, undiscounted LGD | 4.24% | 13.42% | $99.6m | $200.6m | $232.4m | 1.178 |
| (b) reference A, discounted LGD | 4.24% | 13.42% | $101.3m | $204.1m | – | – |
| (c) refit at 2014-12-31 (MOB 1–21 identified) + reference tail, discounted LGD | 3.97% | 12.92% | $92.4m | $188.3m | $215.6m | 1.270 |
| (c') (c) with as-of score and LGD from defaults known by 2014-06 | 3.89% | 12.64% | $91.3m | $188.2m | $215.6m | 1.270 |
| (c2) sensitivity: refit from 2009-01 vintages | 3.33% | 9.21% | $77.5m | $143.2m | $162.4m | 1.686 |
| (d) 90-DPD definition, discounted LGD | 3.25% | 13.10% | $79.2m | $198.8m | $231.2m | 1.184 |

Decomposition realised/predicted = default count × EAD per default × LGD: (a) 1.108 × 1.057 × 1.005; (c) 1.152 × 1.097 × 1.005.
The reference model is already at 1.03× in-sample. 12-month backtest (day 1, reference A): realised $123.7m vs $108.1m (1.14×).

Staging at 2015-12-31 (ex-post illustration):
| stage | reference A, undiscounted LGD | refit at 2015-12-31, discounted LGD |
|---|---|---|
| Stage 1 (12m ECL) | 263,610 loans · $111.0m (3.71%) | 263,610 · $101.5m (3.39%) |
| Stage 2 (1–2 missed ≈ ≥ 30 DPD; lifetime) | 1,571 · $1.5m | 1,571 · $1.4m |
| Stage 3 (≥ 3 missed ≈ 90 DPD; LGD × EAD) | 2,300 · $22.3m | 2,300 · $22.6m |
| memo: stage 3 with ≥ 6 missed (likely written off) | 682 | 682 |
| derecognised (prepaid) | 15,453 | 15,453 |
Caveats: cured delinquencies invisible (stage 2 understated); stage 1/2 ECL not conditioned on delinquency; refit done once per reporting date.

## Deviations
1. **E5 (c) refit window — bug-driven (gate R7-1 / R2-1).** The pre-registered refit on loans issued 2012-09 → R with outcomes to R − 6m observes
   at most MOB 21 for R = 2014-12-31, so the hazard spec A (36-month B-spline) is not identified beyond MOB 21. The refit is used only for MOB 1–21;
   MOB 22–36 hazards come from reference A (stated assumption). A full-horizon refit from 2009 vintages is shown as sensitivity (c2). `fit_mnl`
   now refuses unidentified designs (tests/test_metrics_woe_hazard.py, tests/test_ecl_lib.py). The R = 2015-12-31 refit (max MOB 33) is identified
   and unchanged.
2. **(c') as-of sensitivity — added after review (R3-1 / R8-2 / R2-2):** not pre-registered; descriptive.
3. **Monotone method — bug fix (R5-1):** E1, E2 and E5 recomputed with M2 / the as-of model trained with `"intermediate"`; no threshold, window or
   criterion changed. E1 verdict unchanged.
Note: the as-of training window (7 months) is what the pre-registered information set allows; no tuning on OOT.
