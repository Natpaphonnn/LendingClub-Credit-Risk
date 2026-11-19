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

## Decisions (Nat, 2026-11-19, after Phase 1)
1. Write-up แสดง **scorecard (explainable) คู่กับ LightGBM (champion)**
2. ทำ B **ตาม Plan B rule ที่เขียนไว้ก่อน Phase 1 เป๊ะ ๆ** — ถ้า a/b/c ข้อใดไม่ผ่าน → A + C; รายงานผล macro ไม่ว่าผ่านหรือไม่
3. เพิ่ม **MOB-6 A/E** เข้า monitoring — เพราะค้นพบจาก vintage 2015 จึงต้อง pre-register thresholds ตอนนี้ และประเมินเฉพาะ
   vintage ที่ไม่ได้ใช้ค้นพบ (2016–2017) พร้อมติด label ชัดเจน

## Decisions (Nat, 2026-11-19, after Phase 2)
1. เล่า **B ที่ fail เป็นจุดแข็ง** — pre-registered rule ที่ต้องผ่านครบสามข้อกัน spurious pass (adverse scenario ทำให้ PD ลดลง) ไว้ได้
2. ทำ **management overlay แบบสั้น**: scale lifetime PD ด้วย early A/E (MOB-6 / MOB-12) แล้วดูว่าปิด under-provision 17% บน 2015 backtest ได้เท่าไร —
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
- **Champion = M2 monotone LightGBM:** OOT Gini 36.8 [36.3, 37.3] vs WoE scorecard 33.7 [33.1, 34.2]; ΔGini +3.1 [2.8, 3.4];
  vs LC sub-grade +1.05 [0.56, 1.48]. ทั้ง 12 grid configs ชนะ scorecard ≥ 2.8 Gini
- Ranking รอด 2015 แต่ calibration ไม่รอด: under-predict PD 1.75 pp (M2) / 2.0 pp (M1); cutoff 11% (2014) → 11.7–11.9% (2015)
- Monitoring: score PSI ไม่เตือน (M2 ≤ 0.06 ตลอด 2014–18); MOB-12 A/E amber ที่ vintage 2015Q2 (รู้ได้ Dec 2016 หาก model ใช้งานตั้งแต่ 2015),
  red Sep 2017 (M2) / Jun 2017 (M1); ~545k loans booked ระหว่างนั้น; peak A/E 1.47 (2016Q3)
- Vintage: MOB-12 default สูงขึ้นทุก score band (concept drift)

## Done — Phase 2 (A + Plan B → A + C, ECL) ✅ — notes/03_phase2_results.md
- A: competing-risks lifetime PD — A/E 1.01 train, 0.98–1.02 (2014), 1.07–1.11 (2015), 1.26–1.39 (2016), 1.44 (2017);
  censor prepayment แทน → lifetime PD 18.2% vs 13.6%
- B FAIL → A + C: (a) θ −0.038 [−0.094, −0.004] (ไม่เป็นบวก; E3 bootstrap; run ก่อนหน้า −0.019 [−0.063, 0.011]), (b) PASS แบบหลอก (−27.1%), (c) 0.91
- ECL 2015 (score-only, LGD 88.8%): day-1 12m $100.7m (2.8%), lifetime $202.7m (5.6%); backtest realised $273.8m = 1.17× predicted EL $234.9m;
  overlay MOB-12 ปิด gap 54% (illustrative). Staging (E4, ex-post): stage 2 1,571 loans, stage 3 2,300 loans
- C: บน metric ที่ pre-register (ผิด — ไม่มี cost of funds) approve-all ชนะ; exploratory NPV@5%: PD cutoff $47.4m ≈ MILP $45.6m
- MOB-6 A/E (36m): descriptive เท่านั้น; confirmatory test บน 60m = FAIL (E1)

## Done — Phase 3 prep ✅ — notes/04_story.md, notes/05_claims_and_limitations.md, reports/figures/article/fig1–8

## Done — Quality (steps 1–5) ✅ — **notes/06_quality_report.md**
- Reproducibility: pipeline deterministic (byte-identical reruns), ~6 นาที, versions locked (requirements.lock.txt)
- Tests 48/48 pass; claim re-check all PASS; note-number provenance (02–05 + STATUS + README) traced; leakage & split proof
- Independent review: 1 critical + 10 major — แก้ที่ไม่ต้องเปลี่ยน spec แล้ว; ที่ต้องเปลี่ยน spec รอ Nat (ด้านล่าง)

## Done — Extensions E1–E5 ✅ — notes/10_extensions_results.md (pre-registered: notes/08_prereg_extensions.md, commit 4562602, pushed first)
- E1 MOB-6 confirmatory test (60m): **FAIL** — sensitivity 9/9, specificity 4/6 (67% < 80%)
- E2 as-of model: OOT Gini 33.1 (−3.65 vs reference); realistic first amber Jun 2017, red Sep 2017; PSI never alarmed
- E3 macro bootstrap fix: θ −0.038 [−0.094, −0.004] → B still fails → A + C
- E4 staging illustration: stage 2 1,571 loans, stage 3 2,300 loans (ex-post)
- E5 ECL benchmark: refit at 2014-12 → realised = 1.10× predicted (vs 1.17×); discounted LGD 90.4%; 90-DPD 12m ECL $80m

## Repo
- Private: https://github.com/Natpaphonnn/LendingClub-Credit-Risk (no data files tracked)

## Next step
- Rerun from raw (byte-identical) → 10-reviewer gate (notes/09_gate_rubric.md) → package → demo → article draft (notes/07_article_draft.md)
