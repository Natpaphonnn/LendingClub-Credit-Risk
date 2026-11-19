# LendingClub Credit Risk — portfolio project (bank DS / credit risk roles)

Owner: Nat. Created 2026-11-19. Language for reports to Nat: plain Thai with English technical terms.

## Goal
A bank-grade credit risk portfolio project. Story: "If you were a lender in 2007, would your model survive 2008 — and would you notice in time?"
Target roles: Data Scientist / Credit Risk Analyst at Thai banks (SCB, KBank, Krungthai, ttb).

## Scope (see notes/00_plan.md)
Core: (1) application scorecard (WoE/IV logistic vs LightGBM, KS/Gini, out-of-time, cutoff by approval vs bad rate),
(2) monitoring (PSI/CSI, KS over time, backtest through 2008), (3) vintage analysis.
Senior differentiators — pick 2 after Phase 0: (A) survival / lifetime PD with prepayment as competing risk,
(B) macro-linked PD + baseline/adverse stress test, (C) profit-optimal policy under constraints (LP/IP),
(D) reason codes + monotonic constraints. Optional: (6) LLM/NLP on loan description text, (8) reject inference, (G) causal effect of rate on default.

## Data & license rules (HARD)
- Primary: Kaggle "All Lending Club loan data" (wordsforthewise / Nathan George), tagged CC0 by the uploader; original source LendingClub.
- Backup (clear license): Zenodo 10.5281/zenodo.11295916, CC BY 4.0 — cite it if used.
- Never commit or upload raw or row-level data anywhere (GitHub, Kaggle datasets, articles). Publish only code, aggregates, figures, model results.
- Credit sources in README/article: "Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise)".
- External data only if public domain / open license and recorded in notes/data_sources.md (e.g. US unemployment from BLS/FRED).
- Never read or print kaggle.json, .env or API keys. Nat handles any account login / terms acceptance himself.
- Do not use HomeCredit data or code (separate project with its own restrictions).

## Method rules
- Time-based splits only (train on earlier vintages, test on later). No random split for headline results.
- Beware right-censoring: recent vintages are not matured — restrict to matured vintages or use survival methods; say which.
- No leakage: only application-time features for application models (no payment/recovery fields, no post-origination data).
- Pre-register each model comparison (notes/) before looking at test results; report intervals; report what failed.
- Machine: keep it light (nice 19; watch RAM on the full CSV — read only needed columns / chunk / parquet).

## Workflow
- Small commits; push to a PRIVATE GitHub repo (create only when Nat asks).
- Keep notes/STATUS.md current: what was done, results, next step, open questions for Nat.
