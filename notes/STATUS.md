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

## Done — Phase 0 (data audit) ✅
- Data, sha256, license → notes/data_sources.md; findings → notes/01_data_audit.md; code src/audit/; local git (no remote)

## Done — Phase 1 (core 1+2+3 + D) ✅ — รายละเอียด: notes/02_phase1_results.md
- Pre-register (notes/02_prereg_phase1.md, commit 652b889) ก่อน fit; OOT 2015 แตะครั้งเดียว
- **Champion = M2 monotone LightGBM:** OOT Gini 36.8 [36.3, 37.4] vs WoE scorecard 33.7 [33.1, 34.3]; ΔGini +3.2 [2.9, 3.5]
  (LC sub_grade benchmark 35.7)
- Ranking รอดปี 2015 แต่ **calibration ไม่รอด:** under-predict PD 1.6–2.0 pp; cutoff ที่ตั้งปี 2014 (bad rate 11%) → ปี 2015 ได้ 11.7–11.9%
- **Monitoring:** PSI/CSI ไม่เตือนเลย (score PSI ≤ 0.03 ถึง 2017Q3). MOB-12 A/E amber ที่ vintage 2015Q2 → รู้ได้ ธ.ค. 2016;
  red ที่ 2015Q4 → มิ.ย. 2017; ระหว่างนั้นปล่อยไปแล้ว ~545k loans. Exploratory (ไม่ได้ pre-register): MOB-6 A/E → มิ.ย. 2016
- **Vintage:** default ที่ MOB 12 สูงขึ้นในทุก M1-score band (concept drift ไม่ใช่ mix shift)
- Reason codes: scorecard "points below max" + LightGBM TreeSHAP; top-1 ตรงกัน 48%

## Done — Phase 2 (A + Plan B → A + C, ECL, MOB-6 test) ✅ — รายละเอียด: notes/03_phase2_results.md
- Pre-register: notes/03_prereg_phase2.md (commit 1203ada) ก่อนดาวน์โหลด macro / fit
- **A (competing-risks lifetime PD):** A/E 1.00 train, 0.98–1.02 valid 2014; under-predict OOT 2015 (1.09–1.12) และ 2016–17 (1.26–1.42).
  ไม่สน prepayment → lifetime PD over-state 13.4% → 18.0%
- **B FAIL → Plan B (A + C):** (a) θ = −0.019 [−0.063, 0.011] FAIL; (b) PASS แต่ด้วยเหตุผลผิด (level coef ติดลบ = time-trend confounding);
  (c) adverse/baseline 0.96 FAIL. Macro data: BLS LAUS (public domain)
- **ECL 2015 portfolio** (score-only, LGD 88.8%): day-1 12m ECL $100m (2.8%), lifetime $202m (5.6%); realised loss $274m vs predicted EL $234m (×1.17);
  Stage 2 allocate ไม่ได้ (ไม่มี DPD รายเดือน) — ระบุชัด
- **C (MILP):** แพ้ approve-all บน metric ที่ pre-register (undiscounted profit $222m vs $230m); exploratory NPV @5%: C $46m vs approve-all $28m ≈ M2 cutoff $48m
- **MOB-6 A/E (out-of-discovery 2016–17):** sensitivity 7/7, lead 6 เดือน; specificity ทดสอบไม่ได้

## Next step
- Phase 3 write-up (Medium + Zenn JP), browser demo, private repo — รอ Nat สั่ง

## Open questions for Nat
1. Write-up: เล่า B ที่ fail เป็นจุดแข็ง ("pre-registered rule กัน false positive ได้") ไหม? (แนะนำ: ใช่ — เป็นหนึ่งใน highlight)
2. ECL ไม่มี forward-looking overlay: จะให้ pre-register "management overlay จาก early A/E" เป็น Phase 2.5 ไหม หรือปล่อยเป็น limitation?
   (แนะนำ: ทำแบบสั้น ถ้ามีเวลา — ธนาคารไทยใช้ overlay จริง)
3. C metric ที่ pre-register (undiscounted) เลือกไม่ดี — ใน write-up ให้แสดงทั้งสองแบบพร้อมคำอธิบาย (ตามที่ทำใน figure) โอเคไหม?
