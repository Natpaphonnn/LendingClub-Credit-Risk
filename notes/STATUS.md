# STATUS — 2026-11-19

## Decisions (Nat, 2026-11-19)
1. **Story pivot accepted:** "Lender in 2014 — does the model survive the 2015–16 vintages, and would monitoring notice in time?"
   2007–08 = crisis anchor สำหรับ stress test (Phase 2 B)
2. **Senior items = A + B** (TFRS 9 lifetime ECL: survival/lifetime PD with prepayment competing risk + macro-linked PD & stress test).
   D ทำใน Phase 1. C = stretch. **Plan B = A + C ถ้า macro signal อ่อน** — ใช้กฎด้านล่าง
3. **Exclude "Does not meet the credit policy" loans** (2,749 loans, 2007–2010) จาก headline model (documented in 01_data_audit.md §2)
4. **Skip 8 (reject inference) และ G (causal rate→default)** ตาม evidence ใน 01_data_audit.md §5–6. **Park 6** (NLP)

### Plan B rule (written 2026-11-19, before any macro data is downloaded or examined)
In Phase 2, B goes ahead **only if all three hold**. If any one fails → switch to **A + C**, and keep macro only as a simple sensitivity overlay, labelled as weak.
1. **Sign + significance:** in a PD model of matured 36m vintages (issued 2009–2014) using the Phase 1 score (frozen) plus state unemployment
   (BLS LAUS; level and 12-month change, measured over the loan's life), the macro coefficient has the expected sign (higher/rising unemployment
   → higher PD), and its 95% CI excludes 0. CI from block bootstrap by issue quarter, or cluster-robust by state × quarter.
2. **Out-of-time value:** on held-out 2015 vintages, adding macro cuts the calibration error across issue-quarter × state-group cells
   (mean |predicted − observed| bad rate) by ≥ 10% relative to score-only, and does not worsen OOT log loss.
3. **Plausible stress size:** applying the 2008–09 unemployment path gives an adverse/baseline PD multiplier between 1.1× and 3×.
   This is a sanity range around the crisis-anchor ratio of ~1.5× seen in the audit; it is not an estimation target.

## Done — Phase 0 (data audit) ✅
- Data, sha256, license → notes/data_sources.md; findings → notes/01_data_audit.md; code src/audit/; local git (no remote)

## In progress — Phase 1 (core 1+2+3 + D)
- Pre-registration: notes/02_prereg_phase1.md (committed before any model fitting)

## Open questions for Nat
- (none yet for Phase 1)
