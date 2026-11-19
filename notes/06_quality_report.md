# 06 — Quality report (reproducibility, correctness audit, tests, independent review) — 2026-11-19

ลำดับงานตาม priority ของ Nat: (1) reproducibility → (2) correctness audit + tests → (3) independent review → (4) แก้ critical/major ที่ไม่ต้องเปลี่ยน spec,
log อะไรที่เป็น spec change เป็น deviation → rerun (1)–(2) → (5) รายงานนี้

## สรุปสั้น
- **Reproducible:** pipeline ทั้งหมดจาก `data/raw` รันได้ใน process ใหม่ด้วยคำสั่งเดียว (`scripts/run_all.sh`, ~6 นาที) และ **byte-identical** ทุก report/figure
  ระหว่าง runs (ทดสอบ 3 ครั้ง). Versions: `requirements.lock.txt` (Python 3.12.14, macOS arm64)
- **แต่ผลเดิมไม่ reproducible:** run แรกพบว่า bootstrap CIs, LightGBM config ที่เลือก และ macro θ ขึ้นกับ row order ที่ไม่ deterministic → แก้แล้ว,
  ตัวเลขทั้งหมดถูก re-state (decision ทุกข้อไม่เปลี่ยน) — ตารางด้านล่าง
- **Correctness:** claim re-check 30/30 PASS (หลังแก้ 2 ข้อความที่ผิด), note-number provenance 1,187/1,187 tokens traced, leakage + split proof ผ่าน,
  **48/48 tests pass**. พบและแก้ bugs 6 จุด (รวม off-by-one ใน staging)
- **Independent review** (agent ที่ไม่ได้สร้างงานนี้, read-only, บทบาท bank model validator): scores Data 4 · Methodology 3 · Validation 2 ·
  Monitoring 3 · TFRS 9 2 · Documentation 3; **1 critical + 10 major**. แก้แล้วทุกข้อที่ไม่ต้องเปลี่ยน spec; 7 ข้อที่ต้องเปลี่ยน spec → รอ Nat
- ข้อสรุปหลักที่ยังยืน: champion ชนะ scorecard (ทุก grid config), ranking รอด/calibration drift, PSI ไม่เตือน, B fail, lifetime EL < realised loss.
  ข้อสรุปที่ถูกลดระดับ: MOB-6 "out-of-discovery test" → descriptive เท่านั้น; "provisions 17% short" → lifetime EL backtest (realised = 1.17×);
  "would you notice in time" → relative to a counterfactual 2015 deployment

---

## 1. Reproducibility

**วิธี:** ย้าย `data/interim` ออก, รัน `scripts/run_all.sh` (convert CSV → parquet → Phase 0 → Phase 1 → Phase 2 → overlay → article figures) ใน process ใหม่,
เทียบ `reports/` กับ commit ก่อนหน้า (`git diff`) และเทียบ run กับ run (`diff -r`)

| run | code | ผล |
|---|---|---|
| run 1 | HEAD เดิม (8cbb8f7) | **ไม่ตรง:** point estimates ตรง (≤ 1e-14) แต่ bootstrap CIs, decile tie-breaks, mode ties ใน audit, rule B θ เปลี่ยน |
| root cause | — | `convert_to_parquet.py` ใช้ `preserve_insertion_order=false` + 4 threads → row order ใน parquet ไม่คงที่ → resampling/ subsampling/ LightGBM bagging ขึ้นกับ order |
| fix | `preserve_insertion_order=true`; builds อ่านด้วย `file_row_number` + `ORDER BY`; explicit tie-break สำหรับ mode ใน audit | |
| run 2 vs run 3 | หลัง fix | **byte-identical ทุกไฟล์** (reports + figures) |
| final run | หลังแก้ตาม review ทั้งหมด | byte-identical กับ outputs ก่อนรัน (ดู reports/quality/runtime_final.log) |

**Runtime (final run, nice 19, 4 threads, Apple Silicon, 24 GB):** total **352 s** — convert CSV→parquet 17 s · audit 8 s · Phase 1 94 s (LightGBM grid 34 s, evaluation + bootstrap 37 s) · Phase 2 230 s (**rule B block bootstrap 199 s**) · figures 3 s. Final run outputs were byte-identical to the outputs before the run; afterwards only the fig 7 title/subtitle text was shortened (figure script re-run twice → identical hashes).

**ตัวเลขที่เปลี่ยนเพราะ deterministic re-run และเหตุผล** (ทุกตัวในเอกสาร 02–05 ถูก update แล้ว; ค่าเดิมดูได้จาก commit 8cbb8f7)
| item | เดิม | ใหม่ | เหตุผล |
|---|---|---|---|
| LightGBM config ที่เลือก | leaves 15, 318 rounds | leaves 63, 184 rounds | bagging ขึ้นกับ row order; validation log loss เท่ากันที่ 0.37557 (grid spread 0.0006) |
| OOT Gini M2 [CI] | 36.85 [36.29, 37.39] | 36.78 [36.29, 37.31] | model + bootstrap draws |
| ΔGini M2 − M1 [CI] | 3.17 [2.90, 3.46] | 3.10 [2.81, 3.38] | same |
| CITL M2 (OOT) | −1.59 pp | −1.75 pp | model |
| M2 cutoff / 2014 approval | 0.2039 / 82.3% | 0.2008 / 82.1% | model |
| Rule B θ [CI] | −0.0185 [−0.063, 0.011] | −0.0379 [−0.088, −0.005] | frozen M2 score เปลี่ยน + subsample draws; **verdict FAIL ไม่เปลี่ยน** |
| Rule B (b) / (c) | −23.7% / 0.96 | −27.1% / 0.91 | same; PASS / FAIL ไม่เปลี่ยน |
| Lifetime PD 2015 (competing / naive) | 13.4% / 18.0% | 13.6% / 18.2% | lp covariate (M2) |
| Predicted EL 2015 | $233.8m | $234.9m | same |
| Overlay gap closed MOB-12 / MOB-6 | 58% / 11% | 54% / 6% | same |
| Peak MOB-12 A/E (champion) | 1.45 | 1.47 | model |
| NPV@5% cutoff / MILP | $47.6m / $46.3m | $47.4m / $45.6m | model |
Scorecard (M1), vintage curves, audit numbers, LGD: ไม่เปลี่ยน

## 2. Correctness audit

**2.1 Claim re-check** — `src/quality/check_claims.py` → `reports/quality/claims_check.md`: ทุก claim C1–C26 + ตัวเลข "47%" re-derive จาก data
(duckdb / sklearn — ไม่ใช้ metric code ของเราเอง) หรืออ่านจาก source file; ต้องตรงตาม precision ที่เขียน **และ** ข้อความต้องอยู่ใน row ของ notes/05 จริง

| ผลรอบแรก (หลัง re-run) | การแก้ |
|---|---|
| 22 FAIL | ส่วนใหญ่เพราะตัวเลขเปลี่ยนจาก deterministic re-run → update docs; 3 ข้อเป็น bug ของ checker เอง (precision / string) → แก้ checker |
| C12 FAIL (จริง) | "Source Verified 40–47%" มาจาก 4 quarters ที่เลือก; ทุก quarter 2014–18 = **35–47%** → แก้ทุก note |
| C18 FAIL (จริง) | 2015 A/E@36 = 1.07497 → ช่วงที่ถูกคือ **1.07–1.11** (เดิมเขียน 1.08–1.11) → แก้ |
| C14 (ambiguity) | "red Jun 2017" เป็นของ scorecard; champion red **Sep 2017** → เขียนทั้งสอง |
| **ผลสุดท้าย** | **30/30 PASS** |

**"Up to 47% above expected":** re-derive = Σ defaults by MOB 12 / (Σ PD_M2 × r12), peak 2016Q3 = **1.468** (r12 = 0.310 จาก train);
corroborated ด้วย model อิสระ (competing-risks hazard) A/E@12 ของ 2016Q3 = **1.44**. ข้อจำกัด: expected ใช้ r12 (สัดส่วน MOB-12/final ใน train) — ถ้า timing ของ
default เปลี่ยน A/E นี้ปน level + timing

**2.2 Number provenance** — `src/quality/check_note_numbers.py` → `reports/quality/note_numbers_check.md`: ทุกตัวเลขใน notes 02–05 + STATUS + README
(1,187 tokens) — 1,179 ตรงกับค่าใน reports (รวม historical outputs ที่อ้างใน before/after tables, อ่านจาก git commit ที่ระบุ), 8 ตรงกับ counts ที่ re-derive แยก.
**ข้อจำกัด:** match = มีค่าใดค่าหนึ่งใน reports ที่ปัดแล้วเท่ากัน (lenient) — claim checker คือ test ที่เข้มจริง

**2.3 Leakage** — `tests/test_leakage_and_splits.py`, `reports/quality/leakage_split_proof.md`
- 62 candidate features = 58 APP + 4 derived (จาก fico_range_low, earliest_cr_line, loan_amnt/annual_inc, emp_length — APP ทั้งหมด)
- LightGBM model file feature names == candidate list (62); scorecard 14 characteristics ⊂ list; 51 banned columns (LC/POST/ID/TARGET) ∩ features = ∅
- Training code ใช้ `df[FEATURES]` เท่านั้น (asserted on source); SQL ของ derived features อ่านเฉพาะ source columns ที่ประกาศ
- Lifetime/ECL hazard ใช้ int_rate (LC contract term) — ไม่ใช่ application model; documented ใน prereg

**2.4 Splits** — loan `id` ถูกเพิ่มใน base tables: ids unique; train (2012-09..2013-12, 120,683) / validation (2014, 162,570) / OOT (2015, 282,934)
**pairwise overlap = 0**, train สิ้นสุดก่อน validation เริ่ม และ validation สิ้นสุดก่อน OOT เริ่ม; OOT population เดียวกันใน Phase 1 และ 2; macro fit (≤ 2014-12) < OOT

**2.5 Tests — 48/48 pass** (`.venv/bin/python -m pytest -q tests`)
| area | tests |
|---|---|
| nullable integers (bug จริงใน overlay) | Int64 `<NA>` comparison, naive-pitfall documentation, float NaN boundary |
| censoring / maturity | 12 parametrized cases ของ `code_events` (default in/after window, prepay boundary 33, matured 34–36, payoff after window, no last payment, Current/Late) |
| reporting-date staging (bug จริง off-by-one) | `payments_due`, stage-3 boundary (first missed due Dec vs Jan) |
| EAD / LGD | annuity payment 332.14, amortisation to 0, LGD formula + clipping + zero exposure |
| PSI / CSI | identical = 0, known value, empty bin finite, CSI(reference, reference) = 0 |
| WoE binning | monotone bad rate, ≥ 5% bins, missing bin rule, rare-missing merge, right-closed cuts, IV formula, categorical OTHER/unseen |
| AUC / KS / calibration | equals sklearn / scipy with ties; weighted = row duplication; calibration slope ≈ 1 |
| hazard / A/E by MOB | loan-month expansion, CIF identity (S + CIF_d + CIF_p = 1), naive > CIF, MNL parameter recovery, A/E by MOB |
| leakage / splits (data) | features ⊂ APP, model feature names, scorecard ⊂ features, disjoint/ordered splits, OOT not in training code |

**2.6 Bugs found and fixed in this step**
1. Non-deterministic row order (above) — fixed
2. `policy_C.py` labelled the champion cutoff with a hard-coded "PD ≤ 0.2039" while using the live cutoff — fixed (label from data)
3. Hard-coded numbers in figure texts ("1.45", "~545k", "a third", "86% / 82%") — now computed from data
4. Monitoring headers said "of 59" features; there are **62** (also in note 02) — fixed
5. Two inaccurate ranges in notes (Source Verified, 2015 A/E) — fixed (2.1)
6. **Off-by-one in reporting-date staging** (`ecl.py`): stage 3 included loans whose first missed payment was due Jan-2016, contrary to the
   pre-registered "≤ Dec-2015"; stage-1 remaining-life ECL started a month late. Fixed to match the pre-registration (not a spec change):
   stage 3 4,828 → **3,871** loans, stage 1 allowance $112.1m (3.91%) → **$112.3m (3.75%)**; day-1 ECL and backtest unaffected; test added

## 3. Independent review (bank model-risk validator persona; read-only; did not build the project)

| area | score | reviewer's one-line reason (paraphrased) |
|---|---:|---|
| Data handling | 4 | strong licensing, exclusions, maturity analysis, deterministic pipeline; development labels post-date the story's decision date |
| Methodology | 3 | scorecard / LightGBM / hazard implemented correctly; ECL design weak; macro test thin; profit metric mis-specified |
| Validation | 2 | good splits, leakage controls, CIs; but a "pre-registered" test was already seen, undisclosed re-run, fragile macro inference, unverifiable commit order |
| Monitoring | 3 | good "knowable date" design; A/E without bounds; MOB-6 evidence circular |
| TFRS 9 logic | 2 | honest about gaps, but lifetime-EL backtest called "provisions", hindsight staging, no refit |
| Documentation | 3 | claim table / provenance / leakage proof excellent; stale STATUS, old README, some status upgrades |

Spot-check: 14 numbers re-derived by the reviewer matched; 2 mismatches (stale STATUS; a TL;DR PSI wording) — both fixed.

**Issues and what was done**
| ID | severity | issue | action | spec change? |
|---|---|---|---|---|
| CR-1 | critical | MOB-6 "out-of-discovery test" values were computed and committed (5b35a6e) before thresholds were registered (1203ada) → not confirmatory | **Relabelled** everywhere (C16, story §5, 03, fig 4 legend, mob6_test.md) as descriptive/exploratory. Genuine test → **deferred to Nat** | relabel: no; new test: yes |
| MA-1 | major | development labels (2012–13 full 36m outcomes) only complete ~2017 → "would you notice in time" dates impossible for a 2014 lender | **Reframed**: "built on 2012–13, deployed from 2015 (counterfactual)"; caveat in story, 02, 05, fig 4. As-of rebuild → **Nat** | reframe: no; rebuild: yes |
| MA-2 | major | OOT re-evaluated after the re-run with a different champion config, undisclosed; selection ≈ noise | **Disclosed** (02 §10 #5 with before/after); **grid sensitivity** added: all 12 configs OOT Gini 36.48–36.87, ≥ scorecard + 2.8 → conclusion robust. Tie-break rule → **Nat** | disclosure: no; tie-break: yes |
| MA-3 | major | macro θ fragile; "significantly wrong sign" over-claims; Hessian SEs invalid | **Wording fixed** ("θ is not positive"), both runs reported, SEs removed from report and notes. Bootstrap redesign → **Nat** | wording: no; CI method: yes |
| MA-4 | major | "provisions fell 17% short" mislabels a lifetime-EL backtest | **Fixed**: "lifetime EL under-predicted realised loss (realised = 1.17×; 14% of realised missed)"; fig 7, story, 03, 05, STATUS | no |
| MA-5 | major | staging uses hindsight; inconsistent with "stage 2 not allocable" | **Labelled ex-post** in ecl.md / 03 / story with count (1,571 of 3,871 stage-3 loans < 90 DPD at Dec-2015); off-by-one bug fixed. 90-DPD stage 3 + 30-DPD stage 2 proxy → **Nat** | label: no; redefinition: yes |
| MA-6 | major | ECL not a realistic benchmark (no refit at reporting date, default = first missed payment, undiscounted LGD, no accrued interest) | **Caveat added** (story §8, 03, 05: the ×1.17 gap mixes drift and no recalibration). Refit / discounted LGD / 90-DPD sensitivity → **Nat** | yes |
| MA-7 | major | MOB-6 evidence circular (lead 6 by construction, shared events, 100% base rate); discovery misses omitted | **Reported**: discovery confusion matrix (M2 1/2 sensitivity, 6/6 specificity; M1 2/2, 6/6), lead-by-construction and expectation-dependence stated | no |
| MA-8 | major | "ignoring prepayment overstates lifetime PD by a third" is a straw man | **Reworded**: "treating prepayment as censoring (same hazards) …"; fig 6 legend/title; closing takeaway | no |
| MA-9 | major | STATUS stale, README tells the old story, both outside provenance check | **Regenerated** both; both added to the provenance check | no |
| MA-10 | major | pre-registration order only self-attested (local commits, code + results committed together) | **Disclosed** in story + 05. External anchoring (push to private remote / timestamp) → **Nat** (needs repo) | process |
| MI-1 | minor | champion vs LC has no paired CI | **Added**: +1.05 [0.56, 1.48] (evaluate.py) | no |
| MI-6 | minor | TL;DR "PSI ≤ 0.03 through 2014–2017" wrong for M1 2017Q4 | **Fixed** ("2014Q1–2017Q3; M2 ≤ 0.06 to 2018") | no |
| MI-9 | minor | "a quarter of the columns leak" (actually 31%, and LC columns are not post-origination) | **Fixed** wording (C3, story) | no |
| MI-5 | minor | fig 8 titled the exploratory metric "Corrected" | **Fixed** ("Exploratory: NPV at 5% funding cost") | no |
| MI-2, 3, 4, 7, 8, 10 | minor | i.i.d. bootstrap; A/E without bounds; censoring of defaults after MOB 36; lenient provenance; unseen categories unmonitored; no fair-lending / post-training monotonicity test | **Listed as limitations** in 05 (not fixed) | some yes |

## 4. Deviations requiring Nat's decision (spec changes — NOT done)
1. **CR-1:** new pre-registered MOB-6 test on data whose A/E6 has never been computed (e.g. 60-month loans, or a re-referenced expectation on 2017–18)
2. **MA-1:** as-of rebuild (12-month bad window, or hazard censored at 2014-12) so the timeline is real — or keep the reframing
3. **MA-2:** deterministic tie-break rule for the grid (e.g. simplest config within 1e-3 log loss) — would change the champion config
4. **MA-3:** redraw the 25% subsample inside each bootstrap replicate for rule (a)
5. **MA-5:** stage 3 = ≥ 3 missed payments; stage 2 = ex-post ≥ 30 DPD proxy (labelled) — or drop the staging table
6. **MA-6:** refit A at 2014-12 / 2015-12 as the ECL benchmark; LGD discounted at EIR; 90-DPD default sensitivity
7. **MA-10:** push pre-registration commits to a private remote (or external timestamp) before any further confirmatory run

## 5. Remaining limitations (full list: notes/05_claims_and_limitations.md)
Look-ahead in the development sample (reframed, not removed); hindsight staging; no forward-looking ECL; one downturn for macro; accepted-only
population; default timing from last payment date; i.i.d. bootstrap; A/E thresholds without statistical bounds; self-attested pre-registration order.

## Files
`scripts/run_all.sh` · `requirements.lock.txt` · `src/lib/riskutils.py` · `tests/` · `src/quality/{check_claims,check_note_numbers,leakage_split_proof,grid_sensitivity}.py` ·
`reports/quality/{claims_check,note_numbers_check,leakage_split_proof,grid_sensitivity}.md`, `runtime_run{1,2,3}.log`, `runtime_final.log`

## Addendum — deferred items resolved (Nat's final decisions, 2026-11-19)
All 7 spec-changing items were decided by Nat and pre-registered in `notes/08_prereg_extensions.md` (commit 4562602, pushed to the private remote
before computing). Results: `notes/10_extensions_results.md`.
| item | decision | result |
|---|---|---|
| CR-1 MOB-6 confirmatory test | 60-month loans, never computed | **FAIL** — sensitivity 9/9, specificity 4/6 (67% < 80%) |
| MA-1 as-of model | 12-month bad, data to 2014-06, reported next to the reference | OOT Gini 33.1 (−3.65); realistic first alarm Jun 2017 |
| MA-2 tie-break | no champion change | grid sensitivity reported (36.5–36.9) |
| MA-3 macro bootstrap | subsample redrawn per replicate (correctness fix) | θ −0.038 [−0.094, −0.004] → B still FAIL |
| MA-5 staging | illustration: stage 3 ≥ 3 missed, stage 2 1–2 missed (≈ 30 DPD proxy) | stage 2 1,571, stage 3 2,300 loans |
| MA-6 ECL benchmark | refit at reporting date, discounted LGD, 90-DPD sensitivity | refit → 1.10× (vs 1.17×); LGD 90.4%; 90-DPD 12m ECL $80m |
| MA-10 pre-registration evidence | private remote; pre-registrations pushed before runs | https://github.com/Natpaphonnn/LendingClub-Credit-Risk (private) |

## Re-run after extensions (2026-11-20)
Two fresh runs from `data/raw` with the final code (incl. E1–E5): **byte-identical** (`reports/quality/runtime_runA.log`, `runtime_runB.log`;
522–523 s each, rule B bootstrap now redraws the subsample per replicate). Tests **51/51**; claim re-check **36/36** (one doc rounding fixed:
θ CI upper bound −0.00448 → "−0.004", not "−0.005"); note-number provenance 1,301/1,301 traced. `requirements.lock.txt` regenerated (adds pytest).
