# 03 — Pre-registration: Phase 2 (A survival/lifetime PD, B macro + Plan B rule, ECL, C fallback, MOB-6 test) — 2026-11-19

เขียนและ commit **ก่อน** ดาวน์โหลดหรือดูข้อมูล macro และก่อน fit model ใด ๆ ของ Phase 2
ข้อมูลที่ใช้ตัดสินใจในเอกสารนี้มีแค่ Phase 0–1 results (ที่ commit แล้ว) และโครงสร้างข้อมูล (เช่น total_pymnt รวม recoveries แล้ว,
addr_state มี 51 ค่ารวม DC). ถ้าต้องเบี่ยงจากแผน → บันทึกใน 03_phase2_results.md หัวข้อ "Deviations"

Population ทุกส่วน (ยกเว้นระบุ): 36m, Individual, ไม่รวม "does not meet credit policy" — เหมือน Phase 1
Frozen score = **Phase 1 champion M2 (LightGBM) PD** → ใช้ในรูป `lp = logit(PD_M2)` (ไม่ re-fit M2)

---

## A — Survival / lifetime PD (discrete-time competing risks)

**Event definitions (ต่อ loan, หน่วย = month on book, MOB):**
- Observation window ของ loan i สิ้นสุดที่ `W_i = min(36, months(issue → 2018-09))` (as-of 2019-03 − 6 เดือน charge-off lag เหมือน Phase 1)
- **Default** ที่ MOB d = months(issue → last_pymnt_d) + 1 (ไม่มี last_pymnt_d → 1) สำหรับ Charged Off / Default, ถ้า d ≤ W_i
- **Prepayment** ที่ MOB p = months(issue → last_pymnt_d) สำหรับ Fully Paid ที่ p ≤ min(33, W_i) (จ่ายหมดก่อนครบกำหนด ≥ 3 เดือน)
- Fully Paid ที่ p ∈ 34–36 (≤ W_i) = ครบกำหนดตามปกติ → censored ที่ p (ไม่ใช่ event)
- อื่น ๆ (Current, Late, In Grace, หรือ event หลัง W_i) → **censored ที่ W_i**
- Loan-month panel: loan อยู่ใน risk set ที่ MOB t = 1 … T_i (T_i = event หรือ censoring MOB), outcome ∈ {0 none, 1 default, 2 prepay}

**Model:** multinomial logit hazard (weighted Newton–Raphson, เขียนเอง):
`log(h_k(t)/h_0(t)) = α_k + f_k(t) + β_k1·lp + β_k2·lp·(t/36) + β_k3·int_rate + β_k4·log(loan_amnt)`, k ∈ {default, prepay}
- f_k(t) = cubic B-spline ของ MOB, 6 df (knots ที่ quantiles เท่ากันบน 1–36)
- int_rate / loan_amnt: เป็นเงื่อนไขสัญญา ณ วันปล่อยกู้ ใช้ได้ใน lifetime/ECL model (ไม่ได้ใช้ตัดสินอนุมัติ) — int_rate สำคัญต่อ prepayment
- ไม่มี hyper-parameter tuning

**Time split:** fit บน loans issued **2012-09 → 2013-12** (= Phase 1 train); validation 2014; OOT 2015; censored-era test 2016-01 → 2018-12

**Predictions:** ต่อ loan, h_d(t), h_p(t), t = 1..36 → S(t) = Π(1 − h_d − h_p), **CIF_d(m) = Σ_{t≤m} S(t−1)·h_d(t)**
- Lifetime PD = CIF_d(36); 12-month PD = CIF_d(12)
- เปรียบเทียบ (pre-registered demo): "naive lifetime PD" ที่ไม่สน prepayment = 1 − Π(1 − h_d(t)) → แสดงว่า over-state เท่าไร

**Evaluation:** ต่อ issue quarter 2012Q4 → 2018Q4: predicted vs actual cumulative default ที่ MOB 12 / 24 / 36
- actual = unconditional cumulative default (÷ loans ตั้งต้น) เหมือน vintage.py; แสดงเฉพาะ MOB ที่ observable ทั้ง quarter
  (last issue month + m ≤ 2018-09) → censoring จัดการด้วยการเทียบที่ MOB เดียวกันเท่านั้น
- predicted = ค่าเฉลี่ย CIF_d(m) ของ loans ใน quarter
- รายงาน A/E ต่อ quarter และต่อ period (validation 2014, OOT 2015, 2016, 2017, 2018) + loan-level: Gini ของ lifetime PD
  vs final bad บน OOT 2015 (ที่ matured)
- ไม่มีเกณฑ์ pass/fail สำหรับ A (เป็น descriptive); คาดว่าจะ under-predict 2015–16 (concept drift จาก Phase 1)

## B — Macro (Plan B rule จาก notes/STATUS.md, เขียนก่อน Phase 1) — operationalisation

**Data (ดาวน์โหลดหลัง commit ไฟล์นี้):** state unemployment rate รายเดือน, seasonally adjusted, BLS LAUS ผ่าน FRED series
`{ST}UR` (51 series รวม DCUR), 2007-01 → 2018-12. บันทึก source/license ใน data_sources.md.
ถ้าดาวน์โหลดไม่ได้ → ลอง BLS โดยตรง; ถ้าไม่ได้ทั้งคู่ → บันทึกว่า B ทำไม่ได้ (นับเป็น fail → Plan B)

**Macro covariates (time-varying, ต่อ loan-month):** u = unemployment ของ addr_state ใน calendar month (issue month + t − 1) — contemporaneous;
Δ12u = u(month) − u(month − 12)

**Model สำหรับ rule:** A-specification + `γ_k1·u + γ_k2·Δ12u` ในทั้งสอง cause (default & prepay), fit บน loans issued
**2009-01 → 2014-12** (ตาม rule: matured 36m vintages 2009–2014). Score-only counterpart = model เดียวกันไม่มี macro terms.
- Loans ก่อน 2012-09 ไม่มี bureau batch → M2 score ใช้ NaN path ของ LightGBM (score คุณภาพต่ำกว่า) — ยอมรับตาม rule;
  **sensitivity (ไม่นับใน rule):** fit ซ้ำบน 2012-09 → 2014-12
- Fit ด้วย non-event loan-months สุ่ม 25% (weight 4, seed 20261119), events ทุกตัว — ทั้ง macro และ score-only

**Rule (a) — sign + significance:** สถิติหลัก **θ = γ_default,1 + γ_default,2** (ผลของ unemployment ที่เพิ่ม 1 pp ต่อ log-odds ของ
default hazard: ทั้ง level และ 12m change เพิ่ม 1 pp). ผ่านถ้า **θ > 0 และ 95% CI ไม่คร่อม 0**.
CI = **block bootstrap by issue quarter** (resample 24 issue quarters with replacement), B = 200, percentile CI.
รายงาน γ แต่ละตัวด้วย

**Rule (b) — OOT value:** บน 2015 vintages (OOT), ใช้ realised unemployment path จริง (2015–2018):
- cells = 4 issue quarters × 4 Census regions (Northeast / Midwest / South / West; DC อยู่ South) = 16 cells
- predicted cell bad rate = mean lifetime PD (CIF_d(36)); observed = final bad rate (bad = Charged Off/Default; ตัด non-final)
- error = mean |pred − obs| (unweighted ข้าม 16 cells)
- ผ่านถ้า **error_macro ≤ 0.90 × error_score-only และ loan-level log loss (CIF_d(36) vs bad) ของ macro ≤ score-only**

**Rule (c) — plausible stress:** 2015 OOT portfolio, ต่อ loan:
- baseline: u คงที่ที่ระดับ ณ issue month ตลอดอายุ, Δ12u = 0
- adverse: u(t) = u_state(issue) + [U_state(2008-01 + t − 1) − U_state(2008-01)], Δ12u(t) = U_state(2008-01 + t − 1) − U_state(2008-01 + t − 13)
  (path จริงของ state นั้นช่วง 2008-01 → 2010-12)
- multiplier = Σ lifetime PD_adverse / Σ lifetime PD_baseline. **ผ่านถ้า 1.1 ≤ multiplier ≤ 3.0**

**ตัดสิน:** ผ่านครบ a, b, c → B ต่อ (scenario ECL). ไม่ผ่านข้อใด → **A + C**, macro เหลือเป็น sensitivity overlay ติด label "weak".
รายงานผลทุกข้อไม่ว่ากรณีใด

## ECL (TFRS 9-style) — OOT portfolio = 36m loans issued 2015

**Components (ต่อ loan, monthly):**
- **EAD(t)** = scheduled annuity balance ที่ต้น month t (funded_amnt, int_rate, 36 งวด); prepayment จัดการผ่าน competing risk (survival)
- **LGD** = pooled EAD-weighted mean ของ loans ที่ default ใน train window (2012-09 → 2013-12):
  LGD_i = 1 − (recoveries − collection_recovery_fee) / (funded_amnt − total_rec_prncp), clip [0, 1]. รายงาน CI (bootstrap) และ LGD by risk band เป็น sensitivity
- **PD**: marginal default probability S(t−1)·h_d(t) จาก A (หรือ B-macro ถ้า B ผ่าน)
- **ECL_12m** = Σ_{t=1..12} S(t−1)·h_d(t)·LGD·EAD(t)·DF(t); **ECL_lifetime** = Σ_{t=1..36} …; DF = discount ด้วย EIR = int_rate/12 ต่อเดือน
**Stage logic (พูดตรง ๆ):**
- ณ วันปล่อยกู้ ทุก loan = **Stage 1** → allowance = 12-month ECL
- **Stage 2** (significant increase in credit risk) ต้องใช้ข้อมูล behavioural (DPD, refreshed PD) ซึ่ง LC data **ไม่มีรายเดือน** →
  ไม่สามารถ allocate stage 2 จริงได้; รายงาน lifetime ECL ของทั้ง portfolio เป็น "ถ้าทุก loan ย้ายเป็น stage 2" (upper bound) และ
  ระบุ backstop ตามมาตรฐาน (30 DPD) ว่าใช้ไม่ได้กับข้อมูลนี้
- **Stage 3** = defaulted (credit-impaired) → lifetime loss = LGD × EAD at default
**Backtest (pre-registered):** undiscounted lifetime expected loss ที่ predict ณ origination vs realised net principal loss ของ 2015 vintage
(realised = Σ_defaulted [funded_amnt − total_rec_prncp − recoveries + collection_recovery_fee]); รายงานต่อ quarter และ risk band
**Scenarios (ถ้า B ผ่าน):** baseline / adverse ตามนิยามใน B, probability-weighted 70% baseline / 30% adverse

## C — Profit-optimal policy (ทำเฉพาะเมื่อ B ไม่ผ่าน)

- **Expected NPV per loan** ณ origination จาก A hazards (score-only), discount rate **5% p.a.** (cost of funds + opex รวม; sensitivity 3% และ 8%):
  NPV_i = Σ_t DF(t)·S(t−1)·[(1 − h_d − h_p)·installment + h_p·(EAD(t)) + h_d·(1 − LGD)·EAD(t)] − funded_amnt
  (prepay = จ่ายคืนยอดคงเหลือ; default = recover (1 − LGD) ของ EAD, ณ เดือนนั้น — simplification)
- **Decision cells:** 10 deciles ของ M2 PD (cut points จาก validation 2014) × 3 loan-amount bands (≤ 10k, 10k–20k, > 20k) = 30 cells
- **LP (scipy linprog / milp):** เลือก x_c ∈ {0, 1} (approve cell หรือไม่; MILP) เพื่อ max Σ x_c·E[NPV]_c บน **validation 2014**
  subject to: approval rate ≥ **75%** และ expected portfolio bad rate (Σ x_c·n_c·PD_c / Σ x_c·n_c) ≤ **11.0%**
  (ค่า constraint เดียวกับ Phase 1 risk appetite; approval floor 75% ≈ ระดับของ Phase 1 M1 cutoff)
- **Evaluate บน OOT 2015 ด้วย realised outcomes:** realised profit = Σ (total_pymnt − collection_recovery_fee − funded_amnt)
  (undiscounted; total_pymnt รวม recoveries แล้ว) ของ loans ที่ approve; เทียบกับ (i) approve ทั้งหมด, (ii) Phase 1 M2 cutoff (PD ≤ 0.2039),
  (iii) Phase 1 M1 cutoff (score ≥ 532). รายงาน approval rate, approved bad rate, realised profit total และต่อ loan

## MOB-6 A/E monitoring test (decision 3)

- **Discovered on 2015 vintages** (Phase 1 exploratory) → evaluation set = **issue quarters 2016Q1 → 2017Q4 เท่านั้น**
- Signal: A/E_6 = Σ 1[default_mob ≤ 6] / (Σ PD_model × r6), r6 = (MOB-6 default rate / final bad rate) ใน Phase 1 train;
  knowable ที่ quarter end + 6 + 6 เดือน. ทำทั้ง M1 และ M2
- **Thresholds (pre-registered now): A/E_6 > 1.10 amber, > 1.25 red** (เท่ากับที่ใช้ตอนค้นพบ — ไม่ได้ปรับ)
- Ground truth: MOB-12 deterioration (≥ 1.2× train MOB-12 default rate) — observable ถึง 2017Q3
- Metrics: (i) **sensitivity** = % ของ quarters 2016Q1–2017Q3 ที่ truth = YES และ A/E_6 ≥ amber (เกณฑ์ "useful": ≥ 80%);
  (ii) **lead time** = (knowable date ของ MOB-12) − (knowable date ของ MOB-6) ต่อ quarter ที่ทั้งคู่ flag;
  (iii) 2017Q4: รายงาน A/E_6 อย่างเดียว (MOB-12 truth ยังไม่ observable)
- ข้อจำกัดที่รู้ล่วงหน้า: ทุก quarter ใน 2016–2017 ที่มี truth น่าจะ deteriorated → **specificity ทดสอบไม่ได้** ในช่วงนี้ — จะรายงานตรง ๆ
