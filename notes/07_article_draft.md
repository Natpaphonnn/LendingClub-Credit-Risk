# 07 — Article draft (Medium, English) — 2026-11-20 (numbers after bank gate round 1 fixes)

> สำหรับ Nat: draft แรกสำหรับ Medium; ทุกตัวเลขตรวจกับ reports ได้ (provenance check รวมไฟล์นี้แล้ว) และ status ของแต่ละ claim ตาม
> notes/05_claims_and_limitations.md. Figures: reports/figures/article/fig1–8 + reports/figures/p4_asof_monitoring.png. Zenn (JP) ยังไม่ได้ทำ.

---

# My credit model kept ranking borrowers well. That was the problem.

*A bank-style post-mortem on public LendingClub data: a model built on 2012–13 loans, used from 2015 — did it survive, and would anyone have noticed in time?*

## The question

Every credit model is trained on the past and used in the future. The question a bank actually cares about is not "what is the AUC?" but
"if the world shifts after I deploy this, will my model still make the right decisions — and will my monitoring tell me before the losses do?"

I tried to answer that with LendingClub's public loan book (2.26 million accepted loans, 2007–2018). I wrote the decision rules down and
committed them to git before fitting anything (local commits for the first two phases, so that order is self-attested;
the later confirmatory tests were pushed to a private remote before computing), used time-based splits only, and published only aggregates. Several things I expected to work did
not, and I report those too.

## 1. Two traps before any model

*[Figure 1 — fig1_data_traps.png]*

My first plan was "would a 2007 model survive 2008?". The data said no: only **603 loans were issued in 2007 and 2,393 in 2008**. The crisis
cohort is too small to test anything.

The second trap is at the other end: 36-month loans issued after 2015 were still running when the data was cut in March 2019 (only 72% of 2016
loans had a final outcome). Computing a bad rate on "finished" loans of a young vintage over-weights the loans that failed early — 2016Q2 looks
worse than 2016Q1 (22.4% vs 16.1%) mainly because fewer of its loans had finished.

And almost a third of the columns are traps of their own: 38 of 151 are only known after the loan is funded (a "last FICO" that is actually refreshed
later; a "next payment date" whose emptiness reveals a closed loan), and 9 more are LendingClub's own pricing decisions.

So the story became: **train on loans issued Sep 2012 – Dec 2013, tune on 2014, test on 2015, and watch 2016–2018.**

## 2. The model beats LendingClub's own grades

*[Figure 2 — fig2_champion_vs_lc.png]*

I built two models from application data only: a classic weight-of-evidence scorecard (14 characteristics, points scaled to PDO 20) and a
LightGBM model with monotonic constraints, so that, for example, a higher FICO can never increase the predicted risk.

On unseen 2015 loans the LightGBM model reached a **Gini of 36.7 [36.3, 37.3]** against **33.7** for the scorecard — a paired difference of
+3.1 [2.8, 3.3], above the +2.0 bar I had committed to in advance. It also edges out LendingClub's own sub-grade (35.7). All twelve hyper-parameter configurations I tried land between 36.5 and 36.8, so the conclusion does not hinge on a
lucky setting. At the same bad-rate target the better model approves 82.1% of applicants instead of 77.4% — about 3 points of that gap
survive when the scorecard's integer points are not allowed to round the comparison in the champion's favour.

There is a catch, and it matters for the rest of the story: that model is trained on the *full* 36-month outcomes of 2012–13 loans, which
were only complete around 2017. No lender could have had it in January 2015. So I also built an **as-of model** from what a lender actually
knew on 31 December 2014 — a 12-month bad definition, outcomes up to June 2014. It scores **33.0**: 3.8 points lower. Part of the reference
model's edge is information from the future.

## 3. Ranking held — at first. Calibration did not.

*[Figure 3 — fig3_ranking_vs_level.png]*

On the three 2015 quarters whose outcomes are complete (2014 is the reference year), the champion's KS stayed between 25.8 and 27.2 — it never
came near its alarm line. The model kept putting borrowers in the right order. Later vintages cannot be judged on final outcomes yet, but against
defaults by month 12 the ranking did soften on the worst ones: KS for loans issued in mid-to-late 2016 was about 0.87–0.89 of its 2014 level
before recovering in 2017 (a descriptive check I added after review, not a pre-registered one).

But the *level* broke. On 2015 loans it under-predicted default by 1.7 percentage points (13.2% predicted vs 14.9% observed), and the cutoff
tuned to an 11% bad rate on 2014 delivered 11.9% on 2015. The ratio of actual to expected defaults by month 12 climbed from 0.93 for loans
issued in early 2014 to **1.46** for loans issued in the third quarter of 2016.

## 4. Population stability is the wrong alarm

*[Figure 4 — fig4_alarm_timeline.png] [Figure 5 — fig5_bands_mob12.png]*

The standard monitoring tool for scorecards is the population stability index: has the mix of applicants shifted? For the champion it stayed at
or below 0.06 in every quarter from 2014 to 2018 — comfortably green against an amber line of 0.10. The scorecard's PSI only went amber in 2018,
and then because applicants got *better*.

The characteristic-level alerts that did fire pointed the same reassuring way: revolving utilisation fell (median 59% → 41%) and LendingClub
verified more incomes.

The reason is that this was **concept drift**, not population drift. The same score meant more defaults: in the riskiest fifth of borrowers,
defaults by month 12 went from 7.0% to 10.8%; in the safest fifth from 1.1% to 2.3%. A stability index cannot see that by construction — it
looks only at the inputs.

Only label-based checks caught it, and labels take time. (The month-12 check is essentially the outcome itself, so its delay is
the observation window, not a design flaw.) If the reference model had been live from 2015, the first alarm (actual/expected
above 1.10) could have been known in **December 2016**, for loans first issued in April–June 2015. About 545k loans (544,642) were booked in between.
With the as-of model a lender really could have had, the first amber alarm comes in **June 2017** and the first red in September 2017 — about
two years after the first worse loans went out ("worse" meaning at least 1.2× the 2012–13 month-12 default rate).

## 5. Can we see it earlier? A failed early-warning signal

Defaults by month 6 looked like a faster signal: on 2015 loans it would have gone amber in June 2016, six months before the month-12 alarm. But I
had found it by looking, so it proved nothing.

So I wrote down a test before computing anything — on 60-month loans, which I had never analysed — and pushed it to a private repository:
the signal had to catch at least 80% of deteriorated quarters **and** stay quiet on at least 80% of the others. It caught all 9 deteriorated
quarters, but raised false alarms in 2 of 6 healthy ones (67% specificity). **It failed.** With only six healthy quarters that does not prove
the signal is unspecific — it proves I cannot show that it is. The two false alarms were quarters just below my "deteriorated" line (1.13–1.14×
the reference default rate versus 1.2×) whose defaults simply arrived earlier: a month-6 ratio mixes timing with level.

## 6. Lifetime PD needs prepayment as a competing risk

*[Figure 6 — fig6_prepayment_competing_risk.png]*

TFRS 9 / IFRS 9 needs *lifetime* default probabilities, and prepayment is the dominant way these loans end: 57% of fully repaid 36-month loans
paid off more than three months early. I fitted a discrete-time hazard with default and prepayment as competing risks. If you instead treat a
prepayment as "censored" — as if the borrower were still exposed to default — the same hazards give a lifetime PD of **18.0% instead of 13.4%**
on 2015 loans (actual 14.9%): about a third too high. (A plain 36-month default model doesn't have this problem; a survival model does.)

## 7. Macro data could not explain it — and a written-down rule caught a fake pass

Before looking at any macro data I wrote a rule: unemployment enters the model only if (a) its effect on default is positive with a confidence
interval above zero, (b) it improves out-of-time calibration by at least 10%, and (c) a 2008–09-style stress scenario raises lifetime PD by
1.1× to 3×.

With state unemployment from the US Bureau of Labor Statistics: **(a) failed** (the combined effect was −0.045, interval −0.099 to −0.009 — not
positive), **(b) passed** (calibration error fell 28%), **(c) failed** — the "adverse" 2008–09 scenario *lowered* predicted PD (0.89×).

The (b) pass is the interesting part. Between 2009 and 2014 unemployment fell while LendingClub's defaults rose, so the model learned "lower
unemployment, more defaults". That accident happens to fit 2015, so the macro model looked better out of time — for the wrong reason. Requiring
all three tests is what stopped it.

## 8. Expected vs realised loss

*[Figure 7 — fig7_ecl_backtest_overlay.png]*

I combined the lifetime PD with loss given default (88.8% — recoveries average only about 11% of the outstanding balance) and an amortising
exposure into a TFRS 9-style expected loss for the 2015 portfolio ($3.62 billion funded): **$100 million** of 12-month expected loss on day
one, $201 million lifetime.

Then I compared the lifetime expected loss at origination with what was actually lost: **$232 million predicted vs $274 million realised —
realised came in at 1.18× predicted.** A little of that is structural: on its own development loans the model is already at 1.03×,
because a scheduled-balance exposure understates what is outstanding when a borrower defaults.

Would recalibrating at the reporting date have saved it? I refitted the hazard at 31 December 2014 on outcomes a lender could see then.
It made things **worse: 1.27×** — and that is the generous version, because the refit can only see 21 months on book and I borrowed the
later months from the reference model; with those months also taken from data visible in 2014, it is 1.41×. The only outcomes visible in 2014 came from loans that performed better than the 2015 vintage — a refit
cannot learn about drift that has not happened yet. (An earlier version of this analysis said the refit closed a third of the gap. An
independent review showed that number came from extrapolating the hazard beyond the 21 months the refit could actually see; I withdrew it.)

Scaling expected loss by the observed month-12 actual/expected — a crude, in-sample "management overlay" — closes 57% of the gap, but only
once those month-12 outcomes are known.

Two honest caveats: the data has no monthly delinquency history, so stage 2 and 3 can only be illustrated after the fact (and "three missed
instalments" is closer to 60 than 90 days past due on the reporting date); and with the macro rule
failed, there is no forward-looking component — a real TFRS 9 model would need one.

## 9. A good cutoff is enough — the hard part is where to put it

*[Figure 8 — fig8_policy_cutoff_vs_milp.png]*

Finally I let an optimiser choose which risk cells to approve to maximise profit under an approval floor and a bad-rate cap. My pre-registered
profit measure was wrong — it ignored the cost of funds, so "approve everyone" looked best ($230 million). With a 5% funding cost, the simple
PD cutoff makes $47.5 million and the optimiser $45.8 million (these levels depend on how I timed the cash flows; the differences hold) — a difference of −$1.7 million with a bootstrap interval of −2.7 to −0.8, so on 2015
the optimiser is no better — slightly worse (the interval holds the chosen policies fixed and covers one vintage). At 3% the two are indistinguishable; at 8% the optimiser wins, but only because it approves fewer loans, and a
single PD threshold tuned the same way matches it at every rate. The cell structure adds nothing. Where to put the threshold is the hard
part: tuned to maximise NPV on a PD that was already under-predicting, the single threshold approved too many loans and made only $44.9
million — less than the plain risk-appetite cutoff. The level depends on the cost of funds *and* on how well calibrated the PD is.

## What I would tell a risk team

1. **Monitor the level, not just the mix and the ranking.** The champion's PSI stayed green throughout and its KS stayed green on every quarter
   it could be measured, while defaults ran up to 46% above expectation.
   Track actual/expected by vintage and months on book, with statistical bounds.
2. **Date your alarms by when they could have been known** — and build your monitoring model only from information available at the time.
   The realistic answer to "would you have noticed?" was "about two years later".
3. **If lifetime PD comes from a survival model, treat prepayment as a competing risk.**
4. **Write the rules down before you look.** The macro rule rejected a result that looked good for the wrong reason, and the early-warning test
   failed where my exploratory analysis had looked promising.
5. **Recalibration is necessary, not sufficient.** Refitting on what you can see cannot catch drift in vintages too young to have outcomes;
   pair it with early-performance monitoring — and let an independent reviewer try to break your numbers. Mine broke two of them.

*Data: LendingClub, via Kaggle dataset by Nathan George (wordsforthewise). Unemployment: U.S. Bureau of Labor Statistics. Raw data is not
redistributed; code, aggregates and the full list of claims and limitations are in the project repository.*
