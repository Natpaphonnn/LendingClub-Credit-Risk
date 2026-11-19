# Plan (draft 2026-11-19)

## Phase 0 — data audit (no modelling)
1. Download the Kaggle dataset (accepted + rejected files) into data/raw/. Record file names, sizes, sha256, download date in notes/data_sources.md.
2. Profile accepted file: row count, columns (with meaning from the LC data dictionary), issue_d range, loan_status values and counts, term (36/60) split, missingness by vintage.
3. Matured-vintage check: by issue year × term, share of loans with a final status (Fully Paid / Charged Off). Decide which vintages are usable for a default label.
4. Leakage map: classify every column as application-time vs post-origination.
5. Rejected file: columns, row count, date range; which fields overlap with accepted (feasibility of reject inference, item 8).
6. Feasibility of G (causal rate→default): is there a sharp grade/sub-grade cutoff in FICO or another score in the data? Report evidence only.
7. Text: share of loans with non-empty desc by year (feasibility of item 6).
8. Write notes/01_data_audit.md with all findings + a recommendation of which 2 senior items to do. Stop and report to Nat.

## Phase 1 — core (1, 2, 3)
## Phase 2 — senior items chosen by Nat
## Phase 3 — write-up (Medium + Zenn JP), browser demo, private repo
