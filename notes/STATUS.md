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

## Done — Phase 1 (core 1+2+3 + D) ✅ — รายละเอียด: notes/02_phase1_results.md
- Pre-register (notes/02_prereg_phase1.md, commit 652b889) ก่อน fit; OOT 2015 แตะครั้งเดียว
- **Champion = M2 monotone LightGBM:** OOT Gini 36.8 [36.3, 37.4] vs WoE scorecard 33.7 [33.1, 34.3]; ΔGini +3.2 [2.9, 3.5]
  (LC sub_grade benchmark 35.7)
- Ranking รอดปี 2015 แต่ **calibration ไม่รอด:** under-predict PD 1.6–2.0 pp; cutoff ที่ตั้งปี 2014 (bad rate 11%) → ปี 2015 ได้ 11.7–11.9%
- **Monitoring:** PSI/CSI ไม่เตือนเลย (score PSI ≤ 0.03 ถึง 2017Q3). MOB-12 A/E amber ที่ vintage 2015Q2 → รู้ได้ ธ.ค. 2016;
  red ที่ 2015Q4 → มิ.ย. 2017; ระหว่างนั้นปล่อยไปแล้ว ~545k loans. Exploratory (ไม่ได้ pre-register): MOB-6 A/E → มิ.ย. 2016
- **Vintage:** default ที่ MOB 12 สูงขึ้นในทุก M1-score band (concept drift ไม่ใช่ mix shift)
- Reason codes: scorecard "points below max" + LightGBM TreeSHAP; top-1 ตรงกัน 48%

## Next step — Phase 2 (A + B)
- Pre-register Phase 2 (survival / competing risks; macro data จาก BLS LAUS + ทดสอบตาม Plan B rule) ก่อน fit
- ดาวน์โหลด BLS state unemployment → บันทึกใน notes/data_sources.md

## Open questions for Nat
1. Write-up: M2 LightGBM ชนะตามกฎ — จะให้แสดง scorecard คู่กันในฐานะ "explainable / regulatory alternative" ไหม?
   (แนะนำ: แสดงคู่กัน เพราะธนาคารมักต้องมีทั้งสองแบบ)
2. Phase 2 B: Phase 1 ชี้ว่า drift ปี 2015–16 ไม่ใช่ population shift และ US unemployment ช่วงนั้นกำลังลดลง → macro signal น่าจะอ่อน
   และ Plan B rule อาจถูก trigger (→ A + C). ทำ B ตามกฎก่อนแล้วค่อยตัดสินไหม? (แนะนำ: ทำตามกฎ)
3. จะเพิ่ม MOB-6 A/E เข้า monitoring framework แบบ pre-register ใน Phase 2 ไหม? (exploratory evidence: เร็วกว่า 6 เดือน)
