# 09 — Bank gate rubric (fixed and pushed BEFORE the first gate run) — 2026-11-19

Purpose: an independent, bank-style sign-off gate over the whole project before packaging and write-up.

## Reviewers
10 independent reviewers, each a fresh agent with **no access to earlier review results** and **read-only** access to the repo
(they may read files, run read-only `git` commands and read-only Python on `data/interim`; they may not modify anything).
Each reviewer covers the whole project but leads with one lens:

| ID | lens |
|---|---|
| R1 | Data sourcing, licensing, governance, population definitions and exclusions |
| R2 | Labels, censoring, maturity and time logic (incl. "knowable" dates, as-of model information set) |
| R3 | Leakage and split integrity |
| R4 | Scorecard methodology (WoE binning, selection, scaling, reason codes) |
| R5 | ML model and statistical validation (LightGBM, monotonicity, bootstrap CIs, calibration, benchmark, grid sensitivity) |
| R6 | Monitoring and early warning (PSI/CSI, KS, A/E, MOB-6 confirmatory test on 60m loans, detection timing) |
| R7 | Survival / lifetime PD (competing risks, censoring, event coding, refits) |
| R8 | TFRS 9 / IFRS 9 ECL (12m vs lifetime, staging illustration, LGD/EAD, discounting, backtest, overlay, wording) |
| R9 | Macro rule (Plan B) and profit policy (C) — pre-registration fidelity, statistics, conclusions |
| R10 | Reproducibility, code quality, tests, documentation and claim traceability (notes ↔ reports ↔ code) |

## Scoring
- Each reviewer gives **an overall score 0–10** for the project as a portfolio / research credit-risk model on public data, judged against
  what a Thai bank model-validation team would require for sign-off of such a model. Anchors:
  **10** no material issues · **8** only minor issues; conclusions fully supported · **6** at least one major issue that weakens a conclusion ·
  **4** a correctness / leakage / methodology error that invalidates a headline result · **≤ 2** unusable.
- Each reviewer also scores their lens area 0–10 (reported, not part of the pass rule).
- Documented limitations are not errors **unless** a claim, figure title or headline overstates what the evidence supports.

## Findings
Each finding: ID, severity (**BLOCKING** / major / minor), category, evidence (file:line or report section + what was observed / re-derived),
why it matters, suggested fix. **BLOCKING** is reserved for: (1) a correctness error (a reported number or conclusion is wrong),
(2) a leakage or look-ahead error in a model or claim presented as realistic, (3) a methodology error that makes a method invalid for its stated purpose.

## Pass rule
**PASS = no unfixed verified BLOCKING finding AND mean of the 10 overall scores ≥ 8.0.**
- The orchestrator verifies every BLOCKING finding against the evidence. Verified → must be fixed before the next round (if the fix would change a
  pre-registered specification for a reason other than a bug → stop and report to Nat). Not reproducible / incorrect → rejected with the reason recorded.
- Major findings are fixed where possible without spec changes, otherwise documented.
- **Max 3 rounds.** Every round re-runs all 10 reviewers fresh against the current commit. Results per round: `reports/quality/gate_round{n}.md`.
- If round 3 does not pass, the gate result is FAIL and is reported as such.
