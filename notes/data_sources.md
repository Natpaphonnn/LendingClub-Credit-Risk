# Data sources

All raw / row-level files live only in `data/raw/` and `data/interim/` (git-ignored). Never commit or upload them.

## 1. Primary — "All Lending Club loan data" (Kaggle)

| Field | Value |
|---|---|
| URL | https://www.kaggle.com/datasets/wordsforthewise/lending-club |
| Title / owner | "All Lending Club loan data" — wordsforthewise (Nathan George) |
| License (verified 2026-11-19 via `kaggle datasets metadata`) | `CC0-1.0` (as tagged by the uploader) |
| Original source | LendingClub public loan data (LoanStats / RejectStats downloads, 2007–2018Q4) |
| Credit line | "Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise)" |
| Download method | Kaggle CLI 2.2.4: `kaggle datasets download wordsforthewise/lending-club -f <file> -p data/raw` |
| Downloaded | 2026-11-19, 13:09–13:36 UTC (sizes match the Kaggle file listing) |

| File | Bytes | sha256 |
|---|---|---|
| accepted_2007_to_2018Q4.csv.gz | 392,582,231 | 55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d |
| rejected_2007_to_2018Q4.csv.gz | 255,470,782 | c1f9f2a4ec5537ef0af44b24b2fb2f41f58fcaec45363ef32c6a2fb27347f6c5 |

The dataset also contains uncompressed copies (`accepted_2007_to_2018q4.csv/…`, `rejected_2007_to_2018q4.csv/…`) (per the listing, presumably the same files uncompressed — not verified, not downloaded).

**License caveat (record, not a blocker).** The uploader's description says LendingClub later added a terms-of-service popup to its download page and that "worst case, they will ask me/Kaggle to take it down". The CC0 tag is the uploader's claim; LendingClub's own terms may restrict redistribution. Our rule stays: publish only code, aggregates, figures and model results — never rows. The uploader also notes he removed `%` from `int_rate` and `revol_util` and converted them to floats.

## 2. Data dictionary — LCDataDictionary.xlsx (Figshare copy)

| Field | Value |
|---|---|
| URL | https://figshare.com/articles/dataset/Lending_club_dataset_description/20016077 (file: https://ndownloader.figshare.com/files/35685971) |
| DOI | 10.6084/m9.figshare.20016077.v1 |
| License | CC BY 4.0 (from Figshare API) — cite the DOI if dictionary text is quoted |
| File | data/raw/dictionary/LCDataDictionary.xlsx, 23,582 bytes, sha256 d39e281c1130c8abadce87250d97d363297e6c5c891fac6f721f076469e7a4bf (md5 matches Figshare's 690c70b9…) |
| Downloaded | 2026-11-19 |
| Why this copy | The Kaggle dataset doesn't include the dictionary. Its description points to the LendingClub download page, which is gone. The other Kaggle copy (wendykan/lending-club-loan-data) returns 403. Sheets: LoanStats (153 rows), browseNotes (122), RejectStats (9). All 151 accepted-file columns are found in it. |

## 3. Backup — LC loans granting model dataset (Zenodo) — not downloaded

| URL | License | Status |
|---|---|---|
| https://zenodo.org/records/11295916 (doi:10.5281/zenodo.11295916) | CC BY 4.0 | Not needed so far. Cite it if it is ever used. |

## 4. Planned external data (not yet downloaded)

| Dataset | Source | License | Use |
|---|---|---|---|
| State & national unemployment rate (LAUS / UNRATE) | BLS via FRED | US public domain (BLS); FRED series terms to be checked when downloaded | Item B (macro-linked PD / stress test) |

## Derived local files (git-ignored, not for upload)

| File | Rows | Size | Note |
|---|---:|---:|---|
| data/interim/accepted_2007_to_2018Q4.parquet | 2,260,701 (incl. 33 footer rows) | 277 MB | all columns VARCHAR, zstd |
| data/interim/rejected_2007_to_2018Q4.parquet | 27,648,741 | 168 MB | all columns VARCHAR, zstd |
