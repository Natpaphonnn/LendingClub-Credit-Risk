# 02 — Pre-registration: Phase 1 (scorecard, LightGBM, monitoring, vintage) — 2026-11-19

เขียนและ commit **ก่อน** fit model ใด ๆ. ห้ามแก้ไฟล์นี้หลังเห็นผล validation/OOT — ถ้าต้องเบี่ยงจากแผน ให้บันทึกใน
02_phase1_results.md หัวข้อ "Deviations" พร้อมเหตุผล

ข้อมูลที่ใช้ตัดสินใจในเอกสารนี้มาจาก Phase 0 audit (feature availability, maturity, bad rate ระดับ vintage) เท่านั้น
ยังไม่มีการดูผล model ใด ๆ

## 1. Population & label
- 36-month loans, `application_type = Individual`, ไม่รวม "Does not meet the credit policy" (decision 3)
- **Bad** = loan_status ∈ {Charged Off, Default}; **Good** = Fully Paid. สถานะไม่ final (Current, Late, In Grace) → ไม่อยู่ใน labelled sets
  (ใน 2014–2015 36m มี < 0.2%)
- ข้อจำกัดที่ยอมรับ: population เป็น accepted-only (ไม่ทำ reject inference — decision 4); outcome เป็น full-term 36m ซึ่ง
  lender ปี 2014 ยังไม่เห็นครบสำหรับ vintage 2013 — นี่คือ simplification มาตรฐานของ development sample และจะเขียนไว้ใน write-up

## 2. Time-based split (by issue_d)
| set | issue window | ใช้ทำอะไร |
|---|---|---|
| **Train** | 2012-09 → 2013-12 | fit binning, WoE, coefficients, LightGBM trees. เริ่ม 2012-09 เพราะ bureau batch (tot_cur_bal ฯลฯ) ครบตั้งแต่เดือนนั้น (missing 83% ใน 2012-08, 1.3% ใน 2012-09) |
| **Validation** | 2014-01 → 2014-12 | เลือก hyper-parameters, เลือก cutoff, early stopping, reference KS |
| **OOT test** | 2015-01 → 2015-12 | ประเมินครั้งเดียวตอนจบ → headline numbers |
| **Monitoring** | 2016-01 → 2018-12 (+ แสดง 2014–2015 เป็น reference) | PSI/CSI (no labels), early-MOB performance, vintage curves |

ไม่มี random split ใน headline. ห้ามใช้ OOT ในการเลือกอะไรทั้งสิ้น

## 3. Features (APP only)
**Candidate set** = APP columns (src/audit/leakage_map.py) ที่มีครบใน train window, ยกเว้น:
- free text: desc, emp_title, title (item 6 parked) — `purpose` ใช้แทน title
- geography: zip_code, addr_state (fair-lending / redlining risk; state เก็บไว้ใช้กับ macro ใน Phase 2)
- joint / sec_app_* และ application_type (train ไม่มี joint apps)
- batch ที่เริ่ม 2015-12 (open_acc_6m, open_act_il, open_il_12m/24m, mths_since_rcnt_il, total_bal_il, il_util, open_rv_12m/24m,
  max_bal_bc, all_util, inq_fi, total_cu_tl, inq_last_12m) — ไม่มีใน train
- fico_range_high (= low + 4), term (คงที่ = 36)
- ทุก LC / POST / ID / TIME column (int_rate, grade, sub_grade, installment, funded_amnt*, … ห้ามเด็ดขาด)

**Derived (pre-specified):** `fico` = fico_range_low + 2; `credit_hist_months` = issue_d − earliest_cr_line;
`loan_to_income` = loan_amnt / annual_inc; `emp_length_yrs` (0–10 ordinal, "< 1 year" = 0, missing = NaN)
"mths_since_*" ที่ missing = "ไม่เคยมีเหตุการณ์" → เป็น bin แยก (scorecard) / NaN (LightGBM)

## 4. Candidate models
### M1 — WoE/IV logistic scorecard (champion candidate)
- WoE = ln(%good / %bad) ต่อ bin. Numeric: fine classing 20 quantile bins → merge adjacent bins (pool-adjacent-violators)
  จน WoE monotone ตาม Spearman direction ของ feature, จากนั้น merge bins < 5% ของ train; missing = bin แยก (ถ้า ≥ 0.5%,
  มิฉะนั้นรวมกับ bin ที่ bad rate ใกล้สุด). Categorical: categories < 1% รวมเป็น "OTHER"
- Selection: IV ≥ 0.02 → ถ้า |Pearson corr ของ WoE| > 0.6 ทิ้งตัวที่ IV ต่ำกว่า → เก็บ top 20 by IV →
  fit L2 logistic (C ∈ {0.01, 0.1, 1, 10} เลือกด้วย validation log loss) → ถ้ามี coefficient ผิดเครื่องหมาย (β ≥ 0 เมื่อ WoE = ln(g/b))
  ทิ้ง feature ที่ IV ต่ำสุดในกลุ่มผิดเครื่องหมาย แล้ว refit จนทุกตัวถูกเครื่องหมาย
- **Points scaling:** PDO = 20, score 600 ที่ odds good:bad = 50:1 → factor = 20/ln2, offset = 600 − factor·ln 50.
  points ต่อ attribute = −(β_j·WoE_ij + α/n)·factor + offset/n (ปัดเป็นจำนวนเต็ม; score สูง = ดี)

### M2 — LightGBM with monotonic constraints (challenger) — รวม item D
- ใช้ candidate features เดียวกับ M1 (ก่อน IV filter) แบบ raw values; categorical (home_ownership, verification_status, purpose)
  เป็น category dtype
- **Monotone constraints (กำหนดล่วงหน้า):**
  - ลด risk (−1): fico, annual_inc, credit_hist_months, mths_since_recent_inq, mths_since_last_delinq, mths_since_last_record,
    mths_since_recent_bc, mort_acc, pct_tl_nvr_dlq, bc_open_to_buy, tot_hi_cred_lim, total_rev_hi_lim, mo_sin_old_rev_tl_op,
    mo_sin_old_il_acct, mo_sin_rcnt_rev_tl_op, mo_sin_rcnt_tl, emp_length_yrs
  - เพิ่ม risk (+1): dti, loan_to_income, inq_last_6mths, revol_util, bc_util, percent_bc_gt_75, delinq_2yrs, pub_rec,
    pub_rec_bankruptcies, acc_open_past_24mths, num_tl_op_past_12m, num_tl_90g_dpd_24m, num_accts_ever_120_pd, tax_liens,
    collections_12_mths_ex_med, acc_now_delinq, chargeoff_within_12_mths
  - อื่น ๆ: unconstrained (0)
- Grid (12 configs): num_leaves ∈ {15, 31, 63} × min_child_samples ∈ {200, 1000} × lambda_l2 ∈ {0, 10};
  learning_rate 0.05, feature_fraction 0.8, bagging_fraction 0.8 (freq 1), max 3000 rounds, early stopping 100 rounds
  บน validation log loss. เลือก config ด้วย validation log loss
- **Benchmark (ไม่ใช่ candidate):** LC sub_grade เป็น ranking (A1 ดีสุด) — รายงาน Gini/KS บน OOT เพื่อ context

## 5. Metrics & intervals (OOT 2015 = headline; validation รายงานด้วย)
- Discrimination: Gini (= 2·AUC − 1), KS
- Calibration: calibration-in-the-large (mean PD − observed bad rate), calibration slope (logit(y) ~ logit(p)),
  decile table (predicted vs observed), Brier, log loss
- **Intervals:** bootstrap 95% percentile CI, B = 500 resamples ของ OOT (seed 20261119). Model comparison = paired bootstrap ของ ΔGini
- **Decision rule:** LightGBM เป็น champion ก็ต่อเมื่อ ΔGini (M2 − M1) ≥ 2.0 Gini points **และ** paired 95% CI lower bound > 0.
  มิฉะนั้น scorecard (M1) เป็น champion (interpretability + reason codes ตรงตัว). ไม่ว่าผลจะออกมาอย่างไร รายงานทั้งสองตัว
- ไม่ recalibrate ก่อนรายงาน OOT (miscalibration จาก drift เป็นส่วนหนึ่งของผลที่ต้องรายงาน)

## 6. Cutoff rule (approval vs bad rate)
- **Primary:** cutoff score = ค่าต่ำสุดที่ทำให้ bad rate ของกลุ่มที่อนุมัติบน **validation 2014 ≤ 11.0%**
  (2014 36m bad rate ทั้งหมด 13.7% จาก audit → ลด ~20% relative). รายงาน approval rate ที่เกิดขึ้น
- จากนั้นใช้ cutoff (score เดิม) กับ OOT 2015 → รายงาน approval rate + approved bad rate (พร้อม CI) — "policy ที่ตั้งปี 2014 ยังได้ผลไหม"
- Secondary: strategy curve (approval rate vs approved bad rate) ทั้ง M1, M2 บน validation และ OOT; จุด approval 80%
- **Reason codes (D):** สำหรับผู้ถูก decline (score < cutoff) บน OOT: top-4 characteristics ที่ points ห่างจาก max points ของ characteristic นั้นมากที่สุด
  (method "points below max"). LightGBM: top-4 positive TreeSHAP contributions (pred_contrib). รายงานความถี่ของ reason
  และ % ที่ top-1 reason ตรงกันระหว่าง M1 กับ M2 (ในกลุ่มที่ทั้งคู่ decline)

## 7. Monitoring (champion model; ถ้า M2 ชนะ ทำทั้งคู่)
Reference distribution = **train** (2012-09 → 2013-12). หน่วยเวลา = issue quarter, 2014Q1 → 2018Q4
- **PSI (score):** 10 bands = train score deciles. **< 0.10 green, 0.10–0.25 amber, ≥ 0.25 red.** สัญญาณพร้อมใช้ทันทีที่ quarter ปิด
- **CSI** ต่อ scorecard characteristic (บน WoE bins ของมัน) — thresholds เดียวกัน
- **Score distribution** ต่อ quarter (mean, p10/p50/p90, % ต่ำกว่า cutoff)
- **Performance (labels):**
  - Matured (36m final; quarters ที่ resolved ≥ 99%): KS & bad rate ต่อ quarter. **Amber ถ้า KS < 0.90 × validation KS, red ถ้า < 0.80 ×**
  - Early indicator = **default by MOB 12** (default month = months(issue → last_pymnt_d) + 1; ไม่มี last_pymnt_d = MOB 1),
    observable เมื่อ issue quarter end + 12 + 6 เดือน (เผื่อ charge-off lag) ≤ as-of 2019-03.
    Expected = Σ PD_model × r, โดย r = (MOB12 default rate / final bad rate) ใน train.
    **A/E > 1.10 amber, > 1.25 red**
- **"Deterioration" (ground truth for "would we notice"):** issue quarter ที่ cumulative default ที่ MOB 12 สูงกว่า
  ค่าเฉลี่ยของ train window ≥ 20% relative (ใช้ MOB 12 เพื่อเทียบ vintage ใหม่ที่ยังไม่ครบเทอมได้); ถ้า quarter ไหน matured
  ก็รายงาน final bad rate ด้วย
- **Detection timing:** ต่อ signal ต่อ issue quarter → วันที่ signal นั้น "รู้ได้" (calendar date) และ flag สีอะไร;
  เทียบกับวันที่รู้ final bad rate (issue + 36 + 6 เดือน)

## 8. Vintage analysis
- Cumulative default rate (unconditional, ÷ จำนวน loans ตั้งต้น) by MOB 1–36, ต่อ issue quarter (2012Q3 → 2018Q4), 36m เท่านั้น
- **Risk bands (grade-free):** 5 bands = quintiles ของ M1 score ใน train (cut points fixed จาก train)
- แสดง MOB m เฉพาะเมื่อ issue month + m ≤ 2018-09 (as-of 2019-03 − 6 เดือน charge-off lag)
- ผลลัพธ์: curves (small multiples ต่อ band), ตาราง cumulative default ที่ MOB 12 / 24 / 36

## 9. ข้อจำกัดที่รู้ล่วงหน้า
- Default timing เป็น approximation จาก last_pymnt_d (ไม่มี monthly payment panel)
- Accepted-only population; LC เองก็ใช้ model ที่คัดคนอยู่แล้ว (selection on observables ของ LC)
- Calibration จะเพี้ยนบน OOT ถ้า bad rate เปลี่ยน (คาดไว้ เพราะ 2015 bad rate สูงกว่า train)
