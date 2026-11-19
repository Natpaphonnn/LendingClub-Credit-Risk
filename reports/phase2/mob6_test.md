# MOB-6 A/E — 2016Q1–2017Q4 (EXPLORATORY / DESCRIPTIVE — not a confirmatory test)

**Status (corrected after independent review, CR-1):** the thresholds were registered in notes/03_prereg_phase2.md (commit 1203ada), but the 2016–17 MOB-6 A/E values had already been computed and committed in reports/phase1/exploratory_early_signal.md (commit 5b35a6e) before that registration. This table is therefore descriptive, not an out-of-discovery test. Lead time is 6 months **by construction** (MOB-6 is knowable 6 months before MOB-12); the truth (MOB-12 rate) shares the same default events; every 2016–17 quarter is deteriorated, so any always-on alarm would also score 7/7. The A/E level also depends on how 'expected' is built: under the lifetime hazard model's own MOB shape, 2015 A/E6 is 0.91–1.09 (reports/phase2/overlay.md).

## Discovery-period confusion matrix (2014Q1–2015Q4; truth = MOB-12 ≥ 1.2× train)

| model   | period                    | sensitivity   | specificity   | missed quarters   |
|:--------|:--------------------------|:--------------|:--------------|:------------------|
| M1      | 2014Q1–2015Q4 (discovery) | 2/2           | 6/6           | none              |
| M2      | 2014Q1–2015Q4 (discovery) | 1/2           | 6/6           | 2015Q4            |

r6 (train MOB-6 defaults / final bads) = 0.0983; train MOB-12 default rate = 3.86%. Thresholds: A/E6 > 1.10 AMBER, > 1.25 RED.

## Summary 2016Q1–2017Q3 (descriptive)

| model   |   quarters with truth |   truth YES | sensitivity (amber+)   | ≥80% hit rate? (descriptive)   |   truth no | specificity                                |   median lead (months) |
|:--------|----------------------:|------------:|:-----------------------|:-------------------------------|-----------:|:-------------------------------------------|-----------------------:|
| M1      |                     7 |           7 | 7/7 = 100%             | YES                            |          0 | not testable (no non-deteriorated quarter) |                      6 |
| M2      |                     7 |           7 | 7/7 = 100%             | YES                            |          0 | not testable (no non-deteriorated quarter) |                      6 |

## By quarter (2016–17)

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

## Discovery period by quarter

| issue_q   |     n |   MOB6 default % |   A/E6 M1 | flag M1   |   A/E6 M2 | flag M2   | MOB6 known   |   MOB12 ×train | truth (≥1.2×)   | MOB12 known   |   lead (months) |
|:----------|------:|-----------------:|----------:|:----------|----------:|:----------|:-------------|---------------:|:----------------|:--------------|----------------:|
| 2014Q1    | 34074 |            1.13  |     0.9   | green     |     0.906 | green     | 2015-03      |           0.95 | no              | 2015-09       |               6 |
| 2014Q2    | 37881 |            1.304 |     1.04  | green     |     1.03  | green     | 2015-06      |           1.02 | no              | 2015-12       |               6 |
| 2014Q3    | 40595 |            1.237 |     0.977 | green     |     0.973 | green     | 2015-09      |           1.09 | no              | 2016-03       |               6 |
| 2014Q4    | 50020 |            1.289 |     0.968 | green     |     0.952 | green     | 2015-12      |           1.17 | no              | 2016-06       |               6 |
| 2015Q1    | 56569 |            1.315 |     1.005 | green     |     0.991 | green     | 2016-03      |           1.14 | no              | 2016-09       |               6 |
| 2015Q2    | 64222 |            1.559 |     1.205 | AMBER     |     1.184 | AMBER     | 2016-06      |           1.22 | YES             | 2016-12       |               6 |
| 2015Q3    | 73572 |            1.358 |     1.084 | green     |     1.065 | green     | 2016-09      |           1.18 | no              | 2017-03       |               6 |
| 2015Q4    | 88571 |            1.373 |     1.115 | AMBER     |     1.087 | green     | 2016-12      |           1.27 | YES             | 2017-06       |               6 |
