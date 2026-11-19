# E1 — Confirmatory MOB-6 A/E test on 60-month loans (pre-registered, commit 4562602, pushed before this ran)

Reference window 60m issued 2012-09..2013-12: n = 38,929, MOB-12 default rate 5.75%, r6 (M2) = 0.1219, r6 (M1) = 0.1256. Thresholds amber > 1.10, red > 1.25; truth = MOB-12 rate ≥ 1.2 × reference. Criterion: sensitivity ≥ 0.80 and specificity ≥ 0.80 with ≥ 3 quarters per class (else INCONCLUSIVE). Lead time is 6 months by construction.

## Result

| score          | truth YES / no quarters   | sensitivity                 | specificity               | verdict   | first MOB-6 flag (knowable)   | first truth YES (knowable)   |
|:---------------|:--------------------------|:----------------------------|:--------------------------|:----------|:------------------------------|:-----------------------------|
| M2 (primary)   | 9 / 6                     | 9/9 = 100% (95% CI 66–100%) | 4/6 = 67% (95% CI 22–96%) | **FAIL**  | 2015Q1 (2016-03)              | 2015Q3 (2017-03)             |
| M1 (secondary) | 9 / 6                     | 9/9 = 100% (95% CI 66–100%) | 4/6 = 67% (95% CI 22–96%) | **FAIL**  | 2015Q1 (2016-03)              | 2015Q3 (2017-03)             |

## By issue quarter (2014Q1–2017Q3)

| issue_q   |     n |   MOB6 default % |   A/E6 M2 | flag M2   |   A/E6 M1 | flag M1   |   MOB12 × ref | truth   | MOB6 knowable   | truth knowable   |
|:----------|------:|-----------------:|----------:|:----------|----------:|:----------|--------------:|:--------|:----------------|:-----------------|
| 2014Q1    | 13336 |            1.552 |     0.908 | green     |     0.92  | green     |         0.899 | no      | 2015-03         | 2015-09          |
| 2014Q2    | 17468 |            1.78  |     1.036 | green     |     1.057 | green     |         1.017 | no      | 2015-06         | 2015-12          |
| 2014Q3    | 18131 |            1.881 |     1.076 | green     |     1.09  | green     |         1.104 | no      | 2015-09         | 2016-03          |
| 2014Q4    | 24124 |            1.513 |     0.85  | green     |     0.863 | green     |         0.997 | no      | 2015-12         | 2016-06          |
| 2015Q1    | 27708 |            2.036 |     1.143 | AMBER     |     1.163 | AMBER     |         1.14  | no      | 2016-03         | 2016-09          |
| 2015Q2    | 31603 |            2.092 |     1.176 | AMBER     |     1.204 | AMBER     |         1.133 | no      | 2016-06         | 2016-12          |
| 2015Q3    | 36917 |            2.059 |     1.171 | AMBER     |     1.193 | AMBER     |         1.239 | YES     | 2016-09         | 2017-03          |
| 2015Q4    | 41422 |            2.088 |     1.189 | AMBER     |     1.221 | AMBER     |         1.303 | YES     | 2016-12         | 2017-06          |
| 2016Q1    | 36634 |            2.342 |     1.391 | RED       |     1.426 | RED       |         1.332 | YES     | 2017-03         | 2017-09          |
| 2016Q2    | 22713 |            2.672 |     1.661 | RED       |     1.689 | RED       |         1.348 | YES     | 2017-06         | 2017-12          |
| 2016Q3    | 25024 |            2.402 |     1.468 | RED       |     1.49  | RED       |         1.426 | YES     | 2017-09         | 2018-03          |
| 2016Q4    | 22970 |            2.168 |     1.415 | RED       |     1.443 | RED       |         1.286 | YES     | 2017-12         | 2018-06          |
| 2017Q1    | 22594 |            2.328 |     1.592 | RED       |     1.603 | RED       |         1.224 | YES     | 2018-03         | 2018-09          |
| 2017Q2    | 25258 |            2.502 |     1.718 | RED       |     1.732 | RED       |         1.209 | YES     | 2018-06         | 2018-12          |
| 2017Q3    | 28179 |            2.733 |     1.833 | RED       |     1.867 | RED       |         1.348 | YES     | 2018-09         | 2019-03          |
