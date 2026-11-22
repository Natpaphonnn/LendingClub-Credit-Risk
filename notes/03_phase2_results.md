# 03 — Phase 2 results (A survival/lifetime PD, B macro → failed → C, ECL, MOB-6) — 2026-11-19 (revised after independent validation)

Pre-registration: `notes/03_prereg_phase2.md` (commit 1203ada — commit **ก่อน** ดาวน์โหลด macro data และก่อน fit).
Code: `src/phase2/`; ตาราง: `reports/phase2/`; figures: `reports/figures/p2_*.png`.
อัปเดต 2026-11-20 หลัง gate round 1: M2 retrain ด้วย monotone_constraints_method="intermediate" (bug R5-1 — "advanced" ละเมิด constraint); ตัวเลขเดิมอยู่ใน git history.
E5 refit benchmark แก้ตาม R7-1 / R2-1 (refit ณ 2014-12 identify ได้แค่ MOB 1–21) — ดู notes/10_extensions_results.md.
อัปเดตหลัง gate round 2 (PASS, mean 8.22): relabel DPD ของ staging / default definition, macro CI sentence, policy C wording, E5 lower bound — ดู Deviations ข้อ 10.

Reproduce (~5 นาที, ส่วนใหญ่คือ bootstrap ของ B):
```
nice -n 19 .venv/bin/python -I src/phase2/fetch_bls.py
for s in build_loans fit_A rule_B ecl policy_C mob6_test; do nice -n 19 .venv/bin/python -I src/phase2/$s.py; done
```

---

## TL;DR

1. **A ใช้ได้ (ระดับ portfolio):** competing-risks hazard (default vs prepayment, Current = censored) fit บน 2012-09–2013-12 ให้ A/E ≈ 1.00 ใน train
   และ 0.98–1.03 บน validation 2014 (ราย band ไม่ calibrate — ดู by-band A/E / C22) แต่ under-predict ตาม drift ที่เห็นใน Phase 1: OOT 2015 A/E 1.09–1.12, 2016 1.27–1.39, 2017 1.43 (MOB 12).
   ถ้า treat prepayment เป็น censoring (hazard เดิม), lifetime PD จะ over-state: loans Jan–Sep 2015 (ดูได้ครบ 36 เดือน) 13.6% → 18.2% (actual ภายใน MOB 36 = 14.7%);
   ทั้งปี 2015 13.4% → 18.0% (ตารางด้านล่าง; Q4 ยังดูไม่ครบ 36 เดือน)
2. **B ไม่ผ่าน Plan B rule → เปลี่ยนเป็น A + C** (ตามกฎที่เขียนไว้ก่อน Phase 1): (a) FAIL — θ ไม่เป็นบวก: −0.045 [−0.099, −0.009] (E3: subsample สุ่มใหม่ทุก replicate; run ก่อนหน้า −0.019 และ −0.038 — ติดลบทุกครั้ง แต่ตำแหน่ง CI เปราะ);
   (b) PASS แบบ "ถูกด้วยเหตุผลผิด"; (c) FAIL — adverse/baseline = 0.89 (adverse ทำให้ PD **ลดลง**) → macro signal ถูก confound กับ drift ของ LC
3. **ECL (score-only, ไม่มี forward-looking overlay):** 2015 portfolio funded $3.62bn → day-1 12m ECL $100m (2.7%), lifetime ECL $201m (5.5%).
   Backtest (ไม่ใช่ provision ที่ book จริง): realised net loss **$274m vs predicted lifetime EL $232m (realised = 1.18× predicted; พลาด 15% ของ realised)**
   — ratio สูงสุดใน band ที่ปลอดภัยที่สุด (×1.44) แต่ dollar gap ใหญ่สุดอยู่ band กลาง. Gap นี้มี 3 ส่วน: drift, gradient ตาม band ที่มีอยู่แล้วบน
   validation 2014 (lp slope fit in-sample — gate R7-2) และ EAD ที่ understate (in-sample backtest ×1.03; gate R8-1). Refit ณ reporting date
   ด้วยข้อมูลที่รู้ได้จริง**ไม่ช่วยปิด gap** (E5: 1.27× — lower bound เพราะ tail MOB 22–36 ยืมจาก reference A ที่ใช้ outcome หลัง 2014;
   ใช้ tail ที่ knowable ได้ 1.41×; notes/10)
4. **C:** MILP policy ไม่ชนะ "approve all" บน metric ที่ pre-register (realised profit แบบไม่ discount: $222m vs $230m). Exploratory
   realised NPV @5%: C $46m ≫ approve all $28m แต่**แย่กว่า** Phase 1 M2 cutoff ($47m): C − cutoff = −$1.74m [−2.66, −0.82] (paired bootstrap)
   → cell structure ของ MILP ไม่ได้เพิ่มอะไรเหนือ single PD threshold; **ระดับ** threshold ที่เหมาะขึ้นกับทั้ง funding cost และ calibration ของ PD —
   threshold ที่ tune ด้วย NPV บน PD ที่ under-predict อนุมัติมากเกินไป (single threshold $44.9m < appetite cutoff $47.5m). NPV levels ขึ้นกับ
   สมมติฐาน cash timing มาก — หลักฐานคือ differences/rankings ไม่ใช่ levels; CI condition บน policies ที่เลือกแล้วและ vintage เดียว
5. **MOB-6 A/E — descriptive/exploratory เท่านั้น (relabel หลัง review CR-1):** 2016–17 red ทุก quarter แต่ค่าเหล่านี้ถูกคำนวณและ commit แล้ว
   ก่อน register thresholds, lead time 6 เดือนเป็นจริงโดยนิยาม, และทุก quarter deteriorated → ไม่ใช่ test; discovery period: M2 จับได้ 1/2 (พลาด 2015Q4), ไม่มี false alarm 6/6
   (ทุก quarter ที่มี truth deteriorated หมด). Confirmatory test บน 60m loans (E1) **FAIL**: specificity 4/6 < 80% — specificity ยังไม่ได้แสดง (notes/10)

---

## A — Survival / lifetime PD (prereg §A) — `reports/phase2/survival_A.md`, `p2_A_vintage_ae.png`

- Data: 1,433,835 loans (36m, Individual, meets policy, 2009–2018) → `data/interim/p2_loans.parquet`. Events coded ตาม prereg
  (default = last payment + 1; prepay = Fully Paid ≥ 3 เดือนก่อนครบกำหนด; อื่น ๆ censored ที่ min(36, 2018-09))
- Train: 120,683 loans, 3,030,762 loan-months, 14,902 defaults, 61,594 prepayments; Newton converged ใน 10 iterations
- Coefficients ที่น่าสนใจ: default — lp (logit M2 PD) 1.31 (SE 0.03, descriptive เท่านั้น — lp เป็น generated regressor; gate R7-4), lp × t/36 = −0.45 → อำนาจของ application score ลดลงตาม MOB
  (เหมาะกับ behavioural score ในอนาคต); prepay — lp −0.17 (คนเสี่ยงสูง prepay น้อยกว่า), int_rate +0.077/SD (ดอกแพง prepay มากกว่า)

**A/E ของ cumulative default (n-weighted ข้าม quarters ที่ observable)**
| period | n | A/E @12 | A/E @24 | A/E @36 | pred lifetime PD | naive (no prepay) |
|---|---:|---:|---:|---:|---:|---:|
| train 2012Q4–13 | 115,603 | 1.004 | 1.010 | 1.008 | 12.2% | 16.7% |
| valid 2014 | 162,570 | 0.985 | 1.018 | 1.026 | 13.3% | 17.9% |
| OOT 2015 | 282,934 | 1.101 | 1.124 | 1.086 | 13.4% | 18.0% |
| 2016 (censored) | 318,277 | 1.393 | 1.266 | – | 13.0% | 17.5% |
| 2017 (censored) | 296,484 | 1.432 | – | – | 11.6% | 15.9% |
| 2018 (censored) | 202,395 | – | – | – | 10.9% | 14.9% |
- Censoring: เทียบเฉพาะ MOB ที่ observable ทั้ง quarter (issue + MOB ≤ 2018-09); 2018 ยังไม่ถึง MOB 12 จึงมีแต่ prediction
- OOT 2015 loan-level: Gini ของ lifetime PD 36.4 (M2 PD เดี่ยว 36.7); mean lifetime PD 13.4% vs final bad 14.9% (like-for-like: default ภายใน MOB 36
  = 14.7% — final bad รวม default หลัง MOB 36; gate round 2 R7-5)
- ข้อจำกัด (gate round 2 R7-3): prepay hazard แบบ spline เรียบลงไม่ถึง structural zero ที่ MOB 34–36 (payoff ช่วงนั้นคือ maturity → censored);
  ใส่ term t ≥ 34 แล้ว lifetime PD 13.43% → 13.42% — ไม่กระทบ headline แต่ timing ของ prepay ช่วงท้ายผิดรูป
- A/E@36 ตาม M2-PD quintile band (gate R7-2): validation 2014 band 1 (ปลอดภัยสุด) 1.30 → band 5 0.92; OOT 2015 1.38 → 0.95 → gradient นี้
  **มีอยู่แล้วก่อน drift** (lp slope fit บน in-sample scores ของ M2) แล้ว drift ขยายมัน (survival_A.md)

## B — Macro, Plan B rule (prereg §B) — `reports/phase2/macro_B.md`, `macro_B.json`

Data: BLS LAUS state unemployment (SA), 51 series, 2007–2018, ผ่าน BLS API (FRED timed out) — public domain, บันทึกใน data_sources.md §4

| rule | statistic | threshold | result |
|---|---|---|---|
| (a) sign + significance | θ = γ_u + γ_Δ12u (default) = **−0.0452**, 95% block-bootstrap CI (24 issue quarters, B=200, subsample redrawn per replicate — E3) [−0.0990, −0.0095] | θ > 0, CI > 0 | **FAIL** |
| (b) OOT value | cell error 2.145 pp (macro) vs 2.981 pp (score-only) = −28.0%; log loss 0.39235 vs 0.39420 | ≤ −10%, log loss ไม่แย่ลง | PASS |
| (c) stress size | adverse/baseline lifetime PD = **0.893** (12.48% → 11.15%) | 1.1–3.0 | **FAIL** |

**→ Decision: B FAILS → Plan B = A + C** (macro เหลือเป็น "weak" sensitivity เท่านั้น — ไม่ใช้ใน ECL)

ทำไมถึงล้มเหลว (การตีความ, ไม่ใช่ส่วนของ rule):
- γ_u (level) = −0.066 **ติดลบ**: ใน 2009–2014 unemployment ลดลงต่อเนื่อง (median state 8.6% ปลายปี 2009 → 5.5% ต้นปี 2015)
  ขณะที่ default rate ของ LC ไต่ขึ้น (credit box ขยาย) → model เรียนว่า "unemployment ต่ำ = default สูง" = time-trend confounding
- γ_Δ12u = +0.020 มีทิศถูก (unemployment ที่ **เพิ่มขึ้น** ทำให้ default สูงขึ้น) แต่ไม่พอชดเชย level
- (b) ผ่านเพราะ level coefficient ติดลบทำให้ predict PD สูงขึ้นในปี 2015 (unemployment ต่ำลง) ซึ่งบังเอิญตรงกับ drift → **ถูกด้วยเหตุผลผิด**
  นี่คือเหตุผลที่ rule ต้องผ่านครบทั้ง 3 ข้อ
- (b) เป็น out-of-time ตาม vintage ไม่ใช่ตาม calendar: loan-months ของ fit panel ยาวถึง 2015–17 ซ้อนกับ outcome window ของ vintage 2015 (gate R3-5)
- CI ทั้งสองแบบไม่คร่อม 0 (ฝั่งลบ): percentile [−0.0990, −0.0095], normal-approximation (θ ± 1.96·SD) [−0.0874, −0.0030] (reports/phase2/macro_B.md;
  ประโยคเดิม "normal CI จะคร่อม 0" เป็นจริงเฉพาะก่อน R5-1 retrain — แก้ให้คำนวณใน code แล้ว, gate round 2 R9-1); ผลของ rule ไม่ขึ้นกับวิธีทำ CI เพราะ θ ไม่เป็นบวก.
  Clusters ไม่เท่ากัน: ~85% ของ loans อยู่ใน 10 quarters ตั้งแต่ 2012Q3 → effective clusters น้อยกว่า 24, CI อาจแคบเกินจริง (gate round 2 R9-5)
- Sensitivity (2012-09–2014, ไม่นับใน rule): θ = +0.030 [−0.011, +0.062] — ทิศถูกแต่ CI คร่อม 0 (มีแค่ 10 issue quarters)
- ข้อจำกัด: มี downturn เดียว และ LC แทบไม่ได้ปล่อยกู้ช่วงนั้น; LAUS เป็นข้อมูล revised ไม่ใช่ real-time vintage

## ECL — TFRS 9-style, OOT portfolio (2015) — `reports/phase2/ecl.md`, `ecl.json`, `p2_ecl_backtest.png`

- PD: A (score-only hazard) — **ไม่มี forward-looking macro overlay** เพราะ B fail → เป็นช่องว่างจาก TFRS 9 ที่ต้องบอกตรง ๆ
- **LGD = 88.8%** [88.6, 89.0] (EAD-weighted, 15,007 train defaults; recovery เฉลี่ยแค่ ~11% ของ EAD ณ default). แทบไม่ต่างตาม band (87.5–89.0%).
  หมายเหตุ: ตัวเลข ~0.58 ใน audit คือ loss ÷ funded (รวม principal ที่จ่ายมาแล้วก่อน default) ไม่ใช่ LGD ต่อ EAD
- EAD = scheduled annuity balance; prepayment ผ่าน competing risk; discount ด้วย EIR (= contractual int_rate; ไม่รวม origination fees)

| 2015 portfolio | value |
|---|---:|
| loans / funded | 282,934 / $3,622.8m |
| pred lifetime PD vs actual default | 13.42% vs 14.88% |
| day-1 12-month ECL (Stage 1 ทั้งหมด ณ origination) | $99.6m (2.7% of funded) |
| lifetime ECL (discounted) | $200.6m (5.5%) |
| **predicted lifetime EL (undiscounted) vs realised net principal loss** | **$232.4m vs $273.8m → ×1.18** |

Backtest by quarter: ×1.11 (2015Q1), ×1.19, ×1.16, ×1.23 (2015Q4). By risk band (M2-PD quintile, 1 = safest): ×1.44, ×1.43, ×1.34, ×1.25, ×1.03
→ ratio สูงสุดใน**กลุ่มที่ดูปลอดภัย** (สอดคล้องกับ vintage curves ใน Phase 1: B5 default ×2) แต่ dollar gap ใหญ่สุดอยู่ band 3–4;
  gradient นี้มีอยู่แล้วบน validation 2014 (ดู A) จึงไม่ใช่ผลของ drift ล้วน ๆ
- In-sample backtest ของ A บน development window (2012-09..2013-12): realised $92.4m vs predicted $89.8m (×1.03); EAD จริง ณ default (funded − principal
  received) = ×1.024 ของ scheduled balance → scheduled-balance EAD understate exposure ~2–3% → ส่วนหนึ่งของ gap เป็น structural ไม่ใช่ drift.
  Decomposition OOT: count ×1.108 × EAD/default ×1.057 × LGD ×1.005 (reports/phase2/ecl_benchmark.md; gate R8-1)
- 12-month backtest (descriptive; gate R8-6): 12m EL $108.1m vs realised loss ของ loans ที่ default ภายใน MOB 12 $123.7m (×1.14); 12m PD 4.24% vs 4.66%
- Hessian SEs ถูกตัดออกจาก report: fit ใช้ weighted subsample + ไม่คิด clustering จึงใช้ทำ inference ไม่ได้ (review MA-3)

**Allowance ณ 2015-12-31 (stage logic; เฉพาะ 2015-vintage sub-portfolio ไม่ใช่ทั้ง book ณ วันนั้น):**
DPD mapping (gate round 2 R8-1): missed instalment แรก due ในเดือนหลัง last payment → ณ report date loan ที่ค้าง m งวด ≈ 30(m − 1) ถึง 30m DPD
→ label เดิม "1 missed ≈ 30 DPD, 3 ≈ 90 DPD" ใจดีไป 1 bucket. Threshold ที่ pre-register (E4) คงไว้; relabel เป็น ≈ 0–60 / ≥ 60 DPD
| stage | loans | gross EAD | allowance | coverage |
|---|---:|---:|---:|---:|
| Stage 1 (no missed instalment visible; 12m ECL) | 263,610 | $2,992.3m | $111.0m | 3.71% |
| Stage 2 (1–2 missed instalments ≈ 0–60 DPD, ex-post proxy; lifetime ECL) — E4 | 1,571 | $17.1m | $1.5m | 8.9% |
| Stage 3 (≥ 3 missed instalments ≈ ≥ 60 DPD; LGD × EAD at default) — E4 | 2,300 | $25.1m | $22.25m | 88.8% |
| derecognised (prepaid ≤ Dec-2015) | 15,453 | – | – | – |
| memo: ของ stage 3, ≥ 6 missed instalments (≈ ≥ 150 DPD; น่าจะ write off แล้วตาม charge-off policy ~150 DPD ของ LC; gate R8-4) | 682 | $7.6m | $6.8m | 88.8% |
| memo: ของ stage 3, missed 5 งวดพอดี (≈ 120–150 DPD; borderline write-off; gate round 2 R2-6) | 439 | $4.8m | $4.3m | 88.8% |

Post-hoc variant ที่สอดคล้องกับ backstop 30/90 DPD (descriptive, ไม่ใช่ pre-register; reports/phase2/ecl.md): stage 2 = 2–3 missed (≈ 30–90 DPD),
stage 3 = ≥ 4 missed (≈ ≥ 90 DPD), 1 missed อยู่ stage 1:

| stage (backstop variant) | loans | gross EAD | allowance | coverage |
|---|---:|---:|---:|---:|
| Stage 1 | 264,320 | $2,999.9m | $111.5m | 3.72% |
| Stage 2 (2–3 missed) | 1,521 | $16.4m | $1.5m | 8.9% |
| Stage 3 (≥ 4 missed) | 1,640 | $18.0m | $15.9m | 88.8% |

**Ex-post illustration** (E4, notes/08_prereg_extensions.md): monthly DPD ไม่มีในข้อมูล; missed instalments เห็นได้เฉพาะ loans ที่สุดท้าย charge off
(delinquency ที่ cure ภายหลังมองไม่เห็น → stage 2 understated). Version ที่ refit ณ 2015-12-31 + discounted LGD: notes/10_extensions_results.md

## C — Profit-optimal policy (prereg §C; ทำเพราะ B fail) — `reports/phase2/policy_C.md`, `p2_C_policy.png`

MILP บน 30 cells (M2-PD decile × amount band), max expected NPV (A hazards, LGD 88.8%, discount 5%) บน validation 2014
ภายใต้ approval ≥ 75% และ expected bad (mean M2 PD) ≤ 11% → approve 26/30 cells (ตัด decile 9 ทั้งหมด + decile 8 band 10–20k)

| OOT 2015 | approval | realised bad | **realised profit (pre-reg, undiscounted)** | expected NPV @5% | realised NPV @5% (EXPLORATORY) |
|---|---:|---:|---:|---:|---:|
| C: MILP cells | 86.3% | 12.58% | $222.3m | $71.3m | $45.8m |
| approve all | 100% | 14.88% | **$230.3m** | $50.6m | $28.4m |
| Phase 1 M2 cutoff (PD ≤ 0.1994) | 81.6% | 11.88% | $217.0m | $71.2m | **$47.5m** |
| Phase 1 M1 cutoff (score ≥ 532) | 77.9% | 11.73% | $208.0m | $65.6m | $43.3m |
| single PD threshold, same objective (PD ≤ 0.2288; benchmark — gate R9-4) | 87.6% | 12.72% | $225.2m | $71.3m | $44.9m |

- **บน metric ที่ pre-register, C แพ้ approve-all** (−$8.0m): metric แบบไม่ discount ไม่คิด cost of funds → loan ที่คืนเงินรวมมากกว่ายืม
  ดู "กำไร" หมดแม้จะเสี่ยงสูง → metric นี้เลือกไม่ดี (บันทึกเป็นบทเรียน)
- Exploratory (ไม่ได้ pre-register): discount 5% พร้อม timing โดยประมาณ → C ดีกว่า approve-all +$17.4m [15.6, 19.0] (+61%) แต่**แย่กว่า M2 cutoff**
  −$1.74m [−2.66, −0.82] (paired bootstrap รายloan; block ราย issue month [−2.69, −0.77]) — gate R9-1
- C อนุมัติมากกว่า M2 cutoff (86% vs 82%) เพราะ constraint ใช้ model PD ซึ่ง under-predict — ตั้งแต่ 2014 แล้ว (realised approved bad บน 2014 = 11.67%
  เกิน 11% อยู่แล้ว; gate R9-3) และหนักขึ้นหลัง drift → realised bad 12.6% บน 2015
- C optimal เฉพาะภายใน 30 cells ที่ pre-register: single PD threshold ที่เลือกบน 2014 ด้วย objective + constraints เดียวกันได้ expected NPV เท่ากัน
  ($71.3m) → cell structure ไม่ได้เพิ่มอะไร (gate R9-4)
- Sensitivity: discount 3% → C − M2 cutoff = +$0.98m [−0.07, 2.05] (ไม่ significant; exploratory NPV $113.6m vs $112.6m); 8% → ทุก policy NPV ติดลบ
  (ดอกเบี้ย LC ไม่พอ cover funding 8% + loss); C ดีกว่า M2 cutoff +$4.63m [4.02, 5.22] เพราะอนุมัติน้อยกว่า (75.1% vs 81.6%) — single threshold
  ที่ tune ด้วย objective เดียวกัน (PD ≤ 0.1742) ได้ใกล้กัน → สรุป: optimizer ไม่ช่วย; **ระดับ** cutoff ที่เหมาะขึ้นกับ funding cost **และ** calibration
  ของ PD — ที่ 5% threshold ที่ tune ด้วย NPV บน PD ที่ under-predict ได้ realised NPV $44.9m ต่ำกว่า appetite cutoff $47.5m (gate round 2 R9-2)
- ข้อควรระวัง (gate round 2 R9-3/R9-4): realised NPV levels ขึ้นกับสมมติฐาน cash timing มาก (timing แบบอื่นลด levels ลงราวครึ่ง) แต่ sign/ranking
  ของ differences คงเดิม → อ้าง differences ไม่ใช่ levels; paired bootstrap condition บน policies ที่เลือกแล้ว (ไม่ re-optimise) และครอบคลุม vintage เดียว

## MOB-6 A/E — DESCRIPTIVE / EXPLORATORY (relabelled after independent review CR-1) — `reports/phase2/mob6_test.md`

> **แก้ไข:** ส่วนนี้เคยถูกเรียกว่า "out-of-discovery test" แต่ค่า A/E6 ของ 2016–17 ถูกคำนวณและ commit ใน Phase 1 exploratory file
> (commit 5b35a6e) ก่อน pre-register thresholds (commit 1203ada) → ไม่ใช่ confirmatory. Lead time 6 เดือนเป็นจริงโดยนิยาม; truth ใช้ default events ชุดเดียวกัน;
> base rate 100%. Discovery period (2014Q1–2015Q4): M2 sensitivity 1/2 (พลาด 2015Q4), specificity 6/6; M1 2/2, 6/6

Thresholds (>1.10 amber, >1.25 red) registered ใน commit 1203ada — หลังจากค่าของ 2016–17 ถูกเห็นแล้ว (descriptive เท่านั้น)
| model | 2016Q1–2017Q3 quarters | truth YES | flagged amber+ | lead vs MOB-12 | specificity |
|---|---:|---:|---|---:|---|
| M1 | 7 | 7 | 7/7 | 6 เดือน (โดยนิยาม) | ทดสอบไม่ได้ (base rate 100%) |
| M2 | 7 | 7 | 7/7 | 6 เดือน (โดยนิยาม) | ทดสอบไม่ได้ (base rate 100%) |
- A/E6 อยู่ที่ 1.35–1.82 (red ทุก quarter, รวม 2017Q4 ที่ยังไม่มี truth: 1.58–1.63)
- A/E6 สูงกว่า A/E12 ของ quarter เดียวกัน (เช่น 2017Q2: 1.82 vs 1.48) → default ช่วงต้นเพิ่มมากกว่าช่วงหลัง; signal นี้อาจ "ไว" เกิน
  และ false-alarm rate ยังไม่รู้ → ใช้คู่กับ MOB-12 ไม่ใช่แทน

## What worked / what failed

**Worked**
- Pre-registered ทุกขั้นก่อนดูข้อมูล macro / fit; Plan B rule ทำงานตามที่ออกแบบ (จับ (b) ที่ผ่านแบบหลอก ๆ ได้)
- Competing-risks lifetime PD calibrate ดีใน train/validation ระดับ portfolio (ราย band ไม่ — C22) และจัดการ censoring ของ 2016–2018 ได้ตรง ๆ
- ECL pipeline ครบ (PD × LGD × EAD, discount, stage logic) พร้อม backtest กับ realised loss จริง
- MOB-6 signal ให้ภาพที่สอดคล้องกับ MOB-12 (descriptive) — ยังไม่มี confirmatory evidence

**Failed / ข้อจำกัด**
- **Macro (B) ล้มเหลว** — unemployment อธิบาย drift ของ LC ไม่ได้ (ทิศผิด); ECL จึงไม่มี forward-looking component
- **Lifetime EL ต่ำกว่า realised loss (realised = 1.18×)** สำหรับ 2015 vintage (ratio 1.34–1.44 ใน band 1–3) — drift + gradient ที่มีตั้งแต่ validation +
  EAD understate (in-sample ×1.03); refit ณ reporting date ด้วยข้อมูลที่รู้ได้จริงไม่ช่วย (E5 1.27× lower bound; knowable tail 1.41×)
- **C แพ้ approve-all บน metric ที่ pre-register** — เพราะ metric (undiscounted) ไม่เหมาะ; exploratory metric ที่ถูกกว่าบอกว่า C ไม่ดีกว่า PD cutoff ธรรมดา
  (แย่กว่าที่ 5%, ไม่ต่างที่ 3%)
- **Staging เป็น ex-post illustration เท่านั้น** (E4): monthly DPD ไม่มี; stage 2/3 ใช้ missed instalments จาก final status (hindsight)
- MOB-6: specificity ทดสอบไม่ได้ใน 36m 2016–17; confirmatory test บน 60m (E1) FAIL (specificity 4/6)
- Event timing จาก last_pymnt_d (approximation); defaults ที่ last payment หลัง MOB 35 ถูก censor ที่ 36 (หายาก)

## Deviations from pre-registration
1. **C: เพิ่ม exploratory "realised NPV @ discount rate"** หลังเห็นว่า metric ที่ pre-register (undiscounted) ทำให้ approve-all ชนะ — ติด label ชัด, ไม่ใช้เป็น headline
2. `p2_loans.parquet` ถูก rebuild เพื่อเก็บ application features (ใช้คำนวณ M1 score สำหรับเปรียบเทียบใน C) — rows/ค่าเดิมทั้งหมด, A re-run ได้ผลเหมือนเดิม
3. FRED → BLS API โดยตรง (prereg อนุญาต fallback นี้ไว้แล้ว — ไม่นับเป็น deviation แต่บันทึกไว้)
4. **Deterministic re-run** (row-order fix; ดู 02 §10 ข้อ 5) — ก่อน → หลัง (history): θ −0.0185 → −0.0379, rule (c) 0.959 → 0.911, overlay 58%/11% → 54%/6%,
   lifetime PD 13.4% → 13.6%; decisions ไม่เปลี่ยน. ตัวเลขปัจจุบันเปลี่ยนอีกครั้งหลัง gate fix (ข้อ 9)
5. **MOB-6 relabel** (review CR-1) — ไม่ใช่ confirmatory test; ข้อเสนอ test ใหม่อยู่ใน notes/06_quality_report.md (รอ Nat ตัดสิน)
6. **Staging/ECL caveats** (review MA-5, MA-6) — ระบุ hindsight ของ stage 3 และการไม่ refit; Nat ตัดสินแล้ว → E4 (staging) และ E5 (refit benchmark)
8. **E3–E5 (Nat decisions, pre-registered 4562602):** bootstrap ของ rule (a) สุ่ม subsample ใหม่ทุก replicate (CI [−0.0935, −0.0045] = ค่าก่อน R5-1
   retrain; ปัจจุบัน [−0.0990, −0.0095], ยัง FAIL);
   staging เปลี่ยนเป็นนิยาม E4; ECL benchmark อยู่ใน notes/10_extensions_results.md
7. **Bug fix (off-by-one) ใน staging ณ 2015-12-31:** code เดิมนับ payments due เกิน 1 เดือน → stage 3 รวม loans ที่ first missed payment
   due Jan-2016 (ขัดกับ prereg "≤ Dec-2015"). แก้ให้ตรง prereg: stage 3 4,828 → 3,871 loans, stage 1 allowance $112.1m → $112.3m (3.91% → 3.75%);
   day-1 ECL และ backtest ไม่กระทบ (tests/test_riskutils.py::test_stage3_requires_first_missed_payment_due_by_report)
9. **Gate round 1 fixes (2026-11-20, bugs — ไม่ใช่ spec change ยกเว้นที่ระบุ):** M2 retrain ด้วย monotone method "intermediate" (R5-1) → ตัวเลข A, B, ECL, C,
   overlay เปลี่ยนเล็กน้อย; decisions ไม่เปลี่ยน (B ยัง FAIL: θ −0.045). E5 refit ณ 2014-12 identify ได้แค่ MOB 1–21 (R7-1 / R2-1) → ใช้ refit สำหรับ
   MOB 1–21 + reference tail (assumption ที่ระบุชัด, bug-driven deviation) — notes/10. Stage 3 เพิ่ม memo row (m ≥ 6). C เพิ่ม paired bootstrap CIs และ
   single-threshold benchmark (descriptive)
10. **Gate round 2 (2026-11-20, PASS) — relabels / post-hoc descriptive เท่านั้น ไม่มี threshold ที่ pre-register เปลี่ยน:** DPD labels ของ E4 staging
   (≈ 0–60 / ≥ 60 DPD) + backstop variant (R8-1) + memo m = 5 (R2-6); "90-DPD" (d + 2) relabel เป็น default ที่ missed งวดที่ 3 (≈ 60 DPD) + post-hoc
   d + 3 ≈ 90 DPD: 12m ECL $67.8m, ×1.19 (R8-2); E5 (c) 1.27× เป็น lower bound + knowable-tail (c'') 1.41× (R7-1); macro CI sentence คำนวณใน code (R9-1);
   policy C wording (R9-2/R9-3/R9-4); A/E flags strict > ตาม prereg (R6-3)
นอกนั้นเป็นไปตาม prereg (event coding, model spec, time split, rule a/b/c, ECL components, C constraints, MOB-6 thresholds)

## Implications / next
- Write-up story ครบแล้ว: "model ปี 2014 ranking รอด, calibration/ECL ไม่รอด (+18% loss), PSI ไม่เห็น, A/E เห็นช้า 12–18 เดือน, macro อธิบายไม่ได้"
- ถ้าจะทำต่อ: (i) management overlay สำหรับ ECL จาก early A/E (MOB-6/12) — ต้อง pre-register; (ii) MOB-6 specificity — ทดสอบแล้วบน 60m (E1, FAIL);
  (iii) Phase 3 write-up

## Addendum (Nat decision 2) — management overlay, ILLUSTRATIVE / IN-SAMPLE — `reports/phase2/overlay.md`
Overlay = predicted lifetime EL × A/E ของ cumulative default ที่ MOB k (A model), ต่อ issue quarter 2015 (rule กำหนดไว้ใน header ของ `src/phase2/overlay.py` ก่อนรัน)
| | EL | ปิด gap ได้ | รู้ได้เมื่อ |
|---|---:|---:|---|
| predicted (no overlay) | $232.4m | – | origination |
| overlay MOB-6 | $237.1m | 11% | 2016-03 → 2016-12 |
| overlay MOB-12 | $255.8m | **57%** (in-sample, illustrative) | 2016-09 → 2017-06 |
| realised | $273.8m | – | – |
- MOB-6 ปิดได้น้อย: ภายใต้ hazard shape ของ A model, default ช่วงต้นของ 2015 ใกล้ expected (A/E6 0.92–1.11) — ส่วนเกินมาทีหลัง
- ไม่ใช่วิธีที่ validate แล้ว: ค่า MOB-6/12 ของทุก vintage ถูกดูไปแล้ว — ไม่มี vintage ที่ยังไม่เคยเห็นเหลือ
- Bug ที่เจอและแก้ก่อนรายงาน: default_mob ใน p2_loans เป็น nullable Int64 → comparison คืน NA → A/E ≈ 7 ในรอบแรก (แก้ด้วย fillna);
  ตรวจแล้ว script อื่นไม่โดน (fit_A ใช้ fillna, build_loans/ecl แปลงเป็น float, mob6_test ใช้ Phase 1 base ที่เป็น float)
