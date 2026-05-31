# -*- coding: utf-8 -*-
"""
English refactor of the project extensions section (cells 72-142).
- All markdown rewritten in English, concise, professional.
- No team names, no 'Approfondimenti suggeriti' lists, no internal references.
- Code comments (headers + main blocks) translated to English.
- Indentation preserved (no regex bulk operations).
"""
import json

NB_PATH = r'EarlyWarningSystemPoliMI.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))
cells = nb['cells']

def set_md(i, s):
    cells[i]['source'] = s.splitlines(keepends=True)
    cells[i]['cell_type'] = 'markdown'

def replace_in_code(i, old, new):
    src = ''.join(cells[i]['source'])
    if old not in src:
        return False
    cells[i]['source'] = src.replace(old, new).splitlines(keepends=True)
    return True

# =============================================================
# MARKDOWN REWRITES
# =============================================================

# CELL 72 — Custom Extensions preamble
set_md(72, '''# Custom Extensions

Markets crash. Lehman 2008: -55% in 18 months. COVID 2020: -28% in four weeks. For an investor with one million euros invested, that is 550,000 or 280,000 euros gone.

The question driving this section is simple: **can we build a system that detects these crises before the damage is done?**

In Zenti\\'s words: *we do not need to forecast the future, we need to recognize the present at its dawn*. Catching the moment when something is shifting, even a few weeks early, is already worth a lot.

The pipeline below extends the didactic notebook in five sections, each building on the previous one, with the recurring rule of strict causality (walk-forward, no peeks at future data).
''')

# CELL 73 — Part 1
set_md(73, '''## Part 1 - Features & Target

> *To recognize a crisis, we need clues. The first move is to build them and change the question we ask the model: instead of "is this week anomalous?" we ask "will there be a crisis in the next four weeks?". From reactive to predictive.*

This section transforms raw prices into *precursor signals* and defines a new label for the model: anomaly within the next four weeks. The output (`P` for features, `y_ahead` for the label) is the input to every model that follows.
''')

# CELL 74 — Baseline reframing
set_md(74, '''### Reframing the problem: predictive label and nine precursors

Up to this point the notebook answered the question *"is this week anomalous?"* — recognizing a crisis **while** it happens. We need to **anticipate** it. The new question is:

> *"Will there be an anomaly in the next four weeks?"*

This shifts the problem from recognition to **prediction**. Everything downstream (models, evaluation metric, lead time) follows from this change.

For the model to work it needs **leading indicators** — signals that historically move *before* market stress materializes (the *precursors*). Nine of them are built, all strictly past-only:

- **Volatility acceleration** — short-term equity vol minus medium-term vol (is turbulence picking up?).
- **Average cross-market correlation** — how synchronized are the global equity indices? (high correlation is a classic fragility signal).
- **Credit tension** — high-yield bond index in decline (credit spreads widening).
- **VIX momentum** and **VIX level** — accelerating fear, and starting point of that fear.
- **Yield curve slope (10y - 3m)** — historically a flat or inverted curve precedes stress.
- **Drawdown velocity** — how fast equity is moving away from its peak.
- **Baltic Dry momentum** and **economic surprise** — global trade and macro data disappointing.

**Pipeline steps in the code below:**
1. Build the **predict-ahead label** for each week (1 if any anomaly within the next H=4 weeks).
2. Construct the nine precursors with strictly causal rolling windows.
3. Trim early weeks without history and the last H weeks (incomplete future).
''')

# CELL 76 — Extended features bridge (replaces "Approfondimenti")
set_md(76, '''### Extended features, selection and horizon comparison

Two additional systemic-risk features and a sanity check on the horizon choice:

- **`absorption_ratio`** — fraction of variance of global equities explained by the top 2 principal components on a 52-week window. High value = markets dominated by few common factors = systemic stress (Kritzman et al. 2011).
- **`credit_spread`** — causal high yield minus 10-year Treasury, rolling 4-week mean.

A **mutual information** ranking of all features against `y_ahead` highlights which precursors carry real predictive signal. Finally, three horizon choices (H = 2, 4, 8 weeks) are compared on positive-class prevalence — H = 4 emerges as the right balance between reactivity and signal density.
''')

# CELL 78 — Part 2
set_md(78, '''## Part 2 - Evaluation Framework & Supervised Models

> *Now that we have the clues, we need an honest machine to score them. The framework below is a strictly causal walk-forward: each week the model sees only past data and predicts the next observation. Then nine supervised models compete on the same playing field. The somewhat surprising result is that a plain Logistic Regression (three lines of code) beats XGBoost, RandomForest and Gradient Boosting. The complex models add nothing because the financial knowledge is already baked into the precursors. Sometimes complexity is just noise.*

This section builds the **shared evaluation engine** (walk-forward, no look-ahead) used by every subsequent model, and trains the supervised candidates on the precursors. The output is the `scores` dictionary, the dates, the feature matrices and the shared `START/STEP` constants.
''')

# CELL 80 — Step A
set_md(80, '''### Step A - Tunable model registry

A dictionary of candidate models with their hyperparameter search spaces:
**Logistic (L2)**, **ElasticNet**, **RandomForest**, **HistGradientBoosting**, plus **LightGBM** and **XGBoost** if available. Search spaces are deliberately compact (3-4 values per parameter) to find robust regions rather than global optima.
''')

# CELL 82 — Step B
set_md(82, '''### Step B - Fast tuning with RandomizedSearchCV on TimeSeriesSplit

Tuning runs on the **first 60% of weeks** with `TimeSeriesSplit(n_splits=4)` (always past -> future, no leakage). For each model, 20 random hyperparameter combinations are evaluated, optimizing **average precision** (PR-AUC). Total runtime: a few minutes on this dataset.
''')

# CELL 84 — Step C
set_md(84, '''### Step C - Walk-forward scoring with tuned hyperparameters

Each tuned model is run through the walk-forward engine and its out-of-sample probability series is added to the shared `scores` dictionary. To avoid memory pressure on Windows Jupyter, models are run one at a time. A safety summary at the end shows how many valid scores each model produced.
''')

# CELL 93 — Step D
set_md(93, '''### Step D - Probability calibration

A high PR-AUC does not guarantee **interpretable probabilities**. A model can output `prob=0.8` while only 40% of those cases are actual crises. For a risk manager that difference is large.

- **Reliability diagram**: compare predicted-probability bins against the actual fraction of positives. A perfect diagonal = perfectly calibrated.
- **Brier score**: mean squared error between predicted probability and outcome. Lower is better.
- **Platt scaling** (sigmoid) is applied uniformly to every candidate model with enough valid weeks, producing a calibrated `_platt` version of each score. Platt is preferred over Isotonic because it preserves the ranking (PR-AUC stays constant) and is more robust with limited positives.
''')

# CELL 95 — Step E
set_md(95, '''### Step E - Final summary table

All supervised models (raw + tuned + calibrated) are summarized and sorted by PR-AUC. This is the input the next section consumes for unsupervised additions and the section after that consumes for model selection.
''')

# CELL 97 — Part 3
set_md(97, '''## Part 3 - Unsupervised, Temporal & Regime Models

> *We now add different lenses to the race. Models that need no labels (they learn what a "normal" week looks like and flag the strange ones), models that exploit time structure (LSTM Autoencoder on weekly sequences), models that reason about hidden regimes (HMM/GMM with latent states). Completely different philosophies, same evaluation metric. All strictly out-of-sample, all running through the same framework.*

This section appends to the shared `scores` dictionary with anomaly detectors that do not rely on prior labels and with models that capture temporal dynamics or regime structure. Continuity with Lab 3 is preserved through an HMM-based regime detector.
''')

# CELL 99 — Deep Dive 1 LOF + OC-SVM (already mostly english, polish)
set_md(99, '''### Deep Dive 1 - LOF and One-Class SVM

Two classic anomaly detectors that complete the unsupervised suite:

- **LOF (Local Outlier Factor)**: flags weeks whose density is anomalous *relative to their local neighborhood*, capturing context-dependent outliers.
- **One-Class SVM**: learns a non-linear RBF boundary enclosing normal data; the anomaly score is the distance from this boundary.

Both are evaluated through the shared walk-forward engine to guarantee zero look-ahead.
''')

# CELL 101 — Deep Dive 2 HMM 2vs3
set_md(101, '''### Deep Dive 2 - HMM regime detector: 2 vs 3 states

Markets often display three regimes: calm, transition, and crisis. A third hidden state could capture the *build-up phase* — the weeks where stress quietly accumulates before the crash. The 2-state and 3-state versions are compared with **Spearman correlation** between the predicted stress probability and `y_ahead`, on a temporally split selection / validation set. The 3-state variant is kept only if it confirms its advantage on the validation half.
''')

# CELL 103 — Deep Dive 3 CUSUM
set_md(103, '''### Deep Dive 3 - Change-point detection via CUSUM

**CUSUM** accumulates positive deviations of a signal above a `drift` threshold. It stays at zero during normal periods and rises progressively as systemic stress builds up, producing an actionable signal *before* the crisis peak.

Here CUSUM is applied to a **composite signal** (the normalized average of all unsupervised detectors), so that the change-point detector leverages the consensus across models rather than a single noisy stream.
''')

# CELL 105 — Deep Dive 4 LSTM-AE
set_md(105, '''### Deep Dive 4 - LSTM Autoencoder on temporal sequences

The vanilla autoencoder processes single independent weeks. An **LSTM Autoencoder** processes **rolling windows of consecutive weeks** as sequences, capturing temporal structure — most notably *volatility clustering*.

- **Encoder**: an LSTM layer (hidden=32) compresses a rolling window of 8 consecutive weeks into a latent vector.
- **Decoder**: an LSTM layer reconstructs the original sequence from the latent representation.
- **Anomaly score**: the MSE of the reconstruction; weeks whose temporal pattern breaks historical norms are harder to reconstruct.

Strictly integrated into the walk-forward framework with periodic retraining on past data only.
''')

# CELL 107 — Summary Part 3
set_md(107, '''### Summary and visualizations

Four diagnostics close this section:

1. **Score timeline** of every Part 3 detector overlaid with the actual crisis bands.
2. **Spearman correlation matrix** between detectors, to measure redundancy (uncorrelated errors are the foundation of a good ensemble).
3. **PR-AUC table** comparing every model on the common out-of-sample period.
4. **Random baseline** = positives prevalence, for reference.

The `valid` mask defining the common out-of-sample period is finalized here and consumed by the model-selection section that follows.
''')

# CELL 109 — Part 4
set_md(109, '''## Part 4 - Model Selection & Ensemble

> *With all the candidates in the `scores` dictionary, we need a referee. Three independent tests measure different facets of usefulness (statistical predictivity, timeliness, operational reliability). The winner is then stress-tested for statistical solidity via bootstrap confidence intervals.*

This section selects `best_name`, the single model that will be carried into the final business case.
''')

# CELL 110 — Three-test framework
set_md(110, '''### Three-test framework + Ensemble candidate

Models compete on three independent exams, then ranked by total placement:

- **Test 1 - Predictivity**: how well does the score predict crises within four weeks? (PR-AUC + ROC-AUC).
- **Test 2 - Timeliness**: how many weeks in advance does the alarm trigger before actual crises? (lead-time + fraction of crises anticipated).
- **Test 3 - Reliability**: is the model operationally usable? (precision at recall>=0.5 + Sharpe and MaxDD of the simple "cash on alarm" backtest).

An **Ensemble** candidate (mean of normalized supervised scores) is included for comparison, but the final pick goes to the best **single** model, for simplicity and reproducibility.
''')

# CELL 112 — Statistical robustness
set_md(112, '''### Statistical robustness: Brier, Bootstrap CI, Stacking, Uncertainty

Four extensions to validate the winner:

- **Brier score** for each candidate — quality of the predicted probabilities (complements PR-AUC, which measures only ranking).
- **Bootstrap 95% CI** on the winner\\'s PR-AUC — 500 resamples of the valid period, to show whether the win is solid or within sampling noise.
- **Stacking ensemble** — a Logistic Regression trained on the normalized scores of all candidates, evaluated on a held-out temporal half.
- **Uncertainty signal** — standard deviation across supervised models per week, as a proxy for cross-model disagreement (high-disagreement alarms are natural candidates for human-in-the-loop review).
''')

# CELL 114 — Part 5
set_md(114, '''## Part 5 - Explainability, Stress Test & Business Case

> *The final section turns the winning model into something credible and useful: it explains why the alarm fires, stress-tests it on real and synthetic crises, and translates everything into the language of money.*
''')

# CELL 115 — Crisis archetypes intro
set_md(115, '''### Crisis archetypes and local explanation

A model nobody trusts is a model nobody uses. Two angles to make the system readable:

- **Crisis archetypes** — actual anomaly weeks are clustered (KMeans) on the precursors. Each cluster has a dominant signature: equity shock, rate shock, credit tension, etc. The alarm becomes a **diagnosis**, not a binary flag.
- **Local explanation** — for the week with the highest predicted risk, the most extreme precursors are shown (in standard deviations). This is the *why* behind a single alarm.

**Pipeline steps below:**
1. Cluster the anomaly weeks on standardized precursors; identify each cluster\\'s dominant variables and its position in time.
2. Pick the week with the highest score; show its most extreme precursors as a per-alarm narrative.
''')

# CELL 117 — n_clusters justification (already long, condense + translate)
set_md(117, '''### Choice of `n_clusters = 3` and archetype interpretation

**Why 3 and not other values.** The silhouette of KMeans peaks sharply at `k=2` (0.44) but that configuration is a degenerate "more stressed vs less stressed" split — it merely re-derives `y_now`. From `k=3` onwards the silhouette is flat around 0.19, so no granularity is statistically preferred. We pick the smallest value that produces a financially readable story: three archetypes.

**The three archetypes are sequential phases of the same crisis, not three different types of crisis.** Wear-out -> Panic -> Recovery is the pattern that every historical crisis in the sample exhibits — a powerful narrative result.

---

#### Type 0 - "Wear-out / diffuse stress" (n=128)
Negative average correlation, mild VIX, slightly negative macro surprise, mild VIX momentum. **Anomalous weeks without systemic panic**: markets still desynchronized, implied vol contained, macro data slightly below expectations. The *default* of anomaly weeks: the slow burn of 2000-2003, the early signals of 2007-08, the tails of post-panic episodes.

#### Type 2 - "Acute panic / crisis bottom" (n=24)
Credit tension +1.8 sigma, VIX +1.8 sigma, drawdown velocity strongly negative, VIX momentum rising. **Peak stress**: explosive credit tension, very high VIX, drawdown accelerating. Few episodes by nature (~10% of anomaly weeks). In the timeline these fall exactly on Lehman (autumn 2008 - early 2009) and March 2020 (COVID) - the actual historical bottoms.

#### Type 1 - "Recovery / correlated rebound" (n=81)
Correlation +0.87, drawdown velocity +0.78 (drawdown shrinking), VIX momentum -0.77, credit tension easing. **Rebound phase after the shock**: correlation spikes because everything bounces together, drawdown improves, VIX deflates, high-yield recovers. Visible in March-December 2009 (post-Lehman), end of 2012 (euro crisis), end of 2020.

---

**Overall reading.** Wear-out -> Panic -> Recovery. Every historical crisis in the sample (2000-03, 2008-09, 2011-12, 2018, 2020) shows the same color signature in the timeline. For a risk manager this means the alarm is not a binary traffic light: it tells *which phase of the stress cycle* we are in — decisive information for deciding whether to hedge, wait, or rebalance.
''')

# CELL 118 — Stress test intro
set_md(118, '''### Historical stress test: replay of 2008 / 2011 / 2020

The concrete question: *"if we had used this model during a past crisis, how would it have performed?"* Three real crises are replayed comparing two worlds:

- **Buy & Hold** (always invested in US equities);
- **Alarm strategy** (move to cash whenever the model fires an alarm).

For each crisis we measure return, max drawdown, the perdita avoided thanks to the model, and the lead time before the local trough.

**Pipeline steps:**
1. Define the crisis windows: 2008 (financial crisis), 2011-2012 (euro debt), 2020 (COVID).
2. Use the winning model\\'s predicted probability (already out-of-sample and causal from Part 2).
3. Decision rule: alarm fires when probability exceeds the operational threshold; the following week the position moves to cash.
4. Compute the two equity curves and their MaxDD.
5. Lead-time: weeks between the first alarm and the local trough.
6. Threshold sensitivity (q70 / q85 / q90) for each crisis.
''')

# CELL 120 — Synthesis stress test
set_md(120, '''**Stress test synthesis (3 historical crises)**

- **2008 (slow burn):** the q70 strategy cuts MaxDD from -55.2% to a single-digit drawdown and the return from -39.5% to nearly flat. Alarm active for ~84 consecutive weeks: it effectively "stays out" for almost two years — wins on DD but at a large opportunity cost.
- **2011 (euro debt with rebound):** q70 underperforms B&H significantly and the DD is slightly worse. The model fires too long before the actual stress and misses the 2012 rebound. A realistic scenario that exposes the limits of a low fixed threshold.
- **2020 (COVID shock):** q70 halves the DD but gives up the V-shape recovery. Lead time only ~2-4 weeks — rapid exogenous shocks are not statistically predictable.
- **Threshold sensitivity:** different winners per crisis - q70 in 2008/2020, q90 in 2011. **No fixed threshold wins everywhere** -> motivation for an adaptive rule in the next steps.
- **Switch counts are non-monotonic in the threshold:** low threshold -> almost continuous alarm (few transitions); moderate threshold -> oscillation around the level (many transitions). Important for the transaction-cost analysis that follows.
''')

# CELL 121 — TC intro
set_md(121, '''### Transaction costs

Each cash<->equity switch costs: bid-ask spread, slippage, possibly commissions. On a liquid equity ETF a realistic cost ranges from **3-5 basis points** (institutional broker) to **10 bp** (retail). A strategy that flips signal often gets penalized disproportionately.

The baseline above ignored TC. Here the same backtest is repeated *including* costs to see how the performance erodes per basis point. Persistent strategies (few transitions) absorb TC well; noisy strategies that oscillate constantly get destroyed. This is the reality check before any deployment claim.
''')

# CELL 123 — TC synthesis
set_md(123, '''**Synthesis - Transaction costs**

- **Linear impact in n_switch x cost_bp.** At 10 bp/switch the erosion is at most ~0.9 points (the crisis with most switches), trivial in absolute terms.
- **Operational conclusion:** even at realistic levels (5-10 bp/switch) the model holds up. Transaction costs selectively penalize noisy strategies but do not flip the threshold ranking.
''')

# CELL 124 — Step A backtest full-period
set_md(124, '''### Step A - Full-period backtest of fixed thresholds

Apply the three fixed thresholds (q70 / q85 / q90) across the entire common out-of-sample period (~17 years). This measures the value of the strategy *even during normal times*, not only during catastrophes. The **Calmar Ratio** (CAGR / |MaxDD|) is the key metric here — how much return per unit of maximum loss endured.

Buy & Hold and "always cash" act as the two extreme benchmarks.
''')

# CELL 126 — Synthesis A
set_md(126, '''**Synthesis - Step A**

- **All three fixed thresholds beat B&H on Calmar** (0.20 - 0.30 vs B&H 0.14): the model adds structural value, not only during catastrophes.
- The best fixed threshold reduces MaxDD by ~50% versus B&H, at the cost of some CAGR.
- "Always cash" as a floor confirms that the strategy produces real return, not just "stay out of the market".
''')

# CELL 127 — Already in italian, rewrite in english
set_md(127, '''### Step B - Recovery Detector with Double Confirmation

> *The fixed-threshold and adaptive strategies built so far share one structural flaw: they use the same signal to decide both **when to exit** and **when to re-enter**. But "a crisis that is starting" and "a crisis that is ending" are statistically different problems — they cannot be solved by one model.*

**The idea: two specialized models, two distinct targets.**

- **Model A (existing)**: the winning Logistic Regression on the 9 precursors. Target = *crisis within the next 4 weeks* (`y_ahead`). Knows how to recognize the dawn of a crisis.
- **Model B (new)**: a sibling Logistic Regression with a completely different target = *MXUS forward 6-week log-return > +5%* = sustained rebound coming (`y_recovery`). Knows how to recognize the dawn of a recovery.
- Model B features: the 9 precursors + 6 recovery-specific features (current drawdown, weeks-in-drawdown, VIX off-peak distance, 4-week momentum, declining volatility, credit recovery).

**The rule: Double Confirmation.** Two independent signals must align before acting:

- **Exit** equity when A is loud (score_A > q70) **AND** B is quiet (score_B < q40) - "flight confirmed".
- **Re-enter** equity when B is loud (score_B > q60) **AND** A is quiet (score_A < q60) - "return confirmed".
- Under ambiguity (both high or both low) **do not act**.

**Strict causality.** All thresholds are **expanding causal**: for each week t the quantile is computed only over the scores observed up to t-1. No look-ahead. Deployment-ready.

> The crisis-archetypes clustering above remains as **diagnostic explainability** ("Wear-out -> Panic -> Recovery"). It is no longer used to set operational thresholds — the rule is Double Confirmation.
''')

# CELL 129 — Synthesis B
set_md(129, '''**Synthesis - Step B (Recovery Detector)**

- **The strategy beats Buy & Hold** (CAGR ~9.7% vs B&H 7.63%, **+2.1 points/year**). First result in the pipeline where the system is not only a risk filter but **generates true alpha**.
- **Calmar ~0.35 vs B&H 0.138**: the risk-adjusted return is ~2.5x the passive benchmark.
- **MaxDD still halved** (~-28% vs B&H -55%), despite the higher CAGR. Dominant on both dimensions.
- **Only ~16 switches in 17 years**: at 10 bp/switch the total cost is ~EUR 160 on the final ~470k — negligible.
- **Model B PR-AUC = ~0.33** (modest). The value does not come from a single brilliant model B but from the **A+B combination with the double-confirmation rule**: two weak but independent signals, when aligned, produce a strong effect. Ensemble logic, not model brilliance.
- **The causal version confirms the result**: every threshold is expanding (per t, quantile over scores observed up to t-1). No look-ahead. Directly deployable.

> **Counter-intuitive but real**: the causal version is actually *better* than an in-sample version. Reason: the expanding quantiles are lower in the early years (when history is short), so the system fires *earlier and better* during the 2008 crisis. Rigorous causality here helps, not penalizes.
''')

# CELL 130 — Step C intro
set_md(130, '''### Step C - Recovery Detector on the three crisis windows

The baseline stress test is replayed (2008 / 2011 / 2020) using **Double Confirmation A+B** instead of the fixed or adaptive thresholds. The narrative for each crisis shows why the system works:

- **2008 - financial crisis** — Model A loud (VIX at 80, high-yield collapsing, drawdown accelerating). Model B silent (systemic crises historically do not bounce quickly). **A high + B low -> EXIT.** Correct decision.
- **2011 - euro debt** — Model A sees European credit tension. Model B moderately high (moderate stress often bounces). Mixed decision: cash intermittently, decent but underperforms B&H. Honestly declared partial false alarm.
- **2020 - COVID** — Model A screams in panic. **Model B ALSO SCREAMS**: extreme drawdown velocity + VIX off-peak declining + long DD = historical rebound pattern imminent. **A high + B high -> DO NOT ACT.** Stay 100% invested and catch the COVID rebound.

This is the differential intelligence the second model was built for. **2020 is the true methodological success** of the pipeline: instead of running away and missing the V-shape (like every previous strategy), the system distinguishes "systemic crash" from "crash with rebound".
''')

# CELL 132 — Synthesis C
set_md(132, '''**Synthesis - Step C (Recovery Detector on the three crises)**

- **2008**: the strategy exits the market ~89% of the time (Model B low confirms the flight). Return ~-10% vs B&H -39%. MaxDD -14% vs -55%. **Clear win** on drawdown.
- **2011**: cash ~37%. Return +5% vs B&H +13%. Partial false alarm: A loud, B uncertain -> the system oscillates. Below B&H but honest (not a real crisis).
- **2020**: cash 0%. Return ~+7.7% vs B&H +7.7%. **The system does not exit at all** because B recognizes the rebound pattern. **Identical to B&H** = a draw = an implicit win (previously the system would have lost ~-13% by missing the rebound).

**Overall reading.** Without Model B the system would flee from every crisis and miss the 2020 rebound. With Model B it **distinguishes**: exit systemic ones (2008), stay invested during fast-rebound shocks (2020). The operational translation of *"recognize them at their dawn"* — the dawn applies both to crises and to recoveries.

**2011 remains the weak spot**: real but non-systemic stress causes a partial flight and gives up the moderate recovery. Honestly declared limit, acceptable price for the 2008 protection.
''')

# CELL 133 — Transparency intro
set_md(133, '''### Transparency - what the winning model looks at

Global feature importance for the winning model, in a model-agnostic way: Spearman rank correlation between each precursor and the winning model\\'s out-of-sample scores. Non-parametric, captures monotonic non-linear relationships, works regardless of which model wins.

As a sanity check, a Logistic Regression surrogate is fit on the same standardized precursors and its `|coef|` ranking is compared with the Spearman ranking. If they agree, we have linear validation of the winning model\\'s signal; if they diverge, the model is exploiting non-linearities the Logistic does not see.
''')

# CELL 135 — Synthesis transparency
set_md(135, '''**Synthesis - Explainability**

- **Two features dominate the signal**: `livello_vix` and `correlazione_media`. The remaining seven all have weaker rank correlation, and several are essentially noise. The alarm fires when **implied fear** and **cross-asset correlation** rise together — two established signals of systemic stress in macro finance.
- **The Spearman vs Logistic rankings are highly concordant** when the winner is itself a linear model, as expected — a sanity check that the model is interpretable as standardized coefficients.
- **Practical implication for the CIO**: the alarm narrative is `"VIX up + correlation up"`. Simple to explain, easy to monitor outside the model, robust as an operational signal.
- **Documented robustness risk**: the signal is heavily concentrated on the VIX. A structural distortion of implied volatility (policy interventions, market-making convention changes, a new volatility regime) would compromise the system. Worth including in the model\\'s operational risk register.
''')

# CELL 136 — Business case intro
set_md(136, '''### Business case in EUR - what the strategy is worth in money

Translation of the strategies into the language of the CIO. **EUR 100,000** ideally invested in US equities (MXUS) at the start of the out-of-sample period, tracked to the end, comparing:

- **Buy & Hold** - passive benchmark, always invested;
- **q90 fixed** - the best static threshold from Step A;
- **Recovery Detector (A+B)** - the Step B strategy with double-confirmation causal rule.

**Transaction costs**: 10 basis points per switch (conservative for liquid equity ETFs). B&H pays no TC. The Recovery Detector has ~16 switches in 17 years -> TC negligible (~EUR 160 on the final capital).

**Outputs**: final capital in EUR, total profit, CAGR, max drawdown in % and in EUR, max loss avoided vs Buy & Hold, additional profit vs Buy & Hold. Equity curves in EUR on log scale.
''')

# CELL 138 — Synthesis business case
set_md(138, '''**Synthesis - Recovery Detector business case in EUR**

- **EUR 100,000 invested for 17 years** via the Recovery Detector grows to **~EUR 484,000**, versus **EUR 353,000 with passive Buy & Hold**. **Additional profit: ~+EUR 131,000** - about one-third more capital than the benchmark.
- **CAGR 9.67% vs B&H 7.66%**: +2.0 percentage points per year of pure alpha. Compounded over 17 years the advantage is large.
- **MaxDD still halved**: -28% vs -55%. The system **dominates on both dimensions** (return AND risk).
- **Transaction costs** (10 bp/switch) included: 16 switches in 17 years = ~EUR 160 on EUR 484k, irrelevant.
- **The story for the CIO**: this is not just a risk filter, it is an **alpha generator**. The combination "exit signal (A) + entry signal (B) with double confirmation" resolves the classic Risk-vs-Quant trade-off: the system dominates both perspectives.

> **The honest caveat**: Model B has modest PR-AUC (~0.33). The value comes from the **combination** with Model A via double confirmation - ensemble logic, not single-model brilliance. A solid methodological story, not a statistical trick.
''')

# CELL 139 — Synthetic stress test intro
set_md(139, '''### Robustness - stress test on synthetic scenarios (t-Student copula + k-NN)

1,000 synthetic weeks are generated from a t-Student copula (df=4, fat tails) fit on the nine historical precursors. The scenarios preserve the **dependence structure** between features but are new realizations, some more extreme than anything observed in 17 years of data — continuity with the Lab 3 inverse stress testing.

**Model-agnostic approach via k-NN**: for each synthetic scenario the **closest historical week** (1-NN in standardized space) is identified. Two complementary metrics emerge:

- **Distance to the nearest neighbor**: how out-of-distribution the scenario is.
- **Neighbor\\'s score as a proxy**: if the winning model would have flagged the historical week, it presumably would flag the synthetic scenario too.

This makes the section **completely independent of the chosen model** — no surrogate refit, the OOS scores are reused directly.

**Outputs**: distribution of NN distances, % of "out-of-distribution" scenarios (distance >= 3 z-units), % of scenarios flagged by the model via proxy, top 10 farthest scenarios with the profile of the 3 most extreme precursors, scatter rarity vs proxy score.
''')

# CELL 141 — Synthesis robustness
set_md(141, '''**Synthesis - Robustness on synthetic scenarios (t-Copula + k-NN)**

- **Alarm frequency stable outside training**: the model flags ~30% of synthetic scenarios, matching its historical q70 selectivity. No distributional drift: on 1,000 unseen "alternative" weeks the model maintains the same selectivity.
- **Recall on worst-case = 80-90%**: of the 10 scenarios farthest from the training set (NN distance >= 5.5 z-units), most are correctly flagged. The model holds up even on extreme realizations never observed, as long as the signature matches its known drivers (VIX, correlation, credit, drawdown velocity).
- **The false negatives are interpretable**:
  - Extreme calm scenarios (NOT flagged, correctly): high distance reflects "rare" not "risky"; the model is right to ignore.
  - **Decoupled credit-only crises** (NOT flagged, true weakness): credit tension explodes but cross-asset correlation does not synchronize (rare historical case, e.g. LTCM 1998). The model is blind here because its signature depends on "high VIX + high correlation".
- **Documented operational limit**: the system does not catch atypical decoupled crises. Natural extension: a complementary detector based purely on credit-spread signals.
- **Continuity with Lab 3**: the t-Student copula is the scenario generator from the previous lab. The model-agnostic k-NN approach makes the analysis robust to any change in the underlying winning model.
''')

# CELL 142 — Conclusions (rewrite in English, no team names)
set_md(142, '''## Conclusions

This extension answers the initial question: *which model best anticipates market crises, and how much is that worth?*

### The pipeline at a glance

- **Section 1 (Features & Target)**: 9 causal precursors (volatility, cross-market correlation, credit tension, VIX, yield curve slope, drawdown velocity, Baltic Dry, economic surprise), plus an absorption ratio from academic literature and a credit spread feature. Mutual information for selection, horizon comparison H = 2 / 4 / 8.
- **Section 2 (Evaluation Framework + Supervised)**: causal walk-forward engine, 9 supervised models tuned with RandomizedSearchCV on TimeSeriesSplit, uniform Platt-scaling calibration. The Logistic Regression wins for simplicity and Brier score.
- **Section 3 (Unsupervised + Temporal + Regime)**: Isolation Forest, GMM, COPOD, LOF, OC-SVM, HMM-based regime detector (with GMM fallback when hmmlearn is unavailable, validated 2-vs-3 states), CUSUM on the composite signal, LSTM Autoencoder on weekly sequences.
- **Section 4 (Model Selection)**: 3-test framework (predictivity, timeliness, reliability) + Brier score + Bootstrap 95% CI + Stacking ensemble + cross-model uncertainty signal.
- **Section 5 (Explainability + Stress + Business Case)**: KMeans crisis archetypes + local explanation, historical replay 2008/2011/2020 + synthetic stress test via t-Student copula, **Recovery Detector A+B** with double confirmation that pushes the system above Buy & Hold.

### Final result

**Technical winner** (Section 4): **Logistic Regression** (PR-AUC 0.602). The bootstrap 95% CI [0.54, 0.66] includes the top 3 supervised models (ElasticNet 0.604, Logistica_tuned 0.598) - statistically indistinguishable. Choice = the simplest and most interpretable.

**Operational strategy** (Section 5): **Recovery Detector A+B** with causal double confirmation.
- Model A (Logistic) on 9 precursors, score for "crisis within 4 weeks".
- Model B (sibling Logistic) on 9 precursors + 6 recovery features, score for "+5% rebound within 6 weeks".
- Rule: exit only if A loud **AND** B silent; re-enter only if B loud **AND** A silent; under ambiguity do not act.

### Business case

EUR 100,000 invested in MSCI USA, 17.1 years out-of-sample, transaction costs 10 bp/switch:

| Strategy | Final capital | CAGR | Max DD | Calmar |
|---|---|---|---|---|
| Buy & Hold | EUR 353,409 | 7.66% | -55.2% | 0.138 |
| q90 fixed (+TC) | EUR 292,359 | 6.48% | -31.6% | 0.205 |
| **Recovery Detector A+B (+TC)** | **EUR 484,488** | **9.67%** | **-27.7%** | **0.351** |

**Additional profit vs Buy & Hold: +EUR 131,079** (+37% more profit). **MaxDD halved** (from -55% to -28%). **Calmar 2.5x** the benchmark. The system overcomes the classic Risk-vs-Quant trade-off: it dominates **both** dimensions.

Diagnostic across the three crises:
- **2008** (financial crisis): cash 89%, return -10% vs B&H -39%. Clear win on drawdown.
- **2011** (euro debt): cash 37%, return +5% vs B&H +13%. Honestly declared partial false alarm.
- **2020** (COVID): cash 0%, return +7.7% **identical to B&H**. The system recognizes the "crash with rebound" pattern and stays invested - the methodological signature of the Recovery Detector.

### Three takeaways

**Technical**: in financial machine learning, the *model* matters less than expected. What makes the difference is **rigorous causality** (no peeks at the future), **target engineering** (change the question and you change the problem), and the **intelligent combination of weak signals** (Model B has PR-AUC ~0.33 alone, yet within the double-confirmation rule becomes the decisive ingredient).

**Epistemological**: complexity does not win. A Logistic Regression with 9 well-built features beats XGBoost, LSTM Autoencoder and Random Forest on the actual Bloomberg dataset. All the added value was in the precursors and in the operational rule — not in sophisticated models. *Sometimes complexity is just noise.*

**Narrative**: the value of an anomaly detection system for markets does not lie in beating the market on average. It lies in **distinguishing between types of crises**. A 2008 (systemic, slow, destructive) must be treated the opposite way of a 2020 (exogenous, fast, with rebound). Without distinction you always run or always stay - lose both ways. **Distinguishing is the true dawn to recognize**: not the dawn of the crisis itself, but the dawn of its **nature**.

### Closing line

> *Two specialized models talk to each other. One recognizes crises, the other recognizes recoveries. When they agree we act, when they disagree we stay still. Over 17 years versus passive Buy & Hold we earn 131,000 euros extra per 100,000 invested, with the maximum drawdown halved. Every number we report is statistically honest.*

### Honestly declared limits

1. **The Regime detector is a GMM** (fallback used when hmmlearn is unavailable, e.g. on Python 3.14+).
2. **2011 is a partial false alarm**: the model sees credit tension that does not turn into systemic crisis; the strategy partially exits and gives up some of the rebound. Structural limit.
3. **Model B PR-AUC is modest** (~0.33). The system\\'s value comes from the A+B double-confirmation combination - ensemble logic, not single-model brilliance.
4. **Decoupled credit-only crises** (e.g. LTCM 1998) are missed: the model\\'s signature depends on "high VIX + high correlation". Natural extension: a complementary credit-only detector.
5. **t-Copula stress test** shows the model maintains the same selectivity (~30% alarms) on 1,000 unseen synthetic scenarios, with high recall on worst-case out-of-distribution scenarios.
''')

# =============================================================
# CODE COMMENT TRANSLATIONS (precise replacements)
# =============================================================

# Cell 75 — Vitto's code: translate header
replace_in_code(75, "# 1) Etichetta predict-ahead: 1 se c'e' un'anomalia in [t+1, t+H]",
                    "# 1) Predict-ahead label: 1 if any anomaly within [t+1, t+H]")
replace_in_code(75, '# 2) Feature "precursori" (tutte causali: solo passato)',
                    '# 2) Precursor features (all causal: past only)')
replace_in_code(75, "# 3) Pulizia: via le righe senza storia e le ultime H (futuro incompleto)",
                    "# 3) Cleanup: drop rows without history and the last H (incomplete future)")
replace_in_code(75, '    P[\'accel_volatilita\'] = stationary_df[\'MXUS\'].rolling(4).std() - stationary_df[\'MXUS\'].rolling(12).std()',
                    '    P[\'accel_volatilita\'] = stationary_df[\'MXUS\'].rolling(4).std() - stationary_df[\'MXUS\'].rolling(12).std()')
replace_in_code(75, "W = 13  # correlazione media tra azionari sulle ultime 13 settimane",
                    "W = 13  # average cross-equity correlation over last 13 weeks")
replace_in_code(75, "    P['tensione_credito'] = -stationary_df['LF98TRUU'].rolling(4).mean()           # high yield in calo",
                    "    P['tensione_credito'] = -stationary_df['LF98TRUU'].rolling(4).mean()           # high yield declining")
replace_in_code(75, "    P['slancio_vix']      = stationary_df['VIX'].rolling(4).mean()                  # accelerazione paura",
                    "    P['slancio_vix']      = stationary_df['VIX'].rolling(4).mean()                  # fear acceleration")
replace_in_code(75, "    P['livello_vix']      = X_df['VIX'].reindex(idx)                               # livello paura",
                    "    P['livello_vix']      = X_df['VIX'].reindex(idx)                               # fear level")
replace_in_code(75, "    P['pendenza_tassi']   = (X_df['GT10'] - X_df['USGG3M']).reindex(idx)           # curva 10Y-3M",
                    "    P['pendenza_tassi']   = (X_df['GT10'] - X_df['USGG3M']).reindex(idx)           # yield curve 10Y-3M")
replace_in_code(75, "    P['velocita_drawdown'] = drawdown.diff(4)                                      # quanto velocemente scende",
                    "    P['velocita_drawdown'] = drawdown.diff(4)                                      # drawdown speed")
replace_in_code(75, "    P['slancio_baltic']   = -stationary_df['BDIY'].rolling(8).mean()              # commercio globale in calo",
                    "    P['slancio_baltic']   = -stationary_df['BDIY'].rolling(8).mean()              # global trade declining")
replace_in_code(75, "    P['sorpresa_econ']    = -X_df['ECSURPUS'].reindex(idx).rolling(4).mean()      # dati macro che deludono",
                    "    P['sorpresa_econ']    = -X_df['ECSURPUS'].reindex(idx).rolling(4).mean()      # disappointing macro data")

# Cell 79 — Cata's code header
replace_in_code(79, "# === FRAMEWORK DI VALUTAZIONE CONDIVISO + MODELLI SUPERVISIONATI ===",
                    "# === SHARED EVALUATION FRAMEWORK + SUPERVISED MODELS ===")

# Cell 81 — Step A header
replace_in_code(81, "# === Step A: registro dei modelli da tunare ===",
                    "# === Step A: registry of models to tune ===")

# Cell 83 — Step B tuning
replace_in_code(83, "# === Step B: random search con TimeSeriesSplit (sulla parte iniziale) ===",
                    "# === Step B: random search with TimeSeriesSplit (on initial portion) ===")

# Cell 85 — Step C setup
replace_in_code(85, "# === Setup comune Step C: helper e parametri conservativi ===",
                    "# === Step C common setup: helpers and conservative parameters ===")

# Cell 92 — Safety net
replace_in_code(92, "# === Safety net: garantisce che `scores` abbia almeno i modelli baseline ===",
                    "# === Safety net: ensures `scores` has at least the baseline models ===")

# Cell 94 — Step D header
replace_in_code(94, "# === Step D: reliability diagram + Brier + calibrazione Platt UNIFORME () ===",
                    "# === Step D: reliability diagram + Brier + UNIFORM Platt calibration ===")
replace_in_code(94, "# === Step D: reliability diagram + Brier + calibrazione Platt UNIFORME ===",
                    "# === Step D: reliability diagram + Brier + UNIFORM Platt calibration ===")

# Cell 96 — Step E
replace_in_code(96, "# === Step E: tabella riassuntiva finale ===",
                    "# === Step E: final summary table ===")

# Cell 108 — Summary Part 3
replace_in_code(108, "# === Summary Parte 3: tabella PR-AUC su valid_full (no Platt/Isotonic) ===",
                     "# === Part 3 Summary: PR-AUC table on valid_full (excludes Platt/Isotonic) ===")

# Cell 116 — Crisis archetypes
replace_in_code(116, "# 1) Tipi di crisi: clustering delle settimane anomale (Y=1) sui precursori",
                     "# 1) Crisis archetypes: clustering of anomaly weeks (Y=1) on precursors")
replace_in_code(116, "# 2) Spiegazione locale: la settimana col rischio previsto piu' alto",
                     "# 2) Local explanation: the week with the highest predicted risk")

# Cell 122 — TC code
replace_in_code(122, "# === Costi di transazione: impatto sulla performance al variare del costo per switch ===",
                     "# === Transaction costs: performance erosion at varying cost per switch ===")

# Cell 125 — Step A backtest
replace_in_code(125, "# === Step A: backtest full-period delle soglie fisse ===",
                     "# === Step A: full-period backtest of fixed thresholds ===")

# Cell 134 — Explainability
replace_in_code(134, "# === Explainability: importanza globale dei precursori per il modello vincente ===",
                     "# === Explainability: global precursor importance for the winning model ===")

# Cell 140 — t-Copula
replace_in_code(140, "# === Stress test sintetico con copula t-Student + k-NN proxy scoring ===",
                     "# === Synthetic stress test with t-Student copula + k-NN proxy scoring ===")

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("English refactor completed.")
