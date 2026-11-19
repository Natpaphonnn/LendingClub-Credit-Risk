# 08 — Pre-registration: extensions decided by Nat after the quality review — 2026-11-19

เขียน, commit และ **push ไป private remote ก่อน** คำนวณอะไรก็ตามของส่วนด้านล่าง (decision 7). ไม่มีการคำนวณ outcome ใด ๆ ของ 60-month loans,
ของ as-of sample, หรือของ ECL benchmark ก่อน push ไฟล์นี้. การเบี่ยงจากแผน → บันทึกใน notes/06_quality_report.md (addendum) พร้อมเหตุผล

ใช้ร่วมกันทุกข้อ: Individual, ไม่รวม "does not meet credit policy", charge-off lag 6 เดือน, as-of data cut 2019-03, frozen champion
M2 (LightGBM) PD, default month = first missed payment (MOB d = months(issue → last_pymnt_d) + 1) เว้นแต่ระบุ

---

## E1 — Confirmatory MOB-6 A/E test on 60-month loans (decision 1)

ทำไม 60m: ค่า MOB-6 / MOB-12 A/E ของ 60-month loans **ไม่เคยถูกคำนวณ**ใน project นี้ (Phase 0 audit มีแค่ resolved % และ bad-among-resolved รายปี)

- **Population:** 60-month loans issued 2012-09 → 2017-09
- **Reference window:** 60m loans issued 2012-09 → 2013-12 (เทียบเท่า Phase 1 train). จาก reference: r6 = (MOB-6 default rate) / (mean PD_M2);
  ref12 = MOB-12 default rate ของ reference window
- **Signal (per issue quarter q, 2014Q1 → 2017Q3):** A/E6(q) = Σ 1[d ≤ 6] / (Σ PD_M2 × r6). **Amber > 1.10, red > 1.25** (thresholds เดิม,
  ไม่ปรับ). Knowable ที่ quarter end + 6 + 6 เดือน
- **Truth:** MOB-12 default rate ของ quarter ≥ 1.2 × ref12 (นิยามเดียวกับ Phase 1). Knowable ที่ quarter end + 12 + 6 เดือน
- **Primary criterion (เกณฑ์ตัดสิน):** บน 15 quarters (2014Q1–2017Q3): sensitivity = P(amber+ | truth YES), specificity = P(green | truth NO).
  **PASS** ถ้า sensitivity ≥ 0.80 และ specificity ≥ 0.80 และแต่ละ class มี ≥ 3 quarters; **FAIL** ถ้ามี ≥ 3 quarters ทั้งสอง class แต่ไม่ถึงเกณฑ์;
  **INCONCLUSIVE** ถ้า class ใดมี < 3 quarters (ยังรายงาน sensitivity / specificity ที่ได้)
- รายงาน Clopper–Pearson 95% CI ของ sensitivity / specificity; lead time = 6 เดือนโดยนิยาม (รายงาน แต่ไม่ใช่เกณฑ์)
- Secondary (ไม่ตัดสิน): version ที่ใช้ M1 (scorecard) PD; first-flag date ของ MOB-6 vs first truth-YES knowable date
- ผลของ 2016–17 บน 36m ยังเป็น "descriptive" เหมือนเดิม

## E2 — As-of model: realistic deployment (decision 2)

- **Decision date D = 2014-12-31** (model ใช้กับ originations ตั้งแต่ ม.ค. 2015). ข้อมูล outcome ที่รู้ ณ D = เหตุการณ์ถึง D − 6 เดือน = 2014-06
- **Label = bad12** = default (first missed payment) ภายใน MOB 12 → รู้ได้สำหรับ loans issued ≤ 2013-06
- **Population:** 36m (เหมือน Phase 1), features = 62 APP features เดิม (bureau batch เริ่ม 2012-09)
- **Train:** issued 2012-09 → 2013-03; **Validation:** 2013-04 → 2013-06 (ทั้งคู่ ≤ 2013-06)
- **Model:** monotone LightGBM spec เดิมทุกอย่าง (monotone constraints, 12-config grid, early stopping, เลือกด้วย validation log loss — ของ bad12)
- **Evaluation on 2015 originations (descriptive comparison กับ reference M2 — ไม่มี pass/fail):**
  (i) Gini vs final 36m bad (เทียบ M2 36.8; paired bootstrap ΔGini, B = 500), (ii) Gini vs bad12, (iii) calibration ของ PD12: CITL12 = mean PD12 − observed
  bad12 (bootstrap CI), (iv) **monitoring แบบ realistic:** quarterly A/E12 = Σ bad12 / Σ PD12 (ไม่ต้องใช้ r12) สำหรับ 2015Q1 → 2017Q3, amber > 1.10,
  red > 1.25, knowable ที่ quarter end + 18 เดือน, (v) score PSI vs as-of train (10 deciles; 0.10 / 0.25)
- Reference model (M2, full 36m labels) ยังคงรายงานคู่กัน
- ข้อจำกัดที่รู้ล่วงหน้า: delinquency ที่ cure ภายหลังมองไม่เห็น (label มาจาก final status); training sample เล็กกว่า (~ 7 เดือนของ originations)

## E3 — Macro rule (a): bootstrap correctness fix (decision 4)

- ทุก bootstrap replicate: (1) สุ่ม non-event subsample 25% **ใหม่** (seed ต่อ replicate), (2) resample 24 issue quarters with replacement,
  (3) refit macro model (warm start), (4) θ = γ_u + γ_Δ12u (default). B = 200, percentile 95% CI
- (b) และ (c) คำนวณเหมือนเดิม (point fit บน subsample seed 20261119)
- **ใช้ Plan B rule ตามที่เขียนไว้เดิมทุกตัวอักษร** (a, b, c ต้องผ่านทั้งหมด)

## E4 — Staging illustration at 2015-12-31 (decision 5) — EX-POST, monthly DPD ไม่มีในข้อมูล

- missed payments m = จำนวนงวดที่ due ถึง Dec-2015 แต่ไม่ได้จ่าย = (payments due by Dec-2015) − d + 1 สำหรับ loans ที่ final status = Charged Off / Default
  และ d ≤ payments due; อื่น ๆ m = 0 (รวม loans ที่ค้างแล้ว cure — มองไม่เห็น → stage 2 ถูก understate)
- ใช้ approximation "1 missed instalment ≈ 30 DPD, 3 ≈ 90 DPD":
  **Stage 3:** m ≥ 3 → LGD × EAD at default · **Stage 2:** m ∈ {1, 2} → lifetime ECL · **Stage 1:** อื่น ๆ ที่ยัง performing → 12-month ECL
- ECL ของ stage 1/2 มาจาก hazards conditional on survival (ไม่ได้ condition on delinquency → stage 2 understated — ระบุ)

## E5 — ECL benchmark (decision 6)

- **Refit at reporting date:** hazard spec เดิม (A), refit บน loans issued 2012-09 → R ด้วย outcomes ที่ observable ถึง R − 6 เดือนเท่านั้น
  (censor ที่ min(36, months(issue → R − 6m))), สำหรับ R = 2014-12-31 (ใช้กับ 2015 originations ทั้งปี — simplification: refit ครั้งเดียว) และ
  R = 2015-12-31 (ใช้กับ staging E4)
- **Discounted LGD:** LGD_i = 1 − (recoveries − fee) × (1 + EIR_i)^(−k) / EAD_i, recovery timing k = **12 เดือนหลัง default month** (sensitivity k = 6, 24);
  pooled EAD-weighted บน train-window defaults (2012-09 → 2013-12) เหมือนเดิม
- **90-DPD default definition (sensitivity):** default MOB = d + 2 (งวดที่ 3 ที่ค้าง); EAD ณ default = scheduled balance ที่ต้นเดือน d (ไม่มี principal จ่ายหลัง d);
  refit A ด้วยนิยามนี้; horizon 36 เดือนเท่าเดิม (default ที่ d + 2 > W → censored)
- **Outputs สำหรับ 2015 portfolio:** day-1 12m ECL และ lifetime ECL (discounted) ภายใต้ (a) A + LGD เดิม, (b) A + discounted LGD, (c) refit-2014-12 + discounted LGD,
  (d) 90-DPD A + discounted LGD; backtest undiscounted lifetime EL vs realised net loss สำหรับ (a), (c), (d) (undiscounted LGD เพื่อเทียบกับ realised);
  staging table (E4) ภายใต้ refit-2015-12 + discounted LGD
- ไม่มี pass/fail — benchmark เชิงพรรณนา

## Decision 3 (no spec change)
Champion ไม่เปลี่ยน; รายงาน 12-config grid sensitivity (OOT Gini 36.5–36.9) เป็นหลักฐานว่าข้อสรุปไม่ขึ้นกับ config
