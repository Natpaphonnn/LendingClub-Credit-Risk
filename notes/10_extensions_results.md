# 10 — Extensions results (E1–E5, Nat's decisions after the quality review) — 2026-11-19

Pre-registration: `notes/08_prereg_extensions.md` (commit 4562602, **pushed to the private remote before anything below was computed**).
Code: `src/phase4/`, `src/phase2/{rule_B,ecl,ecl_lib,ecl_benchmark}.py`. Outputs: `reports/phase4/`, `reports/phase2/{macro_B,ecl,ecl_benchmark}.md`.

## TL;DR
1. **E1 — MOB-6 confirmatory test on 60-month loans: FAIL** (pre-registered criterion). Sensitivity 9/9 (95% CI 66–100%), specificity **4/6 = 67%**
   (CI 22–96%) < 80%. The two false alarms (2015Q1, 2015Q2) were quarters at 1.14× and 1.13× the reference MOB-12 rate — just under the 1.2× truth line.
   The 36m 2016–17 result stays "descriptive". Practical reading: MOB-6 A/E is a sensitive but not specific early warning.
2. **E2 — As-of model (realistic deployment, data to 2014-06, 12-month bad):** OOT 2015 Gini vs final outcome **33.1 [32.6, 33.7]**, i.e. **−3.65 [−3.95, −3.37]**
   vs the reference model (36.8) that used labels a 2014 lender could not have had. Its PD12 starts well calibrated (A/E 1.01 for 2015Q1).
   **Realistic alarm timing: first amber for 2015Q4, knowable Jun 2017; first red for 2016Q1, knowable Sep 2017** — about two years after the
   first worse vintage (2015Q2). PSI never left green (max 0.079).
3. **E3 — Macro rule (a) with the subsample redrawn in every bootstrap replicate:** θ = −0.0379, **95% CI [−0.0935, −0.0045]** → (a) FAIL; (b) PASS, (c) FAIL
   unchanged → **B still fails; Plan B (A + C) stands** (rule applied as written).
4. **E4 — Staging illustration (ex-post, monthly DPD not in the data):** at 2015-12-31 with the reference hazard: stage 1 263,610 loans ($112.3m, 3.75%),
   stage 2 (1–2 missed instalments) 1,571 loans ($1.5m), stage 3 (≥ 3 missed) 2,300 loans ($22.3m).
5. **E5 — ECL benchmark:** refitting the hazard at 2014-12-31 (outcomes to 2014-06) moves the 2015 backtest from realised = **1.17× → 1.10×** predicted
   (predicted lifetime EL $234.9m → $249.0m vs realised $273.8m) — about a third (36%) of the original gap came from not recalibrating.
   Discounted LGD (recoveries 12 months after default, at EIR) = **90.4%** (88.8% undiscounted). 90-DPD default definition: 12m ECL $80.1m vs $102.5m,
   lifetime ECL $200.9m vs $206.3m (both with discounted LGD), backtest ratio 1.17×.

---

## E1 — Confirmatory MOB-6 A/E test on 60-month loans — `reports/phase4/mob6_60m_test.md`
Reference 60m loans issued 2012-09..2013-12: n = 38,929, MOB-12 default rate 5.75%, r6 (M2) = 0.1220.
| score | truth YES / no | sensitivity | specificity | verdict |
|---|---|---|---|---|
| M2 (primary) | 9 / 6 | 9/9 = 100% (66–100%) | 4/6 = 67% (22–96%) | **FAIL** |
| M1 (secondary) | 9 / 6 | 9/9 = 100% (66–100%) | 4/6 = 67% (22–96%) | FAIL |
- False alarms: 2015Q1 (A/E6 1.14, truth 1.14×), 2015Q2 (1.17, 1.13×). First MOB-6 flag 2015Q1 (knowable 2016-03); first truth YES 2015Q3 (knowable 2017-03).
- Lead time 6 months by construction (not a criterion).

## E2 — As-of model — `reports/phase4/asof_model.md`, `reports/figures/p4_asof_monitoring.png`
- Train 2012-09..2013-03 (38,249 loans, bad12 4.14%), validation 2013-04..2013-06 (23,136, 3.99%); every bad12 event used occurred by 2014-06 (asserted in code).
  Selected config: num_leaves 15, min_child_samples 1000, lambda_l2 0 (126 rounds).
| OOT 2015 | as-of model | reference M2 |
|---|---|---|
| Gini vs final 36m bad | 33.1 [32.6, 33.7] | 36.8 [36.3, 37.3] |
| Gini vs bad12 | 37.4 [36.5, 38.3] | 38.8 [37.8, 39.7] |
| mean PD12 vs observed bad12 | 4.28% vs 4.66% (CITL12 −0.39 pp [−0.47, −0.32]) | – |
- Realistic monitoring (A/E12 = Σ bad12 / Σ PD12): 2015Q1 1.01 → 2015Q4 1.15 (amber, Jun 2017) → 2016Q1 1.29 (red, Sep 2017) → peak 1.39.

## E3 — Macro rule, corrected bootstrap — `reports/phase2/macro_B.md`
| | θ | 95% CI |
|---|---|---|
| primary 2009–2014 (rule) | −0.0379 | [−0.0935, −0.0045] |
| sensitivity 2012-09..2014 (not in rule) | +0.0287 | [−0.0116, 0.0609] |
(b) −27.1% PASS, (c) 0.91 FAIL — unchanged (point fits). Decision: B FAILS → A + C.

## E4 / E5 — ECL — `reports/phase2/ecl.md`, `reports/phase2/ecl_benchmark.md`
| scenario | 12m PD | lifetime PD | day-1 12m ECL | lifetime ECL | backtest pred EL (undisc.) | realised / predicted |
|---|---:|---:|---:|---:|---:|---:|
| (a) reference A, undiscounted LGD | 4.28% | 13.56% | $100.7m | $202.7m | $234.9m | 1.165 |
| (b) reference A, discounted LGD | 4.28% | 13.56% | $102.5m | $206.3m | – | – |
| (c) refit at 2014-12-31, discounted LGD | 4.01% | 15.14% | $93.4m | $214.6m | $249.0m | 1.099 |
| (d) 90-DPD definition, discounted LGD | 3.28% | 13.24% | $80.1m | $200.9m | $233.7m | 1.172 |
Staging at 2015-12-31 (ex-post illustration):
| stage | reference A, undiscounted LGD | refit at 2015-12-31, discounted LGD |
|---|---|---|
| Stage 1 (12m ECL) | 263,610 loans · $112.3m (3.75%) | 263,610 · $102.1m (3.41%) |
| Stage 2 (1–2 missed ≈ ≥ 30 DPD; lifetime) | 1,571 · $1.5m | 1,571 · $1.5m |
| Stage 3 (≥ 3 missed ≈ 90 DPD; LGD × EAD) | 2,300 · $22.3m | 2,300 · $22.6m |
| derecognised (prepaid) | 15,453 | 15,453 |
Caveats: cured delinquencies invisible (stage 2 understated); stage 1/2 ECL not conditioned on delinquency; refit done once per reporting date.

## Deviations
None from notes/08_prereg_extensions.md. Note: the as-of training window (7 months) is what the pre-registered information set allows; no tuning on OOT.
