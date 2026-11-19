# LightGBM grid — sensitivity of OOT metrics (DESCRIPTIVE; champion unchanged)

Validation log loss spread across the 12 pre-registered configs: 0.00059 — selection among them is close to noise. OOT Gini range 36.48–36.87, KS 26.29–26.70, CITL -1.81 to -1.54 pp. Weakest config minus scorecard OOT Gini (33.68) = 2.80 → the '≥ 2.0 Gini' conclusion holds for every config; every config under-predicts PD on OOT.

|   num_leaves |   min_child_samples |   lambda_l2 |   best_iter |   valid_logloss |   OOT Gini |   OOT KS |   OOT CITL pp | selected   |
|-------------:|--------------------:|------------:|------------:|----------------:|-----------:|---------:|--------------:|:-----------|
|           63 |                1000 |          10 |         184 |          0.3756 |    36.7777 |  26.5937 |       -1.7498 | ◀ champion |
|           15 |                1000 |          10 |         318 |          0.3756 |    36.8659 |  26.6337 |       -1.5482 |            |
|           15 |                1000 |           0 |         318 |          0.3756 |    36.821  |  26.7021 |       -1.5397 |            |
|           31 |                1000 |          10 |         208 |          0.3756 |    36.7879 |  26.5902 |       -1.7434 |            |
|           31 |                1000 |           0 |         191 |          0.3756 |    36.7747 |  26.6385 |       -1.6995 |            |
|           63 |                1000 |           0 |         183 |          0.3756 |    36.7553 |  26.6242 |       -1.6692 |            |
|           15 |                 200 |          10 |         318 |          0.3758 |    36.7051 |  26.4655 |       -1.5687 |            |
|           63 |                 200 |          10 |         143 |          0.3759 |    36.6235 |  26.4405 |       -1.8105 |            |
|           15 |                 200 |           0 |         238 |          0.3759 |    36.5618 |  26.4737 |       -1.6211 |            |
|           31 |                 200 |          10 |         183 |          0.376  |    36.5924 |  26.4972 |       -1.7049 |            |
|           31 |                 200 |           0 |         173 |          0.3761 |    36.4887 |  26.2867 |       -1.6871 |            |
|           63 |                 200 |           0 |         134 |          0.3762 |    36.4842 |  26.3877 |       -1.7269 |            |
