# E2 — As-of model (decision date 2014-12-31; pre-registered, commit 4562602)

Train 2012-09..2013-03 (n = 38,249, bad12 4.14%), validation 2013-04..2013-06
(n = 23,136, bad12 3.99%). Every bad12 event used in fitting occurred by 2014-06 (asserted).
Selected config {'num_leaves': 31, 'min_child_samples': 1000, 'lambda_l2': 10} (validation log loss 0.15807).

## OOT 2015 — ranking and calibration (95% bootstrap CI, B = 500)

| model | Gini vs final 36m bad | KS vs final | Gini vs bad12 | mean PD12 % | observed bad12 % | CITL12 (pp) |
|---|---|---|---|---:|---:|---|
| **As-of model (bad12, data to 2014-06)** | 33.0 [32.5, 33.5] | 23.9 [23.5, 24.4] | 37.4 [36.4, 38.2] | 4.24 | 4.66 | -0.42 [-0.51, -0.35] |
| Reference M2 (full 36m labels, 2012-09..2013-12) | 36.7 [36.2, 37.3] | 26.5 [26.1, 27.1] | 38.7 [37.7, 39.5] | – | – | – |

Paired ΔGini (as-of − reference) on final outcome: -3.76 [-4.05, -3.46].

## Realistic monitoring — what a lender with this model would have seen

A/E12 = Σ bad12 / Σ PD12 (no scaling); knowable at quarter end + 18 months. First amber: {'issue_q': '2015Q4', 'knowable': '2017-06'}; first red: {'issue_q': '2016Q1', 'knowable': '2017-09'}.

| issue_q   |     n |   mean PD12 % |   PSI | PSI flag   |   bad12 % |   A/E12 | A/E flag   | knowable   |
|:----------|------:|--------------:|------:|:-----------|----------:|--------:|:-----------|:-----------|
| 2015Q1    | 56569 |         4.306 | 0.007 | green      |     4.396 |   1.021 | green      | 2016-09    |
| 2015Q2    | 64222 |         4.297 | 0.005 | green      |     4.696 |   1.093 | green      | 2016-12    |
| 2015Q3    | 73572 |         4.174 | 0.003 | green      |     4.562 |   1.093 | green      | 2017-03    |
| 2015Q4    | 88571 |         4.223 | 0.003 | green      |     4.899 |   1.16  | AMBER      | 2017-06    |
| 2016Q1    | 94592 |         4.119 | 0.003 | green      |     5.364 |   1.302 | RED        | 2017-09    |
| 2016Q2    | 73666 |         4.174 | 0.006 | green      |     5.758 |   1.38  | RED        | 2017-12    |
| 2016Q3    | 73579 |         4.272 | 0.015 | green      |     5.979 |   1.399 | RED        | 2018-03    |
| 2016Q4    | 76440 |         4.045 | 0.007 | green      |     5.608 |   1.387 | RED        | 2018-06    |
| 2017Q1    | 69778 |         3.774 | 0.013 | green      |     4.979 |   1.319 | RED        | 2018-09    |
| 2017Q2    | 73380 |         3.793 | 0.012 | green      |     5.343 |   1.409 | RED        | 2018-12    |
| 2017Q3    | 80528 |         3.868 | 0.008 | green      |     5.274 |   1.364 | RED        | 2019-03    |
| 2017Q4    | 72798 |         3.634 | 0.024 | green      |   nan     | nan     | nan        | nan        |
| 2018Q1    | 65848 |         3.531 | 0.039 | green      |   nan     | nan     | nan        | nan        |
| 2018Q2    | 81015 |         3.579 | 0.031 | green      |   nan     | nan     | nan        | nan        |
| 2018Q3    | 79093 |         3.295 | 0.075 | green      |   nan     | nan     | nan        | nan        |
| 2018Q4    | 78336 |         3.302 | 0.073 | green      |   nan     | nan     | nan        | nan        |

## Grid (selection by validation log loss on bad12)

|   num_leaves |   min_child_samples |   lambda_l2 |   best_iter |   valid_logloss_bad12 |
|-------------:|--------------------:|------------:|------------:|----------------------:|
|           31 |                1000 |          10 |         150 |               0.15807 |
|           63 |                1000 |          10 |         150 |               0.15807 |
|           15 |                1000 |          10 |         180 |               0.1581  |
|           15 |                1000 |           0 |         121 |               0.15811 |
|           31 |                1000 |           0 |         119 |               0.15817 |
|           63 |                1000 |           0 |         119 |               0.15817 |
|           15 |                 200 |          10 |         140 |               0.15823 |
|           63 |                 200 |          10 |         115 |               0.15824 |
|           63 |                 200 |           0 |          89 |               0.15835 |
|           31 |                 200 |          10 |         128 |               0.1584  |
|           31 |                 200 |           0 |          88 |               0.15864 |
|           15 |                 200 |           0 |         108 |               0.15877 |
