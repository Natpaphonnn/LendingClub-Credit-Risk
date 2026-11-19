# 03 — Phase 2 results (A survival/lifetime PD, B macro → failed → C, ECL, MOB-6) — 2026-11-19 (revised after independent validation)

Pre-registration: `notes/03_prereg_phase2.md` (commit 1203ada — commit **ก่อน** ดาวน์โหลด macro data และก่อน fit).
Code: `src/phase2/`; ตาราง: `reports/phase2/`; figures: `reports/figures/p2_*.png`.

Reproduce (~5 นาที, ส่วนใหญ่คือ bootstrap ของ B):
```
nice -n 19 .venv/bin/python -I src/phase2/fetch_bls.py
for s in build_loans fit_A rule_B ecl policy_C mob6_test; do nice -n 19 .venv/bin/python -I src/phase2/$s.py; done
```

---

## TL;DR

1. **A ใช้ได้:** competing-risks hazard (default vs prepayment, Current = censored) fit บน 2012-09–2013-12 ให้ A/E ≈ 1.00 ใน train
   และ 0.98–1.02 บน validation 2014 แต่ under-predict ตาม drift ที่เห็นใน Phase 1: OOT 2015 A/E 1.07–1.11, 2016 1.26–1.39, 2017 1.44 (MOB 12).
   ถ้าไม่สน prepayment, lifetime PD จะ over-state จาก 13.6% → 18.2% (+34% relative)
2. **B ไม่ผ่าน Plan B rule → เปลี่ยนเป็น A + C** (ตามกฎที่เขียนไว้ก่อน Phase 1): (a) FAIL — θ ไม่เป็นบวก: −0.038 [−0.094, −0.004] (E3: subsample สุ่มใหม่ทุก replicate; ก่อน deterministic re-run: −0.019 [−0.063, 0.011] — ตำแหน่ง CI เปราะ);
   (b) PASS แบบ "ถูกด้วยเหตุผลผิด"; (c) FAIL — adverse/baseline = 0.91 (adverse ทำให้ PD **ลดลง**) → macro signal ถูก confound กับ drift ของ LC
3. **ECL (score-only, ไม่มี forward-looking overlay):** 2015 portfolio funded $3.62bn → day-1 12m ECL $101m (2.8%), lifetime ECL $203m (5.6%).
   Backtest (ไม่ใช่ provision ที่ book จริง): realised net loss **$274m vs predicted lifetime EL $235m (realised = 1.17× predicted; พลาด 14% ของ realised)**
   — ratio สูงสุดใน band ที่ปลอดภัยที่สุด (×1.52) แต่ dollar gap ใหญ่สุดอยู่ band กลาง; gap นี้ปน drift กับการไม่ refit ณ reporting date
4. **C:** MILP policy ไม่ชนะ "approve all" บน metric ที่ pre-register (realised profit แบบไม่ discount: $222m vs $230m). Exploratory
   realised NPV @5%: C $46m ≫ approve all $28m แต่ ≈ Phase 1 M2 cutoff ($47m) → optimizer สรุปได้แค่ "PD cutoff ที่ดีก็พอ"
5. **MOB-6 A/E — descriptive/exploratory เท่านั้น (relabel หลัง review CR-1):** 2016–17 red ทุก quarter แต่ค่าเหล่านี้ถูกคำนวณและ commit แล้ว
   ก่อน register thresholds, lead time 6 เดือนเป็นจริงโดยนิยาม, และทุก quarter deteriorated → ไม่ใช่ test; discovery period: M2 จับได้ 1/2 (พลาด 2015Q4), ไม่มี false alarm 6/6
   (ทุก quarter ที่มี truth deteriorated หมด) — ใช้ได้ในฐานะ early warning แต่ยังไม่รู้ false-alarm rate

---

## A — Survival / lifetime PD (prereg §A) — `reports/phase2/survival_A.md`, `p2_A_vintage_ae.png`

- Data: 1,433,835 loans (36m, Individual, meets policy, 2009–2018) → `data/interim/p2_loans.parquet`. Events coded ตาม prereg
  (default = last payment + 1; prepay = Fully Paid ≥ 3 เดือนก่อนครบกำหนด; อื่น ๆ censored ที่ min(36, 2018-09))
- Train: 120,683 loans, 3,030,762 loan-months, 14,902 defaults, 61,594 prepayments; Newton converged ใน 10 iterations
- Coefficients ที่น่าสนใจ: default — lp (logit M2 PD) 1.36 (SE 0.03), lp × t/36 = −0.45 → อำนาจของ application score ลดลงตาม MOB
  (เหมาะกับ behavioural score ในอนาคต); prepay — lp −0.17 (คนเสี่ยงสูง prepay น้อยกว่า), int_rate +0.079/SD (ดอกแพง prepay มากกว่า)

**A/E ของ cumulative default (n-weighted ข้าม quarters ที่ observable)**
| period | n | A/E @12 | A/E @24 | A/E @36 | pred lifetime PD | naive (no prepay) |
|---|---:|---:|---:|---:|---:|---:|
| train 2012Q4–13 | 115,603 | 1.005 | 1.011 | 1.008 | 12.2% | 16.7% |
| valid 2014 | 162,570 | 0.978 | 1.010 | 1.019 | 13.3% | 18.0% |
| OOT 2015 | 282,934 | 1.090 | 1.112 | 1.075 | 13.6% | 18.2% |
| 2016 (censored) | 318,277 | 1.387 | 1.258 | – | 13.0% | 17.6% |
| 2017 (censored) | 296,484 | 1.435 | – | – | 11.6% | 15.9% |
| 2018 (censored) | 202,395 | – | – | – | 11.0% | 14.9% |
- Censoring: เทียบเฉพาะ MOB ที่ observable ทั้ง quarter (issue + MOB ≤ 2018-09); 2018 ยังไม่ถึง MOB 12 จึงมีแต่ prediction
- OOT 2015 loan-level: Gini ของ lifetime PD 36.1 (M2 PD เดี่ยว 36.8); mean lifetime PD 13.6% vs final bad 14.9%

## B — Macro, Plan B rule (prereg §B) — `reports/phase2/macro_B.md`, `macro_B.json`

Data: BLS LAUS state unemployment (SA), 51 series, 2007–2018, ผ่าน BLS API (FRED timed out) — public domain, บันทึกใน data_sources.md §4

| rule | statistic | threshold | result |
|---|---|---|---|
| (a) sign + significance | θ = γ_u + γ_Δ12u (default) = **−0.0379**, 95% block-bootstrap CI (24 issue quarters, B=200, subsample redrawn per replicate — E3) [−0.0935, −0.0045] | θ > 0, CI > 0 | **FAIL** |
| (b) OOT value | cell error 2.12 pp (macro) vs 2.91 pp (score-only) = −27.1%; log loss 0.39246 vs 0.39415 | ≤ −10%, log loss ไม่แย่ลง | PASS |
| (c) stress size | adverse/baseline lifetime PD = **0.911** (12.55% → 11.43%) | 1.1–3.0 | **FAIL** |

**→ Decision: B FAILS → Plan B = A + C** (macro เหลือเป็น "weak" sensitivity เท่านั้น — ไม่ใช้ใน ECL)

ทำไมถึงล้มเหลว (การตีความ, ไม่ใช่ส่วนของ rule):
- γ_u (level) = −0.062 **ติดลบ**: ใน 2009–2014 unemployment ลดลงต่อเนื่อง (median state 8.6% ปลายปี 2009 → 5.5% ต้นปี 2015)
  ขณะที่ default rate ของ LC ไต่ขึ้น (credit box ขยาย) → model เรียนว่า "unemployment ต่ำ = default สูง" = time-trend confounding
- γ_Δ12u = +0.024 มีทิศถูก (unemployment ที่ **เพิ่มขึ้น** ทำให้ default สูงขึ้น) แต่ไม่พอชดเชย level
- (b) ผ่านเพราะ level coefficient ติดลบทำให้ predict PD สูงขึ้นในปี 2015 (unemployment ต่ำลง) ซึ่งบังเอิญตรงกับ drift → **ถูกด้วยเหตุผลผิด**
  นี่คือเหตุผลที่ rule ต้องผ่านครบทั้ง 3 ข้อ
- Sensitivity (2012-09–2014, ไม่นับใน rule): θ = +0.029 [−0.014, +0.057] — ทิศถูกแต่ CI คร่อม 0 (มีแค่ 10 issue quarters)
- ข้อจำกัด: มี downturn เดียว และ LC แทบไม่ได้ปล่อยกู้ช่วงนั้น; LAUS เป็นข้อมูล revised ไม่ใช่ real-time vintage

## ECL — TFRS 9-style, OOT portfolio (2015) — `reports/phase2/ecl.md`, `ecl.json`, `p2_ecl_backtest.png`

- PD: A (score-only hazard) — **ไม่มี forward-looking macro overlay** เพราะ B fail → เป็นช่องว่างจาก TFRS 9 ที่ต้องบอกตรง ๆ
- **LGD = 88.8%** [88.6, 89.0] (EAD-weighted, 15,007 train defaults; recovery เฉลี่ยแค่ ~11% ของ EAD ณ default). แทบไม่ต่างตาม band (87.5–89.0%).
  หมายเหตุ: ตัวเลข ~0.58 ใน audit คือ loss ÷ funded (รวม principal ที่จ่ายมาแล้วก่อน default) ไม่ใช่ LGD ต่อ EAD
- EAD = scheduled annuity balance; prepayment ผ่าน competing risk; discount ด้วย EIR

| 2015 portfolio | value |
|---|---:|
| loans / funded | 282,934 / $3,622.8m |
| pred lifetime PD vs actual default | 13.56% vs 14.88% |
| day-1 12-month ECL (Stage 1 ทั้งหมด ณ origination) | $100.7m (2.8% of funded) |
| lifetime ECL (discounted) | $202.7m (5.6%) |
| **predicted lifetime EL (undiscounted) vs realised net principal loss** | **$234.9m vs $273.8m → ×1.17** |

Backtest by quarter: ×1.09 (2015Q1), ×1.18, ×1.15, ×1.22 (2015Q4). By risk band (M2-PD quintile, 1 = safest): ×1.52, ×1.44, ×1.36, ×1.23, ×1.00
→ ratio สูงสุดใน**กลุ่มที่ดูปลอดภัย** (สอดคล้องกับ vintage curves ใน Phase 1: B5 default ×2) แต่ dollar gap ใหญ่สุดอยู่ band 3–4
- Hessian SEs ถูกตัดออกจาก report: fit ใช้ weighted subsample + ไม่คิด clustering จึงใช้ทำ inference ไม่ได้ (review MA-3)

**Allowance ณ 2015-12-31 (stage logic):**
| stage | loans | gross EAD | allowance | coverage |
|---|---:|---:|---:|---:|
| Stage 1 (no missed instalment visible; 12m ECL) | 263,610 | $2,992.3m | $112.3m | 3.75% |
| Stage 2 (1–2 missed instalments ≈ ≥ 30 DPD, ex-post proxy; lifetime ECL) — E4 | 1,571 | $17.1m | $1.5m | 9.0% |
| Stage 3 (≥ 3 missed instalments ≈ 90 DPD; LGD × EAD at default) — E4 | 2,300 | $25.1m | $22.3m | 88.8% |
| derecognised (prepaid ≤ Dec-2015) | 15,453 | – | – | – |

**Ex-post illustration** (E4, notes/08_prereg_extensions.md): monthly DPD ไม่มีในข้อมูล; missed instalments เห็นได้เฉพาะ loans ที่สุดท้าย charge off
(delinquency ที่ cure ภายหลังมองไม่เห็น → stage 2 understated). Version ที่ refit ณ 2015-12-31 + discounted LGD: notes/10_extensions_results.md

## C — Profit-optimal policy (prereg §C; ทำเพราะ B fail) — `reports/phase2/policy_C.md`, `p2_C_policy.png`

MILP บน 30 cells (M2-PD decile × amount band), max expected NPV (A hazards, LGD 88.8%, discount 5%) บน validation 2014
ภายใต้ approval ≥ 75% และ expected bad (mean M2 PD) ≤ 11% → approve 26/30 cells (ตัด decile 9 ทั้งหมด + decile 8 band 10–20k)

| OOT 2015 | approval | realised bad | **realised profit (pre-reg, undiscounted)** | expected NPV @5% | realised NPV @5% (EXPLORATORY) |
|---|---:|---:|---:|---:|---:|
| C: MILP cells | 86.5% | 12.60% | $222.3m | $70.9m | $45.6m |
| approve all | 100% | 14.88% | **$230.3m** | $48.1m | $28.4m |
| Phase 1 M2 cutoff (PD ≤ 0.2008) | 81.7% | 11.91% | $217.0m | $71.2m | **$47.4m** |
| Phase 1 M1 cutoff (score ≥ 532) | 77.9% | 11.73% | $208.0m | $65.5m | $43.3m |

- **บน metric ที่ pre-register, C แพ้ approve-all** (−$8.0m): metric แบบไม่ discount ไม่คิด cost of funds → loan ที่คืนเงินรวมมากกว่ายืม
  ดู "กำไร" หมดแม้จะเสี่ยงสูง → metric นี้เลือกไม่ดี (บันทึกเป็นบทเรียน)
- Exploratory (ไม่ได้ pre-register): discount 5% พร้อม timing โดยประมาณ → C ดีกว่า approve-all +$17m (+61%) แต่ **≈ M2 cutoff** (−$1.8m)
- C อนุมัติมากกว่า M2 cutoff (86% vs 82%) เพราะ constraint ใช้ model PD ซึ่ง under-predict หลัง drift → realised bad 12.6% เกิน 11%
- Sensitivity: discount 3% → C ดีที่สุดเล็กน้อย ($113.5m vs M2 $112.6m, exploratory NPV); 8% → ทุก policy NPV ติดลบ (ดอกเบี้ย LC
  ไม่พอ cover funding 8% + loss) และ constraint approval ≥ 75% บังคับให้อนุมัติ loan ที่ขาดทุน

## MOB-6 A/E — DESCRIPTIVE / EXPLORATORY (relabelled after independent review CR-1) — `reports/phase2/mob6_test.md`

> **แก้ไข:** ส่วนนี้เคยถูกเรียกว่า "out-of-discovery test" แต่ค่า A/E6 ของ 2016–17 ถูกคำนวณและ commit ใน Phase 1 exploratory file
> (commit 5b35a6e) ก่อน pre-register thresholds (commit 1203ada) → ไม่ใช่ confirmatory. Lead time 6 เดือนเป็นจริงโดยนิยาม; truth ใช้ default events ชุดเดียวกัน;
> base rate 100%. Discovery period (2014Q1–2015Q4): M2 sensitivity 1/2 (พลาด 2015Q4), specificity 6/6; M1 2/2, 6/6

Thresholds (>1.10 amber, >1.25 red) registered ใน commit 1203ada — หลังจากค่าของ 2016–17 ถูกเห็นแล้ว (descriptive เท่านั้น)
| model | 2016Q1–2017Q3 quarters | truth YES | flagged amber+ | lead vs MOB-12 | specificity |
|---|---:|---:|---|---:|---|
| M1 | 7 | 7 | 7/7 | 6 เดือน (โดยนิยาม) | ทดสอบไม่ได้ (base rate 100%) |
| M2 | 7 | 7 | 7/7 | 6 เดือน (โดยนิยาม) | ทดสอบไม่ได้ (base rate 100%) |
- A/E6 อยู่ที่ 1.36–1.82 (red ทุก quarter, รวม 2017Q4 ที่ยังไม่มี truth: 1.58–1.63)
- A/E6 สูงกว่า A/E12 ของ quarter เดียวกัน (เช่น 2017Q2: 1.82 vs 1.48) → default ช่วงต้นเพิ่มมากกว่าช่วงหลัง; signal นี้อาจ "ไว" เกิน
  และ false-alarm rate ยังไม่รู้ → ใช้คู่กับ MOB-12 ไม่ใช่แทน

## What worked / what failed

**Worked**
- Pre-registered ทุกขั้นก่อนดูข้อมูล macro / fit; Plan B rule ทำงานตามที่ออกแบบ (จับ (b) ที่ผ่านแบบหลอก ๆ ได้)
- Competing-risks lifetime PD calibrate ดีใน train/validation และจัดการ censoring ของ 2016–2018 ได้ตรง ๆ
- ECL pipeline ครบ (PD × LGD × EAD, discount, stage logic) พร้อม backtest กับ realised loss จริง
- MOB-6 signal ให้ภาพที่สอดคล้องกับ MOB-12 (descriptive) — ยังไม่มี confirmatory evidence

**Failed / ข้อจำกัด**
- **Macro (B) ล้มเหลว** — unemployment อธิบาย drift ของ LC ไม่ได้ (ทิศผิด); ECL จึงไม่มี forward-looking component
- **Lifetime EL ต่ำกว่า realised loss (realised = 1.17×)** สำหรับ 2015 vintage (ratio 1.36–1.52 ใน band ที่ปลอดภัย) — model ที่ calibrate บน 2012–13 ไม่รู้เรื่อง drift
- **C แพ้ approve-all บน metric ที่ pre-register** — เพราะ metric (undiscounted) ไม่เหมาะ; exploratory metric ที่ถูกกว่าบอกว่า C ≈ PD cutoff ธรรมดา
- **Staging เป็น ex-post illustration เท่านั้น** (E4): monthly DPD ไม่มี; stage 2/3 ใช้ missed instalments จาก final status (hindsight)
- MOB-6: specificity ทดสอบไม่ได้
- Event timing จาก last_pymnt_d (approximation); defaults ที่ last payment หลัง MOB 35 ถูก censor ที่ 36 (หายาก)

## Deviations from pre-registration
1. **C: เพิ่ม exploratory "realised NPV @ discount rate"** หลังเห็นว่า metric ที่ pre-register (undiscounted) ทำให้ approve-all ชนะ — ติด label ชัด, ไม่ใช้เป็น headline
2. `p2_loans.parquet` ถูก rebuild เพื่อเก็บ application features (ใช้คำนวณ M1 score สำหรับเปรียบเทียบใน C) — rows/ค่าเดิมทั้งหมด, A re-run ได้ผลเหมือนเดิม
3. FRED → BLS API โดยตรง (prereg อนุญาต fallback นี้ไว้แล้ว — ไม่นับเป็น deviation แต่บันทึกไว้)
4. **Deterministic re-run** (row-order fix; ดู 02 §10 ข้อ 5) — θ −0.0185 → −0.0379, rule (c) 0.959 → 0.911, overlay 58%/11% → 54%/6%,
   lifetime PD 13.4% → 13.6%; decisions ไม่เปลี่ยน. ตัวเลขทั้งหมดในเอกสารนี้เป็นของ run ใหม่
5. **MOB-6 relabel** (review CR-1) — ไม่ใช่ confirmatory test; ข้อเสนอ test ใหม่อยู่ใน notes/06_quality_report.md (รอ Nat ตัดสิน)
6. **Staging/ECL caveats** (review MA-5, MA-6) — ระบุ hindsight ของ stage 3 และการไม่ refit; การแก้จริงต้องเปลี่ยน spec → รอ Nat
8. **E3–E5 (Nat decisions, pre-registered 4562602):** bootstrap ของ rule (a) สุ่ม subsample ใหม่ทุก replicate (CI [−0.0935, −0.0045], ยัง FAIL);
   staging เปลี่ยนเป็นนิยาม E4; ECL benchmark อยู่ใน notes/10_extensions_results.md
7. **Bug fix (off-by-one) ใน staging ณ 2015-12-31:** code เดิมนับ payments due เกิน 1 เดือน → stage 3 รวม loans ที่ first missed payment
   due Jan-2016 (ขัดกับ prereg "≤ Dec-2015"). แก้ให้ตรง prereg: stage 3 4,828 → 3,871 loans, stage 1 allowance $112.1m → $112.3m (3.91% → 3.75%);
   day-1 ECL และ backtest ไม่กระทบ (tests/test_riskutils.py::test_stage3_requires_first_missed_payment_due_by_report)
นอกนั้นเป็นไปตาม prereg (event coding, model spec, time split, rule a/b/c, ECL components, C constraints, MOB-6 thresholds)

## Implications / next
- Write-up story ครบแล้ว: "model ปี 2014 ranking รอด, calibration/ECL ไม่รอด (+17% loss), PSI ไม่เห็น, A/E เห็นช้า 12–18 เดือน, macro อธิบายไม่ได้"
- ถ้าจะทำต่อ: (i) management overlay สำหรับ ECL จาก early A/E (MOB-6/12) — ต้อง pre-register; (ii) ทดสอบ MOB-6 specificity บนช่วงที่ไม่มี drift
  (เช่น re-reference ด้วย model ที่ recalibrate) ; (iii) Phase 3 write-up

## Addendum (Nat decision 2) — management overlay, ILLUSTRATIVE / IN-SAMPLE — `reports/phase2/overlay.md`
Overlay = predicted lifetime EL × A/E ของ cumulative default ที่ MOB k (A model), ต่อ issue quarter 2015 (rule กำหนดไว้ใน header ของ `src/phase2/overlay.py` ก่อนรัน)
| | EL | ปิด gap ได้ | รู้ได้เมื่อ |
|---|---:|---:|---|
| predicted (no overlay) | $234.9m | – | origination |
| overlay MOB-6 | $237.3m | 6% | 2016-03 → 2016-12 |
| overlay MOB-12 | $256.0m | **54%** | 2016-09 → 2017-06 |
| realised | $273.8m | – | – |
- MOB-6 ปิดได้น้อย: ภายใต้ hazard shape ของ A model, default ช่วงต้นของ 2015 ใกล้ expected (A/E6 0.91–1.09) — ส่วนเกินมาทีหลัง
- ไม่ใช่วิธีที่ validate แล้ว: ค่า MOB-6/12 ของทุก vintage ถูกดูไปแล้ว — ไม่มี vintage ที่ยังไม่เคยเห็นเหลือ
- Bug ที่เจอและแก้ก่อนรายงาน: default_mob ใน p2_loans เป็น nullable Int64 → comparison คืน NA → A/E ≈ 7 ในรอบแรก (แก้ด้วย fillna);
  ตรวจแล้ว script อื่นไม่โดน (fit_A ใช้ fillna, build_loans/ecl แปลงเป็น float, mob6_test ใช้ Phase 1 base ที่เป็น float)
