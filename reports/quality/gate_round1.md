# Bank gate — round 1 (rubric notes/09_gate_rubric.md, commit 9a493da; reviewed commit 4abadbe)

10 independent read-only reviewers, each recomputing from the row-level data in their lens. Pass rule: no unfixed BLOCKING
(correctness / leakage / methodology) finding **and** mean overall score ≥ 8.0.

| Reviewer | Lens | Overall | Lens score | BLOCKING |
|---|---|---|---|---|
| R1 | data sourcing, licence, governance | 7.8 | 7.6 | — |
| R2 | labels, censoring, time logic | 5.5 | 6.0 | R2-1 (= R7-1) |
| R3 | leakage / information sets | 7.6 | 7.4 | — |
| R4 | scorecard / WoE / reason codes | 7.4 | 7.2 | — |
| R5 | ML model (LightGBM) | 6.5 | 6.0 | R5-1 |
| R6 | monitoring / early warning | 8.0 | 8.2 | — |
| R7 | survival / competing risks | 5.8 | 5.5 | R7-1 |
| R8 | TFRS 9 ECL | 7.0 | 6.8 | — |
| R9 | macro rule B / policy C / statistics | 7.8 | 7.6 | — |
| R10 | reproducibility / documentation | 7.9 | 7.6 | — |
| **mean** | | **7.13** | | **3 (2 distinct)** |

**Round-1 verdict: FAIL** (mean 7.13 < 8.0; two distinct BLOCKING correctness findings).

## BLOCKING findings — verified by the builder before fixing

| ID | Finding | Verification | Fix |
|---|---|---|---|
| R5-1 | `monotone_constraints_method="advanced"` does not enforce the pre-registered monotone constraints (reversals on 22 of 34 constrained features) | own sweep on real rows: 22 / 34 features reverse | `"intermediate"` in train_lgbm, asof_model, grid_sensitivity; tests/test_monotone.py (synthetic + trained-model sweep). Bug fix — the pre-registered constraint set is unchanged |
| R7-1 / R2-1 | E5(c) refit at 2014-12-31 observes at most MOB 21; last spline column all-zero, ridge hides the singular Hessian; tail hazards are extrapolation; the 1.10× and "a third of the gap is recalibration" claims are artefacts | max W at 2014-12 = 21; basis column max over MOB 1..21 = 0 for column 5 | `hazard.check_identified` (fit_mnl refuses unsupported columns / ill-conditioned designs; test added); refit for R = 2014-12 uses vintages from 2009-01 (outcomes still only to R − 6m) — **bug-driven deviation** from the pre-registered 2012-09 start, logged in notes/10; the as-written refit is reported only over MOB 1–21 |

## Major findings (no spec change)

| ID | Finding | Fix |
|---|---|---|
| R1-1 / R10-1 | README / 06 say pre-registrations were pushed before each confirmatory run — only true for E1–E5 | reworded (Phase 1–2: local self-attested commits; E1–E5: pushed, 4562602) |
| R3-1 / R8-2 / R2-2 | refit benchmark described as look-ahead-free but uses M2 score (full labels) and final-recovery LGD | (c') sensitivity with as-of score and LGD from defaults known by 2014-06; wording corrected |
| R4-1 | +4.7 pp approval partly due to integer-score cutoff granularity | matched-bad-rate approval table (unrounded M1 linear predictor) |
| R4-2 | reason-code ties broken by column order | ranking by unrounded −β·factor·ΔWoE; "not as stable" removed; computed disagreement pairs replace hard-coded example (R5-5) |
| R7-2 | by-band A/E gradient pre-exists on validation (lp slope fitted in-sample) | by-band A/E table for train / validation / OOT in survival_A.md; C22 reworded |
| R8-1 | ECL gap explanation omits structural EAD bias | in-sample backtest, count × EAD × LGD decomposition; wording |
| R9-1 | policy comparisons without CIs | paired bootstrap (loan and issue-month block) for C − M2 and C − all at each discount rate; wording |

Minor findings: fixed where cheap (listed in reports/quality/gate_round1_fixes.md after the rerun); the rest are logged as limitations.
