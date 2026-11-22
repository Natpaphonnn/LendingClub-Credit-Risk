# 07 — Article draft (Medium, English) — 2026-11-20 (post-gate: numbers and meanings after bank gate rounds 1–2)

> สำหรับ Nat: draft สำหรับ Medium — เรียงใหม่: สิ่งที่รอดก่อน แล้วบอกสิ่งที่ fail ตรง ๆ. ทุกตัวเลขผ่าน provenance check; ทุกตัวเลขด้าน ECL และ
> policy ถูกคำนวณซ้ำแบบอิสระจาก raw (reports/quality/rederive_ecl_policy.md); status ของแต่ละ claim ตาม notes/05_claims_and_limitations.md.
> Figures: reports/figures/article/fig1–8 + reports/figures/p4_asof_monitoring.png. Zenn (JP) ยังไม่ได้ทำ.

---

# What survived when my credit model met 2015 — and what didn't

*A bank-style post-mortem on public LendingClub data: a model built on 2012–13 loans and used from 2015. Did it survive, and would anyone have
noticed in time?*

## The question

Every credit model is trained on the past and used in the future. The question a bank cares about is not "what is the AUC?" but "if the world
shifts after I deploy this, will my model still make the right decisions — and will my monitoring tell me before the losses do?"

I tried to answer that with LendingClub's public loan book (2.26 million accepted loans, 2007–2018). I used time-based splits only, published
only aggregates, and wrote the decision rules down before fitting anything. For the first two phases those rules are local git commits, so their
order is self-attested; the later confirmatory tests were pushed to a private remote before anything was computed. Then I let independent
reviewers try to break it. A first review found 1 critical and 10 major issues — the critical one: my month-6 "test" was not confirmatory,
because I had seen those values before setting the thresholds. A ten-reviewer gate then failed its first round on blocking issues, including a
bug in how the monotone constraints were enforced: fixing it retrained the champion and moved every number built on it. All of these were fixed,
and two results were withdrawn — the claim that refitting at the reporting date closed a third of the loss gap, and the month-6 "test" result,
now reported as descriptive. The second gate round passed. Where a correction matters below, I say so.

## The short version

**What survived**
- The model **ranks borrowers well**: it beats a classic scorecard and LendingClub's own sub-grade out of time, and its ranking held on every
  quarter whose outcomes are complete (to 2015Q3).
- **Prepayment must be a competing risk** in a lifetime-PD model; treating it as censoring overstates lifetime PD by about a third.
- **A pre-registered rule for macro variables** stopped a result that looked good for the wrong reason.
- **A plain PD cutoff is as good as an optimised approval policy** — no optimiser beat it.

**What failed**
- **Calibration**: defaults ran up to 46% above what the model expected.
- **Monitoring**: the stability index (PSI) never alarmed; with information a lender really had, the first alarm came in June 2017.
- **An early-warning signal** (defaults by month 6) **failed** its pre-registered confirmatory test.
- **Expected loss** came in below realised loss (1.18×), and refitting at the reporting date made it **worse** (1.27×).
- **Macro data** could not explain the drift, so there is no forward-looking component.

## Part 1 — What survived

### 1. Two traps before any model

*[Figure 1 — fig1_data_traps.png]*

My first plan was "would a 2007 model survive 2008?". The data said no: only **603 loans were issued in 2007 and 2,393 in 2008**.

The second trap is at the other end: 36-month loans issued after 2015 were still running when the data was cut in March 2019 (only 72% of 2016
loans had a final outcome). A bad rate on "finished" loans of a young vintage over-weights the loans that failed early — 2016Q2 looks worse than
2016Q1 (22.4% vs 16.1%) mainly because fewer of its loans had finished. And almost a third of the columns are traps of their own: 38 of 151 are
only known after the loan is funded, and 9 more are LendingClub's own pricing decisions.

So: **train on loans issued Sep 2012 – Dec 2013, tune on 2014, test on 2015, and watch 2016–2018.**

### 2. The model beats LendingClub's own grades

*[Figure 2 — fig2_champion_vs_lc.png]*

I built two models from application data only: a weight-of-evidence scorecard (14 characteristics, points scaled to PDO 20) and a LightGBM model
with monotonic constraints, so that, for example, a higher FICO cannot increase the predicted risk.

On unseen 2015 loans LightGBM reached a **Gini of 36.7 [36.3, 37.3]** against **33.7** for the scorecard — a paired difference of +3.1 [2.8, 3.3],
above the +2.0 bar I had committed to in advance — and edged out LendingClub's own sub-grade (35.7). All twelve hyper-parameter configurations land
between 36.5 and 36.8. At the same 11% bad-rate target the better model approves 82.1% of applicants instead of 77.4%; about 3 points of that gap
survive when the scorecard's integer points are not allowed to round the comparison in the champion's favour.

A catch that matters later: that model learned from the *full* 36-month outcomes of 2012–13 loans, complete only around 2017. No lender could
have had it in January 2015. A model built only from what a lender knew on 31 December 2014 (12-month bad definition, outcomes to June 2014)
scores **33.0** — 3.8 points lower. Part of the reference model's edge is information from the future.

### 3. Ranking held — where it can be measured

*[Figure 3 — fig3_ranking_vs_level.png]*

On every 2015 quarter whose outcomes are complete (2014 is the reference year), the champion's KS stayed between 25.8 and 27.2, never near its
alarm line. Later vintages cannot be judged on final outcomes yet; against defaults by month 12 the ranking softened on the worst ones — KS for
loans issued in mid-to-late 2016 was about 0.87–0.89 of its 2014 level before recovering in 2017 (a descriptive check added after review).

### 4. Lifetime PD needs prepayment as a competing risk

*[Figure 4 — fig4_prepayment_competing_risk.png]*

TFRS 9 / IFRS 9 needs *lifetime* default probabilities, and prepayment is the dominant way these loans end: 57% of fully repaid 36-month loans
paid off more than three months early. I fitted a discrete-time hazard with default and prepayment as competing risks. Treat a prepayment as
"censored" instead — as if the borrower were still exposed to default — and the same hazards give a lifetime PD of **18.2% instead of 13.6%** for
loans issued January–September 2015 — the 2015 loans whose first 36 months are fully observable — against an actual 14.7% defaulted by month
36: about a third too high. A plain 36-month default model does not have this problem; a survival model does.

### 5. A written-down macro rule caught a fake pass

Before looking at any macro data I wrote a rule: unemployment enters the model only if (a) its effect on default is positive with a confidence
interval above zero, (b) it improves out-of-time calibration by at least 10%, and (c) a 2008–09-style stress scenario raises lifetime PD by 1.1×
to 3×. With state unemployment from the US Bureau of Labor Statistics, **(a) failed** (the combined effect was −0.045, interval −0.099 to −0.009),
**(b) passed** (calibration error fell 28%), and **(c) failed** — the "adverse" 2008–09 scenario *lowered* predicted PD (0.89×).

The (b) pass is the interesting part. Between 2009 and 2014 unemployment fell while LendingClub's defaults rose, so the model learned "lower
unemployment, more defaults". That accident happens to fit 2015, so the macro model looked better out of time — for the wrong reason. Requiring
all three tests stopped it. The rule worked; the macro signal did not.

### 6. A plain PD cutoff is as good as an optimiser

*[Figure 5 — fig5_policy_cutoff_vs_milp.png]*

I let an optimiser (a mixed-integer program over 30 risk × loan-size cells) choose which cells to approve to maximise expected profit under an
approval floor and a bad-rate cap. My pre-registered profit measure was wrong — it ignored the cost of funds, so "approve everyone" looked best
($230 million, against $222 million for the optimiser).

With a 5% funding cost, on 2015 loans the simple PD cutoff (82% approved) made $47.5 million, the optimiser (86% approved) $45.8 million, and
approving everyone $28.4 million. The optimiser minus the cutoff is −$1.7 million, bootstrap interval −2.7 to −0.8 — it was no better, slightly
worse (the interval holds the chosen policies fixed and covers one vintage). At a 3% funding cost the two are indistinguishable; at 8% the
optimiser comes out ahead only because it approves fewer loans. These dollar levels depend on how I timed the cash flows; the differences hold.

The cell structure adds nothing over one threshold. *Where* to put the threshold is the hard part: a single PD threshold tuned to maximise NPV on a
PD that was already under-predicting approved too many loans and made $44.9 million — less than the plain risk-appetite cutoff.

## Part 2 — What failed

### 7. Calibration broke

The *level* broke. On 2015 loans the champion under-predicted default by 1.7 percentage points (13.2% predicted vs 14.9% observed), and the
cutoff tuned to an 11% bad rate on 2014 delivered 11.9% on 2015. The ratio of actual to expected defaults by month 12 climbed from 0.93 for loans
issued in early 2014 to **1.46** for loans issued in the third quarter of 2016.

### 8. Population stability was the wrong alarm — and the real alarm came late

*[Figure 6 — fig6_alarm_timeline.png] [Figure 7 — fig7_bands_mob12.png]*

The standard monitoring tool is the population stability index: has the mix of applicants shifted? For the champion it stayed at or below 0.06 in
every quarter from 2014 to 2018, against an amber line of 0.10. The scorecard's PSI only went amber in 2018, and then because applicants got
*better*. Characteristic-level alerts pointed the same reassuring way: revolving utilisation fell (median 59% → 41%) and LendingClub verified
more incomes.

This was **concept drift**, not population drift: the same score meant more defaults. In the riskiest fifth of borrowers, defaults by month 12
went from 7.0% to 10.8%; in the safest fifth from 1.1% to 2.3%. A stability index looks only at the inputs, so it cannot see that.

Only label-based checks caught it, and labels take time. With the reference model live from 2015, the first alarm (actual/expected above 1.10)
could have been known in **December 2016**, for loans issued in April–June 2015; about 545k loans (544,642) were booked in between. With the model
a lender really could have had, the first amber alarm comes in **June 2017** and the first red in September 2017 — about two years after the
first worse loans went out ("worse" meaning at least 1.2× the 2012–13 month-12 default rate). Eighteen months of that is the month-12
observation window itself: a month-12 check is close to the outcome it is checking.

### 9. The early-warning signal failed its test

Defaults by month 6 looked like a faster signal: on 2015 loans it would have gone amber in June 2016, six months before the month-12 alarm. But I
had found it by looking, so it proved nothing.

So I wrote a test down before computing anything — on 60-month loans, which I had never analysed — and pushed it to a private repository: the
signal had to catch at least 80% of deteriorated quarters **and** stay quiet on at least 80% of the others. It caught all 9 deteriorated quarters
but raised false alarms in 2 of 6 healthy ones (67% specificity). **It failed.** With only six healthy quarters that does not prove the signal
is unspecific — it shows I cannot demonstrate that it is specific. The two false alarms were quarters just below my "deteriorated" line
(1.13–1.14× the reference default rate versus 1.2×) whose defaults arrived earlier: a month-6 ratio mixes timing with level.

### 10. Expected loss came in short — and a refit made it worse

*[Figure 8 — fig8_ecl_backtest_overlay.png]*

I combined the lifetime PD with loss given default (88.8% — recoveries average only about 11% of the exposure at default) and an amortising
exposure into a TFRS 9-style expected loss for the 2015 portfolio ($3.62 billion funded): **$100 million** of 12-month expected loss on day one,
$201 million lifetime.

Against what was actually lost: **$232 million predicted vs $274 million realised — realised came in at 1.18× predicted.** A little of that is
structural: on its own development loans the model is already at 1.03×, because a scheduled-balance exposure understates what is outstanding when
a borrower defaults.

Would recalibrating at the reporting date have saved it? I refitted the hazard at 31 December 2014 on outcomes a lender could see then. It made
things **worse: 1.27×** — and that is the generous version: the refit can only see 21 months on book, and I borrowed the later months from the
reference model; with those months also taken from data visible in 2014, it is 1.41×. The outcomes visible in 2014 came from loans that performed
better than the 2015 vintage — a refit cannot learn about drift that has not happened yet. (An earlier version of this analysis said the refit
closed a third of the gap. A reviewer showed that number came from extrapolating the hazard beyond those 21 months; I withdrew it.)

Scaling expected loss by the observed month-12 actual/expected — a crude, in-sample "management overlay" — closes 57% of the gap, but only once
those month-12 outcomes are known.

Two more corrections the review forced. The data has no monthly delinquency history, so stages 2 and 3 can only be illustrated after the fact,
and my labels were one bucket generous: "three missed instalments" is about **60** days past due on the reporting date, not 90. With the stage
thresholds I had pre-registered, 1,571 loans sit in stage 2 and 2,300 in stage 3 at December 2015; aligned with the real 30- and 90-day
backstops the counts are 1,521 and 1,640. Likewise the default definition I had labelled "90 days" is really about 60: dating default at the
third missed instalment gives a 12-month ECL of $79 million, at the fourth (about 90 days) $68 million, against $101 million for the reference
definition (all with recoveries discounted). Lifetime loss barely moves either way. And with the macro rule failed, there is no forward-looking
component — a real TFRS 9 model would need one.

## What I would tell a risk team

1. **Monitor the level, not just the mix and the ranking.** The champion's PSI stayed green throughout and its KS stayed green on every quarter
   it could be measured, while defaults ran up to 46% above expectation. Track actual/expected by vintage and months on book, with statistical
   bounds.
2. **Date your alarms by when they could have been known** — and build your monitoring model only from information available at the time. The
   realistic answer to "would you have noticed?" was "about two years later".
3. **If lifetime PD comes from a survival model, treat prepayment as a competing risk.**
4. **Write the rules down before you look.** The macro rule rejected a result that looked good for the wrong reason, and the early-warning test
   failed where my exploratory analysis had looked promising.
5. **Recalibration is necessary, not sufficient.** Refitting on what you can see cannot catch drift in vintages too young to have outcomes; pair it
   with early-performance monitoring — and let independent reviewers try to break your numbers. Mine found a critical flaw, a bug that changed
   the champion model, and two results I had to withdraw.

Try the interactive version: https://natpaphonnn.github.io/LendingClub-Credit-Risk/

*Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise). Unemployment: U.S. Bureau of Labor Statistics. Raw data is not
redistributed; code, aggregates and the full list of claims and limitations are in the project repository.*
