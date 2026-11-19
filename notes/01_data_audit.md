# 01 — Data audit (Phase 0) — 2026-11-19

สรุปผล Phase 0 (ยังไม่มี modelling) ตาม notes/00_plan.md ขั้น 2–7
ตัวเลขทั้งหมดเป็น aggregate จาก `src/audit/run_audit.py` → ตารางเต็มอยู่ที่ `reports/audit/`:
`audit_tables.md` (ทุกตาราง), `column_catalogue.md` (151 columns: class + missing + ความหมายจาก dictionary),
`missingness_by_year.md`, `fico_rate_profile.md`. Figures: `reports/figures/p0_*.png`.

Reproduce:
```
nice -n 19 .venv/bin/python -I src/audit/convert_to_parquet.py data/raw data/interim
nice -n 19 .venv/bin/python -I src/audit/run_audit.py data/interim data/raw/dictionary/LCDataDictionary.xlsx reports/audit
nice -n 19 .venv/bin/python -I src/audit/make_figures.py data/interim reports/figures
```
(แปลง CSV.gz → parquet แบบ all-VARCHAR ด้วย DuckDB, memory_limit 4 GB, ใช้เวลา ~10 วินาทีต่อไฟล์; cast ด้วย TRY_CAST ตอน query)

---

## TL;DR (สิ่งที่ Nat ต้องรู้ก่อนตัดสินใจ)

1. **เรื่อง "2007 → 2008" ข้อมูลไม่พอเป็น headline** — ปี 2007 มี 603 loans, 2008 มี 2,393 loans (รวม ~3k, bads ~650)
   ฝึก scorecard จาก 2007 แล้วไป test 2008 ไม่ได้อย่างมีความหมาย ส่วนใหญ่ของข้อมูลอยู่ที่ 2013–2018 (2.16M จาก 2.26M = 96%)
   → **เสนอปรับ story** (ดูหัวข้อ 9) ให้ 2007–08 เป็น "crisis anchor" สำหรับ stress test แทน และให้ headline เป็น
   "train 2012–14 → ยังรอดไหมเมื่อ vintage 2015–16 แย่ลง และ monitoring จับได้ทันไหม"
2. **Matured vintages:** 36m ใช้ได้ถึง issue 2015-12 (resolved ≥ 99.8%), 60m ใช้ได้ถึง 2013 (2014 ยัง 83%) — data as-of ≈ 2019-03
3. **Leakage:** 38 columns เป็น POST-origination, 9 columns เป็น LC decision/pricing output (int_rate, grade, sub_grade…) — ห้ามใช้ใน scorecard
4. **Senior items ที่แนะนำ: A (survival / lifetime PD + prepayment competing risk) + B (macro-linked PD + stress test)** —
   รวมกันเป็นเรื่อง TFRS 9 / IFRS 9 lifetime ECL ที่ธนาคารไทยใช้จริง; D ทำแบบเบา ๆ ใน core scorecard ได้; C เป็น stretch
5. **6 (NLP desc):** ทำได้แค่ side study — desc มีเฉพาะ 2007 ถึง 2014-03 (125,814 loans) แล้วหายไปเลย
   **8 (reject inference):** ทำได้แบบจำกัด — rejected file มีแค่ 9 columns และ Risk_Score เป็น FICO เฉพาะก่อน 2013-11-05
   **G (causal rate → default):** ไม่มี sharp cutoff ใน FICO → ไม่มี sharp RD; มีทางเลือกคือ repricing events (fuzzy, power ต่ำ)

---

## 1. Data & files (step 1)

ดู `notes/data_sources.md` (URL, license CC0-1.0 ตรวจผ่าน Kaggle API metadata, sha256, ขนาด)
- accepted_2007_to_2018Q4.csv.gz — 392.6 MB, rejected_2007_to_2018Q4.csv.gz — 255.5 MB (ขนาดตรงกับที่ Kaggle list)
- Data dictionary: LCDataDictionary.xlsx จาก Figshare (CC BY 4.0) — Kaggle dataset ไม่มี dictionary และหน้า LC เดิมปิดไปแล้ว
- ข้อควรระวัง license: คำอธิบายของ uploader เองบอกว่า LC มี TOS popup ตอนดาวน์โหลด → CC0 เป็น claim ของ uploader
  เราจึงยึดกฎเดิมเคร่งครัด: publish เฉพาะ code / aggregates / figures

## 2. Profile — accepted file (step 2)

| item | value |
|---|---|
| rows ในไฟล์ | 2,260,701 |
| loans (issue_d parse ได้) | **2,260,668** (ตัด 33 summary/footer rows) |
| duplicate id | 0 |
| columns | 151 (ทุกตัวมีใน dictionary) |
| issue_d | 2007-06 → 2018-12 |
| data as-of | ≈ 2019-03 (max last_pymnt_d; max last_credit_pull_d 2019-04) |
| member_id | null 100% (ไม่มี borrower id → ทำ repeat-borrower analysis ไม่ได้) |

**Volume by issue year** (ดู `reports/figures/p0_volume_by_year.png`)

| year | loans | share 60m | avg int_rate |
|---|---:|---:|---:|
| 2007 | 603 | 0 | 11.8 |
| 2008 | 2,393 | 0 | 12.1 |
| 2009 | 5,281 | 0 | 12.4 |
| 2010 | 12,537 | 0.27 | 12.0 |
| 2011 | 21,721 | 0.35 | 12.2 |
| 2012 | 53,367 | 0.19 | 13.6 |
| 2013 | 134,814 | 0.26 | 14.5 |
| 2014 | 235,629 | 0.31 | 13.8 |
| 2015 | 421,095 | 0.33 | 12.6 |
| 2016 | 434,407 | 0.26 | 13.0 |
| 2017 | 443,579 | 0.28 | 13.2 |
| 2018 | 495,242 | 0.30 | 12.7 |

**loan_status (ทั้งหมด):** Fully Paid 47.6%, Current 38.9%, Charged Off 11.9%, Late 31–120 0.95%, In Grace 0.37%,
Late 16–30 0.19%, "Does not meet the credit policy. Status: Fully Paid / Charged Off" 1,988 / 761, Default 40.
- term: 60m เริ่มปี 2010 (ก่อนนั้นมีแต่ 36m)
- application_type "Joint App" เริ่ม 2015 (511) → 2018 (68,985) — joint fields (annual_inc_joint, sec_app_*) จึง missing ~95%
- "Does not meet the credit policy" มีเฉพาะ 2007–2010 (2,749 loans; ปี 2007 = 352 จาก 603!) bad rate 23–32% เทียบกับ 13–18%
  ของ loans ที่ meet policy ปีเดียวกัน → เสนอ **exclude จาก headline model** (policy ปัจจุบันไม่ปล่อยกู้แล้ว) และรายงาน sensitivity
- policy_code = 1 ทุกแถวใน accepted

**Missingness by vintage** (ตารางเต็ม `reports/audit/missingness_by_year.md`) — feature availability เป็นขั้น ๆ:

| available ตั้งแต่ | # APP columns | ตัวอย่าง |
|---|---:|---|
| 2007 | 31 | loan_amnt, term, emp_length, home_ownership, annual_inc, dti, fico_range_low/high, delinq_2yrs, inq_last_6mths, revol_util, open_acc, total_acc, purpose, addr_state, zip_code(3 digit), earliest_cr_line |
| 2008 | 1 | pub_rec_bankruptcies |
| 2012 | 11 | acc_open_past_24mths, bc_util, mort_acc, mths_since_recent_inq, total_bc_limit … |
| 2013 | 23 | tot_cur_bal, total_rev_hi_lim, avg_cur_bal, mo_sin_*, num_* … |
| 2016 (เริ่ม 2015-12) | 14 | open_acc_6m, il_util, all_util, inq_fi, inq_last_12m … |
| ไม่เคยถึง 50% | 19 | joint/sec_app fields, mths_since_last_major_derog, mths_since_recent_bc_dlq |

→ ผลต่อการออกแบบ: model ที่ train บน vintage เก่าต้องใช้ feature set ที่มีครบใน train window; ถ้า train 2012–14
จะใช้ได้ ~43–66 APP features; ห้ามเติม missing แบบที่ "missing = vintage เก่า" กลายเป็นสัญญาณเวลา

## 3. Matured-vintage check (step 3)

ดู `reports/figures/p0_matured_share.png`. pct_final = Fully Paid หรือ Charged Off (รวม variant "does not meet policy")

| issue year | 36m n | 36m % final | 36m bad among final | 60m n | 60m % final | 60m bad among final |
|---|---:|---:|---:|---:|---:|---:|
| 2007 | 603 | 100 | 26.2 | – | – | – |
| 2008 | 2,393 | 100 | 20.7 | – | – | – |
| 2009 | 5,281 | 100 | 13.7 | – | – | – |
| 2010 | 9,156 | 100 | 10.9 | 3,381 | 100 | 22.4 |
| 2011 | 14,101 | 100 | 10.6 | 7,620 | 100 | 23.6 |
| 2012 | 43,470 | 100 | 13.6 | 9,897 | 100 | 27.7 |
| 2013 | 100,422 | 100 | 12.3 | 34,392 | 100 | 25.1 |
| 2014 | 162,570 | 100 | 13.7 | 73,059 | 82.9 | (31.1 biased) |
| 2015 | 283,173 | 99.9 | 14.9 | 137,922 | 67.1 | (36.4 biased) |
| 2016 | 323,495 | 71.8 | (19.8 biased) | 110,912 | 54.8 | biased |
| 2017 | 320,419 | 40.1 | biased | 123,160 | 33.1 | biased |
| 2018 | 344,671 | 12.0 | biased | 150,571 | 10.0 | biased |

ตัวอย่าง survivorship bias: 36m issue 2016-Q1 resolved 93% → bad among final 16.1%; 2016-Q2 resolved 68% → 22.4%
(loan ที่จบเร็วคือ default เร็ว + prepay เร็ว → bad rate ใน resolved subset สูงเกินจริง)

**การตัดสินใจ (เสนอ):**
- **Headline default label = 36m loans issued 2007-06 ถึง 2015-12** (621,169 loans ก่อนตัด policy exclusions, resolved ≥ 99.8%) — bad = Charged Off
  (+ Default 1 ราย) vs Fully Paid; ตัด 'does not meet credit policy' ออก (sensitivity แยก)
- 60m: ใช้ได้ถึง 2013 เท่านั้น (55,290 loans) → ไม่รวมใน headline scorecard; ใช้ใน survival model (A) ซึ่งรองรับ censoring
- 2016–2018: **ไม่ใช้เป็น label แบบ binary** — ใช้สำหรับ monitoring (PSI/CSI, early-MOB indicators) และ survival (censored)
- หมายเหตุ: bad rate 36m ไต่ขึ้นจาก 10.6% (2011) → 14.9% (2015) และ 2016 น่าจะสูงกว่าอีก → นี่คือ "drift" ที่ใช้เล่าเรื่องได้

## 4. Leakage map (step 4)

ตารางเต็มต่อ column: `reports/audit/column_catalogue.md`; โค้ด: `src/audit/leakage_map.py`

| class | n | ความหมาย |
|---|---:|---|
| APP | 99 | รู้ ณ วันสมัคร (borrower-stated + bureau pull ตอนสมัคร) → ใช้ได้ |
| LC | 9 | ผลการตัดสินใจ / pricing ของ LC: int_rate, installment, grade, sub_grade, funded_amnt, funded_amnt_inv, initial_list_status, policy_code, disbursement_method → **ไม่ใช้เป็น feature** (จะเท่ากับลอก model ของ LC); ใช้เป็น benchmark/policy variable |
| POST | 38 | หลังปล่อยกู้: payments, out_prncp, recoveries, last_pymnt_d, next_pymnt_d, last_credit_pull_d, last_fico_range_*, pymnt_plan, hardship_* (15), settlement/debt_settlement (7) → **leak** |
| ID / TIME / TARGET | 3 / 1 / 1 | id, member_id, url / issue_d / loan_status |

กับดักที่ต้องจำ:
- `last_fico_range_*` ดูเหมือน FICO แต่เป็นค่า refresh หลังปล่อยกู้ → leak รุนแรง
- `next_pymnt_d` missing pattern (59.5% null) = loan ปิดแล้ว → บอก status ได้ทันที
- `hardship_flag`, `debt_settlement_flag` ไม่ null (เป็น N/Y) แต่เป็นข้อมูลหลังเกิดปัญหา
- `funded_amnt_inv` รู้หลัง listing (investor funding) → mild leak
- `disbursement_method` = "Cash" ย้อนหลังทุกปี, DirectPay เริ่ม 2018 → ไม่มีข้อมูล แต่เป็น time signal
- `title` / `emp_title` / `desc` เป็น free text อาจมี PII → ห้าม publish ตัวอย่างข้อความ

## 5. Rejected file (step 5) → feasibility ของ item 8

| item | value |
|---|---|
| rows | **27,648,741** |
| columns (9) | Amount Requested, Application Date, Loan Title, Risk_Score, Debt-To-Income Ratio, Zip Code, State, Employment Length, Policy Code |
| Application Date | 2007-05-26 → 2018-12-31 |
| Risk_Score | **FICO ก่อน 2013-11-05, VantageScore หลังจากนั้น** (ตาม dictionary) — scale ต่างกัน, max 990 หลัง 2013 |
| Risk_Score null | pre-2013-11: 2.5% (+6.3% เป็น 0); post: 70.3% null (2015: 82%, 2018: 93%) |
| Employment Length | 83% = "< 1 year" → น่าจะเป็นค่า default/placeholder ใช้ไม่ได้ |
| Policy Code | 0 = 99.7%, 2 = 88k (ไม่ตรงกับ coding 1/2 ของ accepted) |
| acceptance proxy | accepted / (accepted + rejected) = 5–15% ต่อปี (rejected รวม application ที่ไม่สมบูรณ์ / auto-decline จึงไม่ใช่ approval rate จริง) |

Overlap กับ accepted: amount↔loan_amnt, Risk_Score↔fico_range_low (**เฉพาะก่อน 2013-11-05**), DTI↔dti, Zip(3)↔zip_code,
State↔addr_state, Loan Title↔title (free text, 74k distinct), Employment Length↔emp_length (ใช้ไม่ได้จริง)
**ไม่มีใน rejected:** annual_inc, home_ownership, term, purpose (category), verification, bureau attributes ทั้งหมด

ขนาดตัวอย่างที่ใช้ได้: rejects ก่อน 2013-11-05 ที่มี FICO 300–850 และ DTI 0–100 = **1.25M**;
ในนี้ FICO ≥ 660 และ DTI ≤ 40 ("near-miss" ที่อยู่ใน credit box) = 418k (accepted ช่วงเดียวกัน ≈ 230k)

**Verdict item 8: feasible แบบจำกัด** — ทำได้เฉพาะ reduced scorecard ~4–5 features (FICO, DTI, amount, state/zip3)
บน window 2007–2013-10; ไม่มี ground truth ของ rejects (ทุก method = extrapolation); rejects ส่วนใหญ่ FICO < 660
(ต่ำกว่า policy floor ที่ไม่เคยมี accepted ให้เรียนรู้). คุณค่าต่อ portfolio = ปานกลาง-ต่ำ → แนะนำ skip หรือทำเป็น
appendix สั้น (parcelling/fuzzy augmentation บน reduced model + บอกข้อจำกัดตรง ๆ)

## 6. Feasibility ของ G — causal effect of rate on default (step 6, evidence only)

ตาราง: `audit_tables.md` หัวข้อ G1–G4, `fico_rate_profile.md`, figure `p0_rate_by_fico.png`

- **G1 FICO floor:** ตั้งแต่ 2009 min fico_range_low = 660 ทุกปี (2007: 27% < 660, 2008: 14%). → 660 เป็น sharp
  **acceptance** cutoff แต่ใต้ 660 ไม่มี outcome (ถูก reject) → ใช้ศึกษา rate→default ไม่ได้
- **FICO resolution:** fico_range_low เป็น bin 5 แต้ม (range_high = low + 4) → running variable หยาบ
- **G3 grade ไม่ใช่ deterministic function ของ FICO:** within issue-month R² ของ int_rate:
  sub_grade 0.995–0.998 (rate = f(sub_grade, date) เกือบ 100%) แต่ FICO bin แค่ 0.66 (2007–09), 0.53 (2010–12), 0.17 (2013–18).
  ใน FICO bin เดียวกัน (bins n ≥ 200) มีแค่ 7–35% ที่ได้ sub_grade เดียวกับ modal sub_grade ของ bin
- **G2 jumps:** mean int_rate ระหว่าง FICO bin ติดกันเปลี่ยนแบบ median 0.22–0.36 pp; jump ใหญ่สุด 0.8–0.96 pp
  (2010–12 ที่ 670/675, 700, 715; 2016–18 ที่ 720) → อาจเป็น fuzzy threshold ใน grading ช่วงแรก แต่ไม่ sharp
- **G4 repricing events (ทางเลือกที่ดีกว่า):** LC ปรับ rate ของ sub_grade เดิมเป็นครั้งคราว — 3–8 เดือนต่อปีที่มี repricing (2008–2018),
  31–140 subgrade-month changes ต่อปี, |Δrate| เฉลี่ย 0.24–0.80 pp → borrowers ความเสี่ยงเท่ากัน (sub_grade เดียวกัน)
  ได้ rate ต่างกันตาม issue date → design แบบ event study / difference-in-discontinuities in time

**Verdict G: ไม่มี sharp RD.** ทางที่เป็นไปได้คือ repricing event study แต่ (1) Δrate เล็ก (~0.5 pp) → effect ต่อ default
น่าจะเล็กมาก (power ต่ำ ต่อ event; ต้อง pool หลาย events), (2) repricing มักมาพร้อม policy/marketing change และ
selection ว่าใครรับ offer → identification อ่อน. แนะนำ **ไม่ทำเป็น senior item**; ถ้าอยากทำ ให้เป็น exploratory appendix

## 7. Text — desc (step 7) → feasibility ของ item 6

ดู `p0_desc_share.png`

| year | % desc non-empty | median chars | % ≥ 100 chars | % emp_title |
|---|---:|---:|---:|---:|
| 2007 | 97.5 | 152 | 59 | 91 |
| 2008 | 100 | 196 | 68 | 96 |
| 2009 | 95.2 | 289 | 75 | 94 |
| 2010 | 66.1 | 309 | 59 | 94 |
| 2011 | 58.6 | 229 | 50 | 93 |
| 2012 | 61.4 | 155 | 47 | 94 |
| 2013 | 36.1 | 103 | 24 | 94 |
| 2014 | 6.5 | 87 | 4 | 94 |
| 2015–2018 | 0 | – | 0 | 89–94 |

- desc หยุดหลัง **2014-03** (2014-03: 25%, 2014-04: 0.3%, หลังจากนั้น 0)
- ทั้งหมด 125,814 loans มี desc (90,044 ≥ 100 chars), resolved 125,703, bads 19,576
- univariate: มี/ไม่มี desc แทบไม่ต่างใน bad rate (36m: 2012 13.5 vs 13.7, 2013 11.8 vs 12.6)
- emp_title มี 89–96% ทุกปี (412k distinct values) — เหมาะกับ LLM normalisation/embedding มากกว่า และใช้ได้ทุก vintage

**Verdict item 6: feasible เป็น side study เท่านั้น** — "text เพิ่ม lift เหนือ structured features ไหม" บน 36m 2009–2013
(~83k resolved loans มี desc) ได้; แต่ใช้ใน production scorecard ไม่ได้เพราะ feature หายไปหลัง 2014-03.
ถ้าอยากโชว์ LLM ใน project แนะนำ emp_title (normalise อาชีพ → industry/seniority) แทน. ห้าม publish ข้อความ desc (PII)

## 8. Evidence สำหรับ senior items A–D

**A — survival / lifetime PD + prepayment competing risk** (resolved loans 2009–2015)

| term | outcome | n | median months to last payment | % resolved > 3m ก่อนครบกำหนด |
|---|---|---:|---:|---:|
| 36m | charged off | 85,950 | 16 | 95.0 |
| 36m | fully paid | 532,076 | 29 | **57.3** (= prepayment) |
| 60m | charged off | 66,459 | 19 | 99.7 |
| 60m | fully paid | 141,872 | 27 | **90.9** |

- event time ระดับเดือน derive ได้จาก issue_d + last_pymnt_d (charge-off ≈ 4–5 เดือนหลัง last payment);
  ไม่มี monthly payment panel → event time เป็น approximation (ต้องบอกใน write-up)
- prepayment ใหญ่มาก → ถ้าไม่ treat เป็น competing risk lifetime PD จะเพี้ยน
- Current loans 878k (เกือบทั้งหมด issue 2014–2018) = right-censored ที่ as-of 2019-03 → survival ใช้ข้อมูลทั้งหมดได้ ไม่ต้องทิ้ง vintage ใหม่
- **Feasibility: สูง**

**B — macro-linked PD + baseline/adverse stress test**
- กระจาย 50 states, 897–914 zip3 ต่อปี (2015+); state ใหญ่สุด CA 13–19% → มี cross-sectional variation สำหรับ
  state unemployment (BLS LAUS, public domain — ยังไม่ดาวน์โหลด)
- crisis signal: bad rate ต่อ grade ของ vintage 2007–08 vs 36m 2010–11: A 5.8 vs 5.8, B 17.2 vs 10.2, C 21.6 vs 14.6,
  D 27.4 vs 18.3, F 38.7 vs 27.6 → ประมาณ 1.5× ใน grade B–F แต่ n แค่ ~3k
- ข้อจำกัด: มี downturn เดียว (2008–09) และ LC ปล่อยกู้น้อยมากตอนนั้น; national trend confound กับ policy change ของ LC
  (credit box ขยาย 2012–15, เหตุการณ์ปี 2016) → ต้องอาศัย state × time variation และรายงาน uncertainty
- **Feasibility: ปานกลาง** (ทำได้, แต่ macro coefficient จะมี interval กว้าง — เป็นเรื่องที่ต้องพูดตรง ๆ ซึ่งก็ดีสำหรับ portfolio)

**C — profit-optimal policy (LP/IP)**
- มี cash-flow ครบ: total_pymnt, total_rec_prncp, total_rec_int, recoveries, collection_recovery_fee, funded_amnt
- resolved 2009–2015: charged off จ่ายคืนรวม 0.62× ของ funded, recoveries 0.079×, approx LGD (principal) ≈ 0.58; fully paid 1.18×
- **Feasibility: สูง** (ข้อมูลพร้อม; งานเป็น optimisation มากกว่า data)

**D — reason codes + monotonic constraints**
- grade → bad rate monotone ชัด (36m 2010–15: A 5.5%, B 11.2, C 17.9, D 23.4, E 28.7, F 33.0, G 39.8)
- ไม่ต้องการข้อมูลพิเศษ; LightGBM monotone_constraints + WoE scorecard ให้ reason codes อยู่แล้ว
- **Feasibility: สูง, novelty ต่ำ** → ทำเป็นส่วนหนึ่งของ Phase 1 scorecard ได้ในราคาถูก

## 9. Recommendation

**Senior items: A + B** — เหตุผล
1. ตรงกับงานจริงของ credit risk ในธนาคารไทย: TFRS 9 (IFRS 9) ECL = lifetime PD (A) × forward-looking macro scenarios (B) × LGD
   (มี LGD proxy จาก recoveries อยู่แล้ว) → เล่าเป็นเรื่องเดียว "lifetime ECL under baseline vs adverse"
2. A แก้ปัญหา right-censoring ของข้อมูลนี้ได้ตรง ๆ (ใช้ 2016–2018 ได้) และ prepayment 57–91% ทำให้ competing risk สำคัญจริง
3. B ใช้ 2007–08 เป็น "crisis anchor" ได้พอดี — ทำให้คำถาม 2008 ยังอยู่ในเรื่อง แม้ข้อมูลจะน้อยเกินสำหรับ OOT test
- D: ใส่ monotone constraints + reason codes ใน Phase 1 (ราคาถูก ไม่นับเป็น senior item)
- C: stretch goal ถ้าเวลาเหลือ (ข้อมูลพร้อม)
- Plan B: ถ้า macro signal ใน B อ่อนเกินไปหลังลอง state-level → เปลี่ยนเป็น A + C

**Optional items:** 6 = side study ได้ (ช่วง 2009–2013, หรือใช้ emp_title แทน); 8 = feasible แบบจำกัด, แนะนำ skip/appendix;
G = ไม่มี sharp cutoff, แนะนำ skip (หรือ repricing event study เป็น exploratory)

**ข้อเสนอปรับ story (ต้องให้ Nat ตัดสินใจ):**
"If you were a lender in 2014, would your model survive the 2015–16 vintages — and would you notice in time?"
- train: 36m issued 2012–2013 (~144k) / validation 2014 (163k) / OOT test 2015 (283k, matured) — time-based ทั้งหมด
- monitoring/backtest: 2016–2018 (PSI/CSI, KS ตาม vintage, early-MOB charge-off curves) → "notice in time?"
- 2007–08: crisis anchor สำหรับ adverse scenario ใน B + กราฟ vintage

## 10. สิ่งที่ล้มเหลว / ข้อจำกัดที่เจอ (report what failed)
- LC data dictionary: หน้า LC เดิมปิดแล้ว, Kaggle wendykan dataset ตอบ 403 → ใช้ Figshare copy (CC BY 4.0) แทน
- Kaggle download ช้า (~0.1–1.2 MB/s; รวม ~27 นาที) — ไม่มีผลต่อข้อมูล (ขนาดไฟล์ตรงกับ listing, มี sha256)
- Bug ใน audit script ที่เจอและแก้แล้ว: `desc` เป็น SQL keyword; `avg()` ข้าม NULL ทำให้ % desc ช่วงแรกสูงเกินจริง
  (แก้ด้วย coalesce) — ตัวเลขในเอกสารนี้เป็นของ version ที่แก้แล้ว
- ไม่มี monthly payment history → event time ใน A และ vintage curves เป็น approximation จาก last_pymnt_d
- Application date ของ accepted ไม่มี (มีแต่ issue_d = เดือนที่ fund) → เทียบเวลากับ rejected (Application Date) ได้ระดับเดือนโดยประมาณ
