# STATUS — 2026-11-22

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

## Decisions (Nat, 2026-11-19, after Phase 1)
1. Write-up แสดง **scorecard (explainable) คู่กับ LightGBM (champion)**
2. ทำ B **ตาม Plan B rule ที่เขียนไว้ก่อน Phase 1 เป๊ะ ๆ** — ถ้า a/b/c ข้อใดไม่ผ่าน → A + C; รายงานผล macro ไม่ว่าผ่านหรือไม่
3. เพิ่ม **MOB-6 A/E** เข้า monitoring — เพราะค้นพบจาก vintage 2015 จึงต้อง pre-register thresholds ตอนนี้ และประเมินเฉพาะ
   vintage ที่ไม่ได้ใช้ค้นพบ (2016–2017) พร้อมติด label ชัดเจน

## Decisions (Nat, 2026-11-19, after Phase 2)
1. เล่า **B ที่ fail เป็นจุดแข็ง** — pre-registered rule ที่ต้องผ่านครบสามข้อกัน spurious pass (adverse scenario ทำให้ PD ลดลง) ไว้ได้
2. ทำ **management overlay แบบสั้น**: scale lifetime PD ด้วย early A/E (MOB-6 / MOB-12) แล้วดูว่าปิด gap ของ lifetime-EL backtest (realised > predicted) บน 2015 ได้เท่าไร (คำว่า "under-provision" ถูกเลิกใช้หลัง review MA-4) —
   ติด label **illustrative / in-sample** (MOB-6 ค้นพบบน 2015 และทดสอบบน 2016–17 แล้ว จึงไม่มี vintage ที่ยังไม่เคยเห็นเหลือ)
3. C: แสดง profit metric ทั้งสองแบบ, บอกตรง ๆ ว่า metric ที่ pre-register (undiscounted) **ผิด** (ไม่มี cost of funds),
   และข้อสรุปทางธุรกิจคือ **"PD cutoff ที่ดีก็พอ"**

## Decisions (Nat, 2026-11-19, priority change)
- ทำงานให้ถูกต้องระดับ bank-grade **ก่อน** write-up / demo: reproducibility → correctness audit + tests → independent review → แก้ critical/major
  (ห้ามเปลี่ยน spec หลังเห็นผล — อะไรที่จะเป็น spec change ให้ log เป็น deviation และรายงาน Nat)

## Decisions (Nat, 2026-11-19, final — on the 7 review items)
1. YES confirmatory MOB-6 test on never-computed data (60m), pre-registered and pushed first · 2. YES as-of model (12-month bad) reported next to the reference ·
3. NO champion change; report the grid sensitivity · 4. YES redraw the subsample in every bootstrap replicate; re-apply the Plan B rule ·
5. YES staging illustration (stage 3 ≥ 3 missed, stage 2 ≈ 30 DPD proxy) · 6. YES ECL benchmark (refit, discounted LGD, 90-DPD) ·
7. YES private repo, push every pre-registration before its run. Then: rerun from raw → 10-reviewer gate → package → demo → article

## Done — Phase 0 (data audit) ✅
- Data, sha256, license → notes/data_sources.md; findings → notes/01_data_audit.md; code src/audit/; local git (no remote)

## Done — Phase 1 (core 1+2+3 + D) ✅ — notes/02_phase1_results.md
(ตัวเลขทั้งหมดหลัง gate fix R5-1: M2 retrain ด้วย monotone_constraints_method="intermediate")
- **Champion = M2 monotone LightGBM:** OOT Gini 36.7 [36.3, 37.3] vs WoE scorecard 33.7 [33.1, 34.2]; ΔGini +3.1 [2.8, 3.3];
  vs LC sub-grade +1.01 [0.52, 1.46]. Grid sensitivity: reports/quality/grid_sensitivity.md
- Approval ที่ bad rate 11% (2014): 82.1% vs 77.4%; ที่ matched bad rate (unrounded scorecard) ต่าง 3.0 pp
- Ranking รอด 2015 แต่ calibration ไม่รอด: under-predict PD 1.70 pp (M2); approved bad 11.88% vs target 11%
- Monitoring: score PSI ไม่เตือน (M2 ≤ 0.057 ตลอด 2014–18); MOB-12 A/E amber ที่ vintage 2015Q2 (รู้ได้ Dec 2016 หาก model ใช้งานตั้งแต่ 2015),
  red Sep 2017 (M2) / Jun 2017 (M1); ~545k loans booked ระหว่างนั้น; peak A/E 1.46 (2016Q3). MOB-12 A/E กับ truth ใช้ numerator เดียวกัน →
  lag 18 เดือน = observation window
- Vintage: MOB-12 default สูงขึ้นทุก score band (concept drift)

## Done — Phase 2 (A + Plan B → A + C, ECL) ✅ — notes/03_phase2_results.md
- A: competing-risks lifetime PD — A/E 1.01 train, 0.98–1.03 (2014), 1.09–1.12 (2015), 1.27–1.39 (2016), 1.43 (2017);
  censor prepayment แทน → lifetime PD 18.2% vs 13.6% (loans Jan–Sep 2015 ที่ดูได้ครบ 36 เดือน; actual 14.7%)
- B FAIL → A + C: (a) θ −0.045 [−0.099, −0.009] (ไม่เป็นบวก), (b) PASS แบบหลอก (−28.0%), (c) 0.89
- ECL 2015 (score-only, LGD 88.8%): day-1 12m $99.6m (2.7%), lifetime $200.6m (5.5%); backtest realised $273.8m = 1.18× predicted EL $232.4m
  (in-sample 1.03× — EAD structural); overlay MOB-12 ปิด gap 57% (illustrative). Staging (E4, ex-post): stage 2 1,571 loans, stage 3 2,300 loans
- C: metric ที่ pre-register (ผิด — ไม่มี cost of funds) approve-all ชนะ; exploratory NPV@5%: PD cutoff $47.5m > MILP $45.8m
  (MILP − cutoff −1.74 [−2.66, −0.82]); single PD threshold ที่ tune objective เดียวกัน = MILP → cell optimiser ไม่ช่วย, ระดับ cutoff ต้องตั้งด้วย cost of funds
- MOB-6 A/E (36m): descriptive เท่านั้น; confirmatory test บน 60m = FAIL (E1)

## Done — Phase 3 prep ✅ — notes/04_story.md, notes/05_claims_and_limitations.md, reports/figures/article/fig1–8

## Done — Quality (steps 1–5) ✅ — **notes/06_quality_report.md**
- Reproducibility: deterministic pipeline, versions locked (requirements.lock.txt), raw inputs pinned by raw_inputs.sha256
- Independent review (1 critical + 10 major) แก้แล้ว

## Done — Extensions E1–E5 ✅ — notes/10_extensions_results.md (pre-registered: notes/08_prereg_extensions.md, commit 4562602, pushed first)
- E1 MOB-6 confirmatory test (60m): **FAIL** — sensitivity 9/9, specificity 4/6 (67% < 80%; CI 22–96%) — verdict เดิมหลัง retrain
- E2 as-of model: OOT Gini 33.0 (−3.76 vs reference); realistic first amber Jun 2017, red Sep 2017; PSI never alarmed (max 0.075)
- E3 macro bootstrap fix: B still fails → A + C
- E4 staging illustration: stage 2 1,571 loans, stage 3 2,300 loans (ex-post; 682 ของ stage 3 น่าจะ write-off แล้ว)
- E5 ECL benchmark: **refit ที่ 2014-12 ไม่ได้ปิด gap — กลับแย่ลง 1.27×** (vs 1.18×); 1.10× เดิมเป็น artefact (ถอนแล้ว, gate R7-1/R2-1);
  discounted LGD 90.4%; 90-DPD 12m ECL $79.2m

## Bank gate (rubric notes/09_gate_rubric.md, commit 9a493da)
- **Round 1: FAIL** — mean 7.13; BLOCKING R5-1 (monotone method), R7-1/R2-1 (E5 refit unidentified) → แก้แล้ว (bug fixes);
  deviation: E5 refit ใช้เฉพาะ MOB 1–21 ที่ identify ได้ + reference tail (log ใน notes/10). รายละเอียด reports/quality/gate_round1.md
- **Round 2: PASS** — mean 8.22 (R1 8.4 · R2 7.9 · R3 8.4 · R4 8.6 · R5 8.5 · R6 8.3 · R7 7.9 · R8 8.0 · R9 8.2 · R10 8.0), ไม่มี BLOCKING.
  Majors แก้หลัง gate (relabel / post-hoc descriptive เท่านั้น ไม่เปลี่ยน pre-registered spec): reports/quality/gate_round2.md, gate_round2_fixes.md
  - ข้อที่เปลี่ยนความหมาย: E5 refit 1.27× เป็น lower bound (knowable tail 1.41×); "stage 3 ≥ 3 missed" ≈ ≥ 60 DPD ไม่ใช่ 90; "90-DPD" sensitivity
    จริง ๆ ≈ 60 DPD (4th missed ≈ 90 DPD: 12m ECL $67.8m); policy C: ระดับ cutoff ขึ้นกับทั้ง cost of funds และ calibration ของ PD;
    ranking "รอด" ยืนยันได้เฉพาะ 2014Q1–2015Q3 (month-12 KS ของ 2016Q2–Q4 ลดเหลือ 0.87–0.89×)

## Repo
- Private: https://github.com/Natpaphonnn/LendingClub-Credit-Risk (no data files tracked)

## Done — package / demo / article ✅
- README (reproduce steps: run_all ลบ data/interim แล้ว rebuild จาก raw + tests + checkers), requirements.lock.txt, raw_inputs.sha256, bls_values.sha256
- Demo: demo/index.html (static, aggregates only) · Article draft: notes/07_article_draft.md

## Next step / open questions for Nat
- 2026-11-22: repo public (Nat). Demo policy slider default = pre-registered cutoff 0.1994 ตรงเป๊ะ + note ว่า NPV curve เป็น ex-post 2015;
  rebuild จาก raw x2 byte-identical (62 tests, 36/36 claims, provenance 0 unmatched, re-derivation 31/31); demo deploy ผ่าน GitHub Pages workflow.
  History scan: ไม่มี data / secret; มีแค่ local absolute path (username) ใน stderr log ของ commit เก่า → run_all scrub path แล้ว;
  **Open:** จะ rewrite history (git filter-repo + force push) เพื่อลบ path เก่าไหม — รอ Nat ตัดสิน
- อ่าน article draft แล้วตัดสินใจ publish (Medium)
- ปิด minor ที่ค้างแล้ว (2026-11-20, ตามที่ Nat สั่ง): independent re-derivation ของทุก ECL/policy claim ใน article จาก raw (31/31 ตรง —
  reports/quality/rederive_ecl_policy.md), scorecard bin-stability table, shared scoring helper (src/lib/scoring.py), test ของ as-of information set;
  article เขียนใหม่ (สิ่งที่รอดก่อน แล้วสิ่งที่ fail)
