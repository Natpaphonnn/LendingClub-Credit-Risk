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

## 4. External data — BLS LAUS state unemployment (used in Phase 2 B)

| Field | Value |
|---|---|
| Dataset | Local Area Unemployment Statistics (LAUS), state unemployment rate, monthly, **seasonally adjusted** |
| Publisher | U.S. Bureau of Labor Statistics |
| Series | `LASST{FIPS}0000000000003` × 51 (50 states + DC), 2007-01 → 2018-12 (144 months each, 7,344 rows) |
| Access | BLS Public Data API v1 (no key), `src/phase2/fetch_bls.py`, 6 requests on 2026-11-19 ~15:00 UTC |
| License | **Public domain** — BLS copyright page (https://www.bls.gov/opub/copyright-information.htm): "everything that we publish … is in the public domain"; BLS asks to be cited → credit line: "Unemployment data: U.S. Bureau of Labor Statistics, LAUS" |
| Files | data/raw/macro/bls_laus_b{0,1,2}_{2007_2016,2017_2018}.json (raw API responses); tidy: data/interim/state_unemployment.parquet |
| Note | FRED (`{ST}UR`, the same BLS data) was tried first; fredgraph.csv timed out for scripted requests → used BLS directly (primary source). Values are the **current revised** LAUS series, not the real-time vintages a lender would have seen in 2015–16 (limitation) |

sha256 of raw responses:
```
17e444ebe1c560ff643e1f1e13e0fd51a092e1536b1fe63a39e412f60774a3fb  bls_laus_b0_2007_2016.json
5a19d91de5037db2be983d3a103992fe92c8088365df56d86492ada0eb0639f5  bls_laus_b0_2017_2018.json
6e0dd408ba3cf4ef54caf0ba30be3e2f5724bc1308fce3b807e3bf630f097ee2  bls_laus_b1_2007_2016.json
ea94ebc9c235f555b2920cfef141f8df20be5c0b66499c940f50a2c089b9266f  bls_laus_b1_2017_2018.json
1b19c85a7a094e7127bb8c6cd0a7e742a6548c760e93d176baee81a11dab93ec  bls_laus_b2_2007_2016.json
cd034186345fda83e4cf6c9d657ed15effbfc8bd5da7c7f7a2df50f3b2a1a71b  bls_laus_b2_2017_2018.json
```

## Derived local files (git-ignored, not for upload)

| File | Rows | Size | Note |
|---|---:|---:|---|
| data/interim/accepted_2007_to_2018Q4.parquet | 2,260,701 (incl. 33 footer rows) | 277 MB | all columns VARCHAR, zstd |
| data/interim/rejected_2007_to_2018Q4.parquet | 27,648,741 | 168 MB | all columns VARCHAR, zstd |
