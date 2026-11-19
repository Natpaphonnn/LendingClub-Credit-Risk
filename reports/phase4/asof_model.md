# E2 — As-of model (decision date 2014-12-31; pre-registered, commit 4562602)

Train 2012-09..2013-03 (n = 38,249, bad12 4.14%), validation 2013-04..2013-06
(n = 23,136, bad12 3.99%). Every bad12 event used in fitting occurred by 2014-06 (asserted).
Selected config {'num_leaves': 15, 'min_child_samples': 1000, 'lambda_l2': 0} (validation log loss 0.15794).

## OOT 2015 — ranking and calibration (95% bootstrap CI, B = 500)

| model | Gini vs final 36m bad | KS vs final | Gini vs bad12 | mean PD12 % | observed bad12 % | CITL12 (pp) |
|---|---|---|---|---:|---:|---|
| **As-of model (bad12, data to 2014-06)** | 33.1 [32.6, 33.7] | 24.0 [23.6, 24.6] | 37.4 [36.5, 38.3] | 4.28 | 4.66 | -0.39 [-0.47, -0.32] |
| Reference M2 (full 36m labels, 2012-09..2013-12) | 36.8 [36.3, 37.3] | 26.6 [26.1, 27.1] | 38.8 [37.8, 39.7] | – | – | – |

Paired ΔGini (as-of − reference) on final outcome: -3.65 [-3.95, -3.37].

## Realistic monitoring — what a lender with this model would have seen

A/E12 = Σ bad12 / Σ PD12 (no scaling); knowable at quarter end + 18 months. First amber: {'issue_q': '2015Q4', 'knowable': '2017-06'}; first red: {'issue_q': '2016Q1', 'knowable': '2017-09'}.

| issue_q   |     n |   mean PD12 % |   PSI | PSI flag   |   bad12 % |   A/E12 | A/E flag   | knowable   |
|:----------|------:|--------------:|------:|:-----------|----------:|--------:|:-----------|:-----------|
| 2015Q1    | 56569 |         4.341 | 0.006 | green      |     4.396 |   1.013 | green      | 2016-09    |
| 2015Q2    | 64222 |         4.327 | 0.006 | green      |     4.696 |   1.085 | green      | 2016-12    |
| 2015Q3    | 73572 |         4.211 | 0.003 | green      |     4.562 |   1.083 | green      | 2017-03    |
| 2015Q4    | 88571 |         4.255 | 0.004 | green      |     4.899 |   1.151 | AMBER      | 2017-06    |
| 2016Q1    | 94592 |         4.151 | 0.003 | green      |     5.364 |   1.292 | RED        | 2017-09    |
| 2016Q2    | 73666 |         4.211 | 0.005 | green      |     5.758 |   1.368 | RED        | 2017-12    |
| 2016Q3    | 73579 |         4.306 | 0.012 | green      |     5.979 |   1.389 | RED        | 2018-03    |
| 2016Q4    | 76440 |         4.079 | 0.004 | green      |     5.608 |   1.375 | RED        | 2018-06    |
| 2017Q1    | 69778 |         3.815 | 0.011 | green      |     4.979 |   1.305 | RED        | 2018-09    |
| 2017Q2    | 73380 |         3.841 | 0.01  | green      |     5.343 |   1.391 | RED        | 2018-12    |
| 2017Q3    | 80528 |         3.906 | 0.007 | green      |     5.274 |   1.35  | RED        | 2019-03    |
| 2017Q4    | 72798 |         3.665 | 0.026 | green      |   nan     | nan     | nan        | nan        |
| 2018Q1    | 65848 |         3.551 | 0.044 | green      |   nan     | nan     | nan        | nan        |
| 2018Q2    | 81015 |         3.604 | 0.034 | green      |   nan     | nan     | nan        | nan        |
| 2018Q3    | 79093 |         3.319 | 0.079 | green      |   nan     | nan     | nan        | nan        |
| 2018Q4    | 78336 |         3.332 | 0.076 | green      |   nan     | nan     | nan        | nan        |

## Grid (selection by validation log loss on bad12)

|   num_leaves |   min_child_samples |   lambda_l2 |   best_iter |   valid_logloss_bad12 |
|-------------:|--------------------:|------------:|------------:|----------------------:|
|           15 |                1000 |           0 |         126 |               0.15794 |
|           63 |                 200 |          10 |         125 |               0.15804 |
|           31 |                1000 |          10 |         150 |               0.15806 |
|           63 |                1000 |          10 |         150 |               0.15806 |
|           15 |                1000 |          10 |         152 |               0.15811 |
|           31 |                 200 |          10 |         138 |               0.15812 |
|           31 |                1000 |           0 |         121 |               0.15821 |
|           63 |                1000 |           0 |         121 |               0.15821 |
|           15 |                 200 |          10 |         143 |               0.15822 |
|           63 |                 200 |           0 |          88 |               0.15827 |
|           31 |                 200 |           0 |         108 |               0.15827 |
|           15 |                 200 |           0 |         113 |               0.15851 |
