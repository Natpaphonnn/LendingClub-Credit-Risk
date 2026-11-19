# LightGBM grid — sensitivity of OOT metrics (DESCRIPTIVE; champion unchanged)

Validation log loss spread across the 12 pre-registered configs: 0.00048 — selection among them is close to noise. OOT Gini range 36.47–36.79, KS 26.31–26.67, CITL -1.77 to -1.56 pp. Weakest config minus scorecard OOT Gini (33.68) = 2.79 → the '≥ 2.0 Gini' conclusion holds for every config; every config under-predicts PD on OOT.

|   num_leaves |   min_child_samples |   lambda_l2 |   best_iter |   valid_logloss |   OOT Gini |   OOT KS |   OOT CITL pp | selected   |
|-------------:|--------------------:|------------:|------------:|----------------:|-----------:|---------:|--------------:|:-----------|
|           31 |                1000 |           0 |         192 |          0.3757 |    36.7422 |  26.5336 |       -1.6961 | ◀ champion |
|           15 |                1000 |           0 |         270 |          0.3758 |    36.7319 |  26.4943 |       -1.6106 |            |
|           63 |                1000 |          10 |         196 |          0.3758 |    36.7327 |  26.6724 |       -1.7314 |            |
|           15 |                1000 |          10 |         318 |          0.3758 |    36.789  |  26.5822 |       -1.5865 |            |
|           63 |                1000 |           0 |         157 |          0.3759 |    36.6099 |  26.582  |       -1.7661 |            |
|           15 |                 200 |          10 |         304 |          0.3759 |    36.7106 |  26.5215 |       -1.5607 |            |
|           31 |                1000 |          10 |         214 |          0.3759 |    36.6896 |  26.4998 |       -1.694  |            |
|           31 |                 200 |          10 |         192 |          0.3759 |    36.6334 |  26.4436 |       -1.7218 |            |
|           15 |                 200 |           0 |         250 |          0.376  |    36.5861 |  26.4248 |       -1.6024 |            |
|           31 |                 200 |           0 |         165 |          0.3761 |    36.5174 |  26.3058 |       -1.6958 |            |
|           63 |                 200 |          10 |         172 |          0.3761 |    36.4699 |  26.3791 |       -1.7314 |            |
|           63 |                 200 |           0 |         135 |          0.3762 |    36.4699 |  26.3693 |       -1.7229 |            |

## Cost of the monotone constraints (descriptive; gate R5-2)

Champion config without constraints: validation log loss 0.37481 (constrained 0.37568); OOT Gini 37.16 (constrained 36.74). Not a candidate model — shown to size what the interpretability constraint costs.
