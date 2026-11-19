# Bank gate — round 2 (rubric notes/09_gate_rubric.md, commit 9a493da; reviewed commit 330f9d2)

10 fresh, independent read-only reviewers (instructed not to open earlier gate results), each recomputing from data/interim in their lens.
Pass rule: no unfixed verified BLOCKING finding **and** mean overall score ≥ 8.0.

| Reviewer | Lens | Overall | Lens score | BLOCKING | Majors |
|---|---|---|---|---|---|
| R1 | data sourcing, licence, governance | 8.4 | 8.8 | — | — |
| R2 | labels, censoring, time logic | 7.9 | 8.4 | — | R2-1 ranking wording beyond KS coverage |
| R3 | leakage / information sets | 8.4 | 8.8 | — | — |
| R4 | scorecard / WoE / reason codes | 8.6 | 8.8 | — | — |
| R5 | ML model / statistics | 8.5 | 8.6 | — | — |
| R6 | monitoring / early warning | 8.3 | 8.4 | — | R6-1 ranking wording (= R2-1) |
| R7 | survival / competing risks | 7.9 | 8.1 | — | R7-1 E5 (c) tail not knowable-only |
| R8 | TFRS 9 ECL | 8.0 | 7.5 | — | R8-1 missed-instalment→DPD mapping; R8-2 "90-DPD" is ≈ 60 DPD |
| R9 | macro rule B / policy C | 8.2 | 8.0 | — | R9-1 stale hard-coded CI sentence; R9-2 policy takeaway overstated |
| R10 | reproducibility / documentation | 8.0 | 7.5 | — | R10-1 rerun reused parquet; R10-2 06 stale; R10-3 residual monotonicity (NaN routing); R10-4 BLS checksum blocks outside rerun |
| **mean** | | **8.22** | | **0** | |

**Round-2 verdict: PASS** (mean 8.22 ≥ 8.0; no BLOCKING finding). Every reviewer reproduced the headline numbers in their lens.

## Post-gate fixes (majors fixed where possible without spec changes, per the rubric)
Listed with outcomes in reports/quality/gate_round2_fixes.md after the final rerun.
