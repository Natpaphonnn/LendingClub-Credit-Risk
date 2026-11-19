# 02 — Phase 1 results (core 1 + 2 + 3 + D) — 2026-11-19

Pre-registration: `notes/02_prereg_phase1.md` (commit 652b889 — commit ก่อน fit model ใด ๆ).
ทุกตัวเลขมาจาก code ใน `src/phase1/` → ตารางเต็ม `reports/phase1/`, figures `reports/figures/p1_*.png`.
OOT 2015 ถูกประเมินครั้งเดียวต่อ pipeline run ใน `evaluate.py` หลังเลือกทุกอย่างบน validation แล้ว; มี deterministic re-run 1 ครั้ง (ดู §10 ข้อ 5)

Reproduce (ตามลำดับ, รวม ~2 นาที):
```
for s in build_dataset train_scorecard train_lgbm evaluate monitoring vintage explore_early_signal; do
  nice -n 19 .venv/bin/python -I src/phase1/$s.py; done
```

---

## TL;DR

1. **Champion = M2 LightGBM (monotone)** ตามกฎที่ pre-register ไว้: OOT Gini 36.8 [36.3, 37.3] vs scorecard 33.7 [33.1, 34.2];
   paired ΔGini = **+3.1 [2.8, 3.4]** points (เกณฑ์ ≥ 2.0 และ CI > 0 → ผ่าน)
2. **Model "รอด" 2015 ในแง่ ranking แต่ไม่รอดในแง่ calibration:** KS/Gini บน OOT ไม่ลดลงเลย แต่ทั้งสอง model
   under-predict PD 1.75–2.0 pp (≈ 12–13% relative); cutoff ที่ตั้งไว้ปี 2014 ให้ bad rate 11.0% → ปี 2015 ได้ 11.7–11.9%
3. **Monitoring: PSI/CSI ไม่จับ drift เลย** (score PSI ≤ 0.03 ตลอด 2014Q1–2017Q3; M2 ≤ 0.06 ถึง 2018). Signal แรกที่จับได้คือ MOB-12 A/E:
   amber สำหรับ vintage 2015Q2 → **รู้ได้ ธ.ค. 2016**, red สำหรับ 2015Q4 → มิ.ย. 2017. ระหว่างนั้น LC ปล่อยไปแล้ว
   ~545k loans (36m, 2015Q2–2016Q4) ที่อยู่ใน vintage ที่แย่ลง
4. **Vintage curves:** default ที่ MOB 12 สูงขึ้น**ในทุก risk band** (B1: ~7% ใน 2013 → ~10.5% ใน 2016; B5: ~1.1% → ~2.2%)
   ขณะที่ characteristics ของผู้กู้ดู "ดีขึ้น" (utilization ลด) → นี่คือ **concept drift** (score→PD เปลี่ยน) ไม่ใช่ population shift
   ซึ่งเป็นเหตุผลที่ PSI มองไม่เห็น → ต่อเข้ากับ Phase 2 B (macro / forward-looking) ได้ตรง ๆ
5. **D (reason codes + monotone):** ทำแล้วทั้งสอง model; top-1 reason ตรงกัน 48%, M1 top-1 อยู่ใน M2 top-4 90%

---

## 1. Data & split (prereg §1–2)

36m, Individual, ไม่รวม "does not meet credit policy"; bad = Charged Off / Default vs Fully Paid
| set | window | n (labelled) | bad rate |
|---|---|---:|---:|
| Train | 2012-09 → 2013-12 | 120,683 | 12.44% |
| Validation | 2014 | 162,570 | 13.73% |
| OOT | 2015 | 282,787 | 14.88% |
| Monitoring | 2014Q1 → 2018Q4 | 1,364,557 (ทุกสถานะ) | – |
Base table: 1,485,240 rows (`data/interim/p1_base.parquet`, git-ignored). OOT ตัด 147 loans ที่ยังไม่ final (0.05%)

## 2. M1 — WoE/IV scorecard (prereg §4)

- 62 candidate features → 28 ผ่าน IV ≥ 0.02 → 14 ตัดเพราะ |corr WoE| > 0.6 → เหลือ **14 characteristics** (น้อยกว่า cap 20 เพราะ
  correlation filter) → ไม่มี coefficient ผิดเครื่องหมาย → L2 C = 0.1 (validation log loss 0.38033; C 0.1–10 แทบเท่ากัน)
- Characteristics (IV train): fico 0.120, annual_inc 0.102, tot_hi_cred_lim 0.078, bc_open_to_buy 0.077, dti 0.047, loan_to_income 0.046,
  acc_open_past_24mths 0.045, mo_sin_rcnt_rev_tl_op 0.039, percent_bc_gt_75 0.038, mths_since_recent_inq 0.032, mo_sin_old_rev_tl_op 0.032,
  mo_sin_old_il_acct 0.024, purpose 0.023, num_rev_tl_bal_gt_0 0.022
- IV โดยรวมต่ำ (สูงสุด 0.12) — คาดได้ เพราะ population ถูก LC คัดมาแล้ว
- Points: PDO 20, 600 ที่ odds 50:1 → score range จริง 473–620 (แคบ เพราะ IV ต่ำ). ตาราง: `reports/phase1/scorecard_points.md`

## 3. M2 — LightGBM monotone (prereg §4)

- 12 configs; เลือก num_leaves 63, min_child_samples 1000, lambda_l2 10, 184 rounds (validation log loss 0.37557).
  ทุก config ห่างกันแค่ ≤ 0.0006 log loss → ไม่ sensitive ต่อ hyper-parameters. `reports/phase1/lgbm_grid.md`, `lgbm_importance.md`
- Monotone constraints ตามรายการที่ pre-register (17 ลด risk, 17 เพิ่ม risk)

## 4. Headline comparison — OOT 2015 (n = 282,787) — `reports/phase1/evaluation.md`

| model | Gini ×100 | KS ×100 | mean PD | CITL (pp) | calib slope | Brier | log loss |
|---|---|---|---:|---|---|---|---|
| M1 scorecard | 33.7 [33.1, 34.2] | 24.3 [23.8, 24.8] | 12.89% | −2.00 [−2.12, −1.88] | 1.001 [0.984, 1.019] | 0.1215 | 0.3996 |
| **M2 LightGBM** | **36.8 [36.3, 37.3]** | **26.6 [26.2, 27.1]** | 13.13% | −1.75 [−1.87, −1.63] | 0.928 [0.914, 0.943] | 0.1202 | 0.3946 |
| LC sub_grade (benchmark) | 35.7 [35.2, 36.3] | 26.2 [25.8, 26.7] | – | – | – | – | – |

Observed bad rate 14.88%. 95% bootstrap CI (B = 500). Validation 2014: M1 Gini 32.4, M2 36.2, LC 31.9
- **ΔGini M2 − M1 = 3.10 [2.81, 3.38]** → M2 champion. (validation: 3.74 [3.37, 4.09])
- M2 − LC sub_grade บน OOT = +1.05 [0.56, 1.48] (paired bootstrap, descriptive)
- LC sub_grade ดีกว่า M1 บน OOT 2.0 [1.6, 2.5] points แต่ไม่ดีกว่าบน validation (31.9 vs 32.4) — LC มีข้อมูลมากกว่าเรา
  (full bureau report, model ที่ update ทุกปี) และ M2 ชนะ LC ได้ ~1.05 points
- Calibration: M2 slope 0.93 = PD กระจายเกินไปเล็กน้อย (overconfident ที่ปลาย); ทั้งคู่ under-predict ทั้งระดับ → `p1_calibration_oot.png`

## 5. Cutoff rule (prereg §6) — `p1_strategy_curve.png`

Cutoff ตั้งบน validation 2014 ให้ approved bad rate ≤ 11.0%, แล้วใช้กับ OOT 2015 แบบไม่ปรับ:
| model | cutoff | 2014 approval / approved bad | **2015 approval / approved bad** | 2015 declined bad |
|---|---|---|---|---:|
| M1 | score ≥ 532 | 77.4% / 10.88% | 77.9% [77.7, 78.0] / **11.73% [11.60, 11.87]** | 25.97% |
| M2 | PD ≤ 0.2008 | 82.1% / 11.00% | 81.7% [81.5, 81.8] / **11.91% [11.78, 12.04]** | 28.13% |

- Policy ที่ตั้งปี 2014 **เกิน risk appetite** ในปี 2015 (0.7–0.9 pp เหนือ 11%) — ทั้งที่ approval rate แทบไม่เปลี่ยน
- ที่ bad-rate target เดียวกัน M2 อนุมัติได้มากกว่า M1 ~4.7 pp (82.1% vs 77.4% บน 2014) = มูลค่าทางธุรกิจของ +3 Gini
- ที่ approval 80% บน OOT: approved bad rate M1 12.00%, M2 11.69%

## 6. Reason codes (D) — OOT 2015 declines

- M1 ("points below max"), 62,585 declines: top-4 มี fico 92%, tot_hi_cred_lim 82%, acc_open_past_24mths 66%, loan_to_income 45%;
  top-1 บ่อยสุด: acc_open_past_24mths 34%, fico 29%, loan_to_income 15%
- M2 (TreeSHAP), 51,788 declines: top-1 loan_to_income 18%, fico 15%, acc_open_past_24mths 15%, purpose 13%, annual_inc 10%
- ผู้ที่ถูก decline โดยทั้งสอง model (41,017): top-1 ตรงกัน **48.2%**, M1 top-1 อยู่ใน M2 top-4 **89.7%**
  → reason ของ M2 ใช้ได้แต่ไม่ "เสถียร" เท่า scorecard (M2 ใช้ correlated substitutes ได้ เช่น num_tl_op_past_12m แทน acc_open_past_24mths)

## 7. Monitoring backtest 2014Q1–2018Q4 (prereg §7) — `reports/phase1/monitoring.md`, `p1_psi.png`, `p1_ae_mob12.png`

**First flag per signal**
| signal | first issue quarter flagged | knowable at |
|---|---|---|
| Score PSI M1 (≥ 0.10) | 2018Q3 (amber; never red) | 2018-09 |
| Score PSI M2 | never | – |
| MOB-12 A/E M1 amber / red | 2015Q2 / 2015Q4 | 2016-12 / 2017-06 |
| MOB-12 A/E M2 amber / red | 2015Q2 / 2016Q1 | 2016-12 / 2017-09 |
| Final-outcome KS (< 0.9× validation) | never (2014Q1–2015Q4) | – |
| **Deterioration truth** (MOB-12 default ≥ 1.2× train 3.86%) | **2015Q2** (4.70% = 1.22×) | 2016-12 |

**"Would we notice in time?" — ตอบ:**
- **PSI: ไม่เลย.** Score PSI ≤ 0.03 ตลอด 2014Q1–2017Q3. การ amber ครั้งเดียวของ M1 (2018Q3–Q4, PSI 0.11–0.12) เกิดเพราะ
  score mix **ดีขึ้น** (% ต่ำกว่า cutoff ลดจาก ~21% เหลือ 10%) จาก LC tighten credit box — ไม่ใช่ warning ที่ถูกทิศ
- **CSI:** มี alerts แต่ชี้ไปทางที่ "ดูปลอดภัยขึ้น": verification_status red ตั้งแต่ 2015Q4 (Source Verified 16% ใน 2013 → 35–47% ในแต่ละ quarter หลัง 2014
  = LC เปลี่ยนกระบวนการ); revol_util / bc_util / percent_bc_gt_75 red ตั้งแต่ 2017Q4 (median revol_util 59% → 41%).
  ไม่มี characteristic ไหนบอกว่า risk แย่ลง
- **KS ไม่ลด** (M1 22.4–25.2, M2 25.9–27.1 ทุก quarter ที่ matured) → ranking ยังดี; ปัญหาคือ level
- **A/E MOB-12** คือ signal เดียวที่ใช้ได้: เริ่มไต่ตั้งแต่ 2014Q3 (1.05) → amber 2015Q2 (1.15) → red 2015Q4 (1.26) →
  peak 2016Q3 (1.52, M1). แต่ lag 18 เดือน: vintage แรกที่แย่ลง (เม.ย.–มิ.ย. 2015) จับได้ ธ.ค. 2016
- **Exploratory (ไม่ได้ pre-register):** A/E ที่ MOB 6 (เกณฑ์เดิม) จะ amber สำหรับ 2015Q2 ได้ตั้งแต่ **มิ.ย. 2016** — เร็วขึ้น 6 เดือน
  (`reports/phase1/exploratory_early_signal.md`); ถือเป็น hypothesis — ควร pre-register ใน monitoring framework รอบหน้า

## 8. Vintage analysis (prereg §8) — `reports/phase1/vintage.md`, `p1_vintage_curves.png`

Cumulative default (% ของ loans ตั้งต้น), risk bands = M1-score quintiles ใน train (B1 เสี่ยงสุด)
| issue q | all @12 | all @24 | all @36 | B1 @12 | B3 @12 | B5 @12 |
|---|---:|---:|---:|---:|---:|---:|
| 2013Q2 | 3.99 | 9.34 | 12.73 | 8.05 | 2.97 | 1.38 |
| 2014Q2 | 3.94 | 9.63 | 13.46 | 7.33 | 3.66 | 1.10 |
| 2015Q2 | 4.70 | 11.53 | 15.18 | 8.61 | 4.14 | 1.32 |
| 2016Q2 | 5.76 | 12.46 | – | 10.51 | 5.37 | 2.12 |
| 2016Q3 | 5.98 | 12.69 | – | 10.80 | 5.63 | 2.28 |
| 2017Q2 | 5.34 | – | – | 10.25 | 5.49 | 1.93 |

- Deterioration อยู่ในทุก band (ไม่ใช่ mix): B3@12 3.0% → 5.6%, B5@12 1.1–1.4% → 2.1–2.3% (≈ 1.6–2×)
- Mix กลับเอียงไปทาง "ดี": 2018Q3–Q4 มี B1 แค่ ~10–11% (train 20%) และ B5 ~29% → LC tighten; แต่ default ต่อ band ปี 2017 ยังสูงกว่า 2013–14
- 2012Q3 = ก.ย. 2012 เท่านั้น (base เริ่ม 2012-09)

## 9. What worked / what failed

**Worked**
- Pre-registered pipeline วิ่งจบไม่ต้องย้อนแก้ decision ใด ๆ; time-based split; OOT ไม่เคยใช้เลือก model/cutoff
- Monotone LightGBM ชนะ scorecard ชัด (+3.1 Gini, CI แคบ) และชนะ LC sub_grade
- Vintage + A/E เล่าเรื่อง "would you notice" ได้ชัด พร้อมวันที่ที่รู้ได้จริง

**Failed / ข้อจำกัด (รายงานตรง ๆ)**
- **Calibration ไม่รอด 2015:** under-predict ~1.75–2.0 pp; risk appetite (11%) ถูกละเมิดใน OOT
- **PSI/CSI ไร้ประโยชน์สำหรับ drift ชนิดนี้** — และ alert เดียวที่เกิดชี้ผิดทิศ
- **Scorecard แพ้ LC sub_grade บน OOT** (33.7 vs 35.7) — feature set แบบ APP-only + ไม่ใช้ geography ทำให้ทำได้แค่นี้
- Reason-code agreement ระหว่าง model แค่ 48% (top-1)
- Score range ของ scorecard แคบ (473–620) เพราะ IV ต่ำ
- Default timing เป็น approximation จาก last_pymnt_d; accepted-only population (ไม่มี reject inference)
- Outcome 36m ของ train vintage 2013 จริง ๆ lender ปี 2014 ยังไม่เห็นครบ (simplification มาตรฐาน — ดู prereg §1)

## 10. Deviations from pre-registration
1. **เพิ่ม exploratory analysis** (MOB-6/9 A/E) หลังเห็นผล MOB-12 — แยกไฟล์และติด label "not pre-registered"
2. Monitoring flags ใช้ "≥ threshold" (prereg เขียน ">" สำหรับ A/E) — ไม่มีค่าใดตกตรง threshold พอดี จึงไม่มีผล
3. Calibration slope CI ใช้ Newton 8 iterations ต่อ bootstrap replicate (point estimate ใช้ 25) — approximation เล็กน้อย
4. Vintage 2012Q3 มีเฉพาะ ก.ย. 2012 (ข้อมูลก่อนหน้าไม่มี bureau batch ให้ score)
5. **Deterministic re-run (quality step, 2026-11-19):** ผลเดิมมาจาก parquet ที่ row order ไม่ deterministic (`preserve_insertion_order=false`)
   ทำให้ bootstrap CIs และ LightGBM bagging ขึ้นกับ row order. แก้ให้ order = ลำดับใน CSV (`file_row_number`) แล้ว re-run ทั้ง pipeline
   (OOT ถูกประเมินอีกครั้ง — ไม่ได้ใช้เลือกอะไร). Config ที่เลือกเปลี่ยน (num_leaves 15 → 63, 318 → 184 rounds; validation log loss เท่ากันที่ 0.37557)
   | | ก่อน | หลัง |
   |---|---|---|
   | OOT Gini M2 | 36.85 [36.29, 37.39] | 36.78 [36.29, 37.31] |
   | ΔGini M2 − M1 | 3.17 [2.90, 3.46] | 3.10 [2.81, 3.38] |
   | CITL M2 (pp) | −1.59 | −1.75 |
   | cutoff M2 | PD ≤ 0.2039 | PD ≤ 0.2008 |
   ข้อสรุปและ decision rule ไม่เปลี่ยน; ทั้ง 12 configs ให้ OOT Gini 36.48–36.87 (≥ scorecard + 2.8) — reports/quality/grid_sensitivity.md.
   ตัวเลขทั้งหมดในเอกสารนี้เป็นของ run ใหม่ (reproducible byte-for-byte)
6. **Timeline caveat (independent review MA-1):** training labels (outcome เต็ม 36 เดือนของ vintage 2012–13) จะครบจริงราว 2017 →
   "knowable" dates ใน §7 เป็นของ counterfactual "model ใช้งานตั้งแต่ 2015" ไม่ใช่สิ่งที่ lender ปี 2014 ทำได้จริง
นอกนั้นเป็นไปตาม prereg ทุกข้อ (split, features, binning, selection, grid, decision rule, cutoff rule, thresholds)

## 11. Implications for Phase 2 (A + B)
- Concept drift ที่เห็นคือสิ่งที่ forward-looking PD (B) ต้องอธิบาย: ถ้า state unemployment อธิบาย A/E ↑ ปี 2015–16 ไม่ได้
  (US unemployment **ลดลง** ช่วงนั้น — general knowledge, ยังไม่ได้ดึงข้อมูล BLS) → macro signal น่าจะอ่อน → Plan B rule มีโอกาสถูก trigger — ต้องทดสอบตามกฎที่เขียนไว้
- Survival (A): vintage curves ยืนยันว่า default timing จาก last_pymnt_d ให้ S-curve ที่สมเหตุสมผลทุก band → ใช้เป็น event time ได้
