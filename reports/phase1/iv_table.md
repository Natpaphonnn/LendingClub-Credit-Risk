# IV on train (2012-09..2013-12) and selection status

| feature                        |     iv |   n_bins | status                                         |
|:-------------------------------|-------:|---------:|:-----------------------------------------------|
| fico                           | 0.1198 |       12 | FINAL                                          |
| annual_inc                     | 0.102  |       13 | FINAL                                          |
| tot_hi_cred_lim                | 0.0782 |       10 | FINAL                                          |
| bc_open_to_buy                 | 0.0766 |        9 | FINAL                                          |
| avg_cur_bal                    | 0.0706 |       10 | corr drop: |r|=0.87 with tot_hi_cred_lim       |
| tot_cur_bal                    | 0.0629 |        7 | corr drop: |r|=0.95 with tot_hi_cred_lim       |
| total_bc_limit                 | 0.061  |       10 | corr drop: |r|=0.75 with bc_open_to_buy        |
| total_rev_hi_lim               | 0.0548 |       11 | corr drop: |r|=0.66 with bc_open_to_buy        |
| dti                            | 0.047  |        9 | FINAL                                          |
| loan_to_income                 | 0.0463 |        9 | FINAL                                          |
| mort_acc                       | 0.046  |        5 | corr drop: |r|=0.65 with tot_hi_cred_lim       |
| acc_open_past_24mths           | 0.0445 |        9 | FINAL                                          |
| num_tl_op_past_12m             | 0.0439 |        5 | corr drop: |r|=0.70 with acc_open_past_24mths  |
| mo_sin_rcnt_rev_tl_op          | 0.0387 |        9 | FINAL                                          |
| mo_sin_rcnt_tl                 | 0.0384 |        9 | corr drop: |r|=0.73 with mo_sin_rcnt_rev_tl_op |
| home_ownership                 | 0.0379 |        4 | corr drop: |r|=0.62 with tot_hi_cred_lim       |
| percent_bc_gt_75               | 0.0376 |        7 | FINAL                                          |
| bc_util                        | 0.0337 |       10 | corr drop: |r|=0.73 with bc_open_to_buy        |
| mths_since_recent_bc           | 0.032  |        8 | corr drop: |r|=0.65 with mo_sin_rcnt_rev_tl_op |
| mths_since_recent_inq          | 0.0319 |       10 | FINAL                                          |
| mo_sin_old_rev_tl_op           | 0.0316 |        9 | FINAL                                          |
| inq_last_6mths                 | 0.0273 |        4 | corr drop: |r|=0.79 with mths_since_recent_inq |
| revol_util                     | 0.0259 |        8 | corr drop: |r|=0.66 with percent_bc_gt_75      |
| mo_sin_old_il_acct             | 0.0244 |       10 | FINAL                                          |
| purpose                        | 0.0233 |        7 | FINAL                                          |
| num_rev_tl_bal_gt_0            | 0.0223 |        8 | FINAL                                          |
| num_actv_rev_tl                | 0.0221 |        8 | corr drop: |r|=1.00 with num_rev_tl_bal_gt_0   |
| credit_hist_months             | 0.0215 |       11 | corr drop: |r|=0.87 with mo_sin_old_rev_tl_op  |
| revol_bal                      | 0.0165 |        7 | IV<0.02                                        |
| emp_length_yrs                 | 0.0138 |        6 | IV<0.02                                        |
| total_bal_ex_mort              | 0.0133 |        6 | IV<0.02                                        |
| total_acc                      | 0.0129 |        9 | IV<0.02                                        |
| total_il_high_credit_limit     | 0.0122 |        6 | IV<0.02                                        |
| num_il_tl                      | 0.0112 |        8 | IV<0.02                                        |
| loan_amnt                      | 0.0089 |        5 | IV<0.02                                        |
| num_actv_bc_tl                 | 0.0051 |        4 | IV<0.02                                        |
| num_bc_tl                      | 0.0048 |        5 | IV<0.02                                        |
| num_op_rev_tl                  | 0.0037 |        9 | IV<0.02                                        |
| verification_status            | 0.0019 |        3 | IV<0.02                                        |
| mths_since_last_major_derog    | 0.0017 |        7 | IV<0.02                                        |
| num_rev_accts                  | 0.0017 |        7 | IV<0.02                                        |
| mths_since_last_record         | 0.0014 |        5 | IV<0.02                                        |
| tot_coll_amt                   | 0.001  |        2 | IV<0.02                                        |
| num_bc_sats                    | 0.0007 |        4 | IV<0.02                                        |
| mths_since_last_delinq         | 0.0005 |        4 | IV<0.02                                        |
| mths_since_recent_revol_delinq | 0.0005 |        5 | IV<0.02                                        |
| num_accts_ever_120_pd          | 0.0003 |        2 | IV<0.02                                        |
| mths_since_recent_bc_dlq       | 0.0002 |        4 | IV<0.02                                        |
| open_acc                       | 0.0001 |        4 | IV<0.02                                        |
| pct_tl_nvr_dlq                 | 0.0001 |        2 | IV<0.02                                        |
| num_sats                       | 0.0001 |        4 | IV<0.02                                        |
| pub_rec_bankruptcies           | 0      |        2 | IV<0.02                                        |
| delinq_2yrs                    | 0      |        2 | IV<0.02                                        |
| delinq_amnt                    | 0      |        1 | IV<0.02                                        |
| pub_rec                        | 0      |        1 | IV<0.02                                        |
| tax_liens                      | 0      |        1 | IV<0.02                                        |
| num_tl_90g_dpd_24m             | 0      |        1 | IV<0.02                                        |
| num_tl_30dpd                   | 0      |        1 | IV<0.02                                        |
| chargeoff_within_12_mths       | 0      |        1 | IV<0.02                                        |
| collections_12_mths_ex_med     | 0      |        1 | IV<0.02                                        |
| acc_now_delinq                 | 0      |        1 | IV<0.02                                        |
| num_tl_120dpd_2m               | 0      |        1 | IV<0.02                                        |
