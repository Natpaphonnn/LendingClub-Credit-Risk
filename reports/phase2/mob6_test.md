# MOB-6 A/E — out-of-discovery test (2016Q1–2017Q4)

**Label: signal discovered on 2015 vintages (Phase 1 exploratory); thresholds pre-registered in notes/03_prereg_phase2.md (commit 1203ada) before this run; evaluated only on 2016–2017 vintages.**

r6 (train MOB-6 defaults / final bads) = 0.0983; train MOB-12 default rate = 3.86%. Thresholds: A/E6 > 1.10 AMBER, > 1.25 RED.

## Summary

| model   |   quarters with truth |   truth YES | sensitivity (amber+)   | useful (≥80%)?   |   truth no | specificity                                |   median lead (months) |
|:--------|----------------------:|------------:|:-----------------------|:-----------------|-----------:|:-------------------------------------------|-----------------------:|
| M1      |                     7 |           7 | 7/7 = 100%             | YES              |          0 | not testable (no non-deteriorated quarter) |                      6 |
| M2      |                     7 |           7 | 7/7 = 100%             | YES              |          0 | not testable (no non-deteriorated quarter) |                      6 |

## By quarter

| issue_q   |     n |   MOB6 default % |   A/E6 M1 | flag M1   |   A/E6 M2 | flag M2   | MOB6 known   |   MOB12 ×train | truth (≥1.2×)   | MOB12 known   |   lead (months) |
|:----------|------:|-----------------:|----------:|:----------|----------:|:----------|:-------------|---------------:|:----------------|:--------------|----------------:|
| 2016Q1    | 94592 |            1.716 |     1.404 | RED       |     1.358 | RED       | 2017-03      |           1.39 | YES             | 2017-09       |               6 |
| 2016Q2    | 73666 |            2.038 |     1.662 | RED       |     1.605 | RED       | 2017-06      |           1.49 | YES             | 2017-12       |               6 |
| 2016Q3    | 73579 |            1.937 |     1.553 | RED       |     1.502 | RED       | 2017-09      |           1.55 | YES             | 2018-03       |               6 |
| 2016Q4    | 76440 |            1.739 |     1.463 | RED       |     1.42  | RED       | 2017-12      |           1.45 | YES             | 2018-06       |               6 |
| 2017Q1    | 69778 |            1.652 |     1.444 | RED       |     1.415 | RED       | 2018-03      |           1.29 | YES             | 2018-09       |               6 |
| 2017Q2    | 73380 |            2.08  |     1.822 | RED       |     1.79  | RED       | 2018-06      |           1.38 | YES             | 2018-12       |               6 |
| 2017Q3    | 80528 |            1.83  |     1.596 | RED       |     1.557 | RED       | 2018-09      |           1.37 | YES             | 2019-03       |               6 |
| 2017Q4    | 72798 |            1.74  |     1.63  | RED       |     1.581 | RED       | 2018-12      |         nan    | not observable  | nan           |             nan |
