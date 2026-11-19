# STATUS — 2026-11-19

## Done — Phase 0 (data audit) ✅
- ดาวน์โหลด Kaggle "All Lending Club loan data" (accepted + rejected .csv.gz) → data/raw/; license CC0-1.0 ตรวจจาก Kaggle API;
  sha256 / ขนาด / วันที่ บันทึกใน notes/data_sources.md. Data dictionary: Figshare copy (CC BY 4.0)
- แปลงเป็น parquet ใน data/interim/ (DuckDB, all-VARCHAR); venv: `.venv` (Python 3.12, requirements.txt)
- Audit ขั้น 2–7 → **notes/01_data_audit.md** (+ reports/audit/*.md, reports/figures/p0_*.png); code: src/audit/
- git init แบบ local (ไม่มี remote); data files ไม่อยู่ใน git

## Key results
- 2,260,668 accepted loans (2007-06 → 2018-12, as-of ≈ 2019-03); 27.6M rejected applications
- 2007 = 603 loans, 2008 = 2,393 → **ใช้ 2007→2008 เป็น headline OOT test ไม่ได้**
- Matured: 36m ถึง issue 2015-12 (621k loans), 60m ถึง 2013; 2016–2018 ใช้สำหรับ monitoring / survival
- Leakage map: 99 APP / 9 LC-decision / 38 POST columns
- Recommendation: senior items **A + B** (TFRS 9 lifetime ECL story); D ใส่ใน Phase 1; C stretch.
  6 = side study only (desc หายหลัง 2014-03); 8 = limited (skip/appendix); G = no sharp cutoff (skip)

## Open questions for Nat
1. ยอมรับการปรับ story ไหม: "lender ปี 2014 → model รอด vintage 2015–16 ไหม และ monitoring จับได้ทันไหม",
   โดยให้ 2007–08 เป็น crisis anchor ของ stress test (ดู 01_data_audit.md §9)
2. เลือก senior items 2 ตัว (แนะนำ A + B)
3. Exclude loans 'does not meet the credit policy' (2,749 loans, 2007–2010) จาก headline model — ok ไหม?
4. ทำ item 6 / 8 / G ไหม (แนะนำ: 6 แบบ side study ด้วย emp_title หรือ desc 2009–13; skip 8 และ G)

## Next step
- Phase 1 pre-registration (notes/02_prereg_scorecard.md): split, bad definition, feature list (APP only), metrics + intervals
  — รอ Nat ตอบ open questions ก่อน
