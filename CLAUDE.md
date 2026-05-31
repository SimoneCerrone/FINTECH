# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Coursework for **ML for Fintech** at Politecnico di Milano (Group 14, Cerrone / De Amici / Cataldi / Villani / Tomasini). Three self-contained "business cases", each materialised as a Jupyter notebook plus an Excel dataset. No shared Python package, no `requirements.txt`, no build system. Each assignment notebook is meant to run top-to-bottom.

```
assignment_1/   Bank client segmentation (clustering)
assignment_2/   Estimating client needs (classification)
assignment_3/   Portfolio replication (the biggest one)
```

Reports are PDFs in the assignment folders (`Zenti_Business_Case_*.pdf` is the prompt; `BC2_Group14_finale.pdf` is a delivered report). `assignment_3/_report_figs/` contains exported plots for the final PowerPoint.

## Environment

Notebooks run on Windows with CPython. Two Python paths are in active use across teammates:

```bash
"C:/Users/stefa/AppData/Local/Programs/Python/Python312/python.exe"   # primary
"C:/Users/stefa/AppData/Local/Programs/Python/Python314/python.exe"   # Stefano's machine
```

The bare `python` command on this machine resolves to the Microsoft Store stub and **fails** — always use a full path.

Dependencies are installed ad-hoc with `pip install`. The stack across the three notebooks: `numpy pandas scipy scikit-learn matplotlib seaborn statsmodels openpyxl`. Assignment 1 also uses `kmedoids`. Assignment 3 references `hmmlearn`, which **has no Python 3.13+ wheels at the moment** — the relevant cell falls back to `sklearn.mixture.GaussianMixture` via an adapter (`_RegimeDetector`).

## Running notebooks

Standard Jupyter / VS Code Jupyter. No project-level launcher. To regenerate a notebook from scratch use `Restart Kernel → Run All`.

Large notebooks (assignment 3 is ~50 MB with embedded base64 PNG outputs) **exceed Claude Code's `Read` token limit**. Two workarounds in active use:

- **Reading**: use `grep` / `awk` / `sed` via `Bash` rather than the `Read` tool. Searching by cell `id` is faster than by line number because IDs are stable across edits.
- **Editing**: scripted via `_apply_edits.py` files written to the assignment folder, executed once, then deleted. Pattern: read JSON → mutate `cells` array → `json.dumps(indent=1)` → write back. Avoid Unicode in `print` statements (Windows console is `cp1252` and crashes on `→`, `≈`, etc.).

The `NotebookEdit` tool also works but requires a prior `Read` of the file, which fails for assignment 3's main notebook. Use the Python-script approach there.

## Assignment 3 — required context

This is by far the most complex notebook and the one most actively iterated. Future Claude instances will spend most of their time here. Below is the "big picture" you cannot derive from a single file read.

### Replication problem

Target = synthetic **Monster Index** = `0.50 × HFRXGL + 0.25 × MXWO + 0.25 × LEGATRUU` (weekly returns). Investable universe = **11 futures** (`FUTURES = ['RX1','TY1','GC1','CO1','ES1','VG1','NQ1','LLL1','TP1','DU1','TU2']`), classified by `meta` dict into Equity DM / Equity EM / Bond / Commodity.

### Pipeline-level constants (assumed everywhere)

```python
best_window  = 208     # 4-year rolling training window, selected by EN grid search
rebalance_every = 4    # monthly for everything after the baselines
TC_BPS       = 2e-4    # flat 2 bps per unit of turnover (frequently reset defensively)
VAR_MAX      = 0.20    # 20% UCITS VaR cap
VAR_LOOKBACK = 156     # 3 years of history for the VaR estimator
ANN          = 52      # weekly → annualised
```

`TC_BPS` gets **overwritten to `5` by the Idea 5 cell** (sparse EN + turnover penalty), which treats it as raw bps. Cells downstream (Idea A V6, Idea B, Combined A+B, the cost reevaluation) all start with a defensive `TC_BPS = 2e-4` reset. Always preserve that line when editing.

### Models actually built (in order)

1. **Baselines** at `rolling_window=156`: OLS, Ridge, Lasso, ElasticNet — collapse onto OLS because default penalties are far below the binding scale.
2. **Elastic Net grid search**: sweeps `alpha ∈ [1e-5, 3e-1]`, `l1_ratio ∈ [0.1, 1.0]`, `window ∈ {104, 156, 208, 260}`. Wins `(208, 0.10, 0.3)`. From here on, `best_window=208` is the canonical training length.
3. **Re-baseline at 4 years**: re-fits the 4 baselines on `best_window` so all subsequent comparisons share the same OOS window.
4. **NN-Lasso** (`NNLSWrapper`): long-only via `scipy.optimize.nnls`, gross exposure ~0.65.
5. **Fully-invested NNLS** (`FullyInvestedNNLS`): adds `Σ w_j = 1` via SLSQP. Closes the "Beta gap". Net IR ≈ −0.02.
6. **Kalman filter** (`kalman_replication`): random-walk on `β`. Grid on `q`; winner is `q=1e-7` (essentially static weights).
7. **Idea 4** (`ConstrainedReplica`): asset-class exposure constraints + per-asset bounds + `Σ|w| ≤ 1.2`. Watch the intercept (see below).
8. **Idea A V6** (`fit_liquidity_aware`, `backtest_liquidity_aware`): adds per-asset transaction-cost penalty to the fit. `LIQUIDITY_PRIOR_BPS` is a hand-set dict (`TY1: 1.0`, …, `LLL1: 6.0`). Penalty auto-calibrates to ~`penalty_intensity × MSE / 100`.
9. **Idea B** (`backtest_adaptive`): fit-agnostic policy layer. At each rebalance, decide `rebalance iff expected_gain > θ_t · cost`, with `θ_t = θ_base × √(σ_base/σ_t) × √(TE_base/TE_t) × max(0.5, 1 − 0.05·k)`. Force-rebalances every `max_skip=12` weeks.
10. **Combined A+B** (`backtest_liquidity_adaptive`): A in the fit, B as the trading rule.
11. **Regime-aware composite** (Stefano's, FLIPPED): post-hoc switch — Liquidity-aware during calm, NN-Lasso during stress. Stress = target rolling-13w vol above expanding 70th percentile.
12. **HMM Idea 2** (`HMMReplicator`): per-regime Ridge fits, regime detector via hmmlearn or GMM fallback. Empirically worst of the candidates (turnover and gross blow up). Documented as a negative result.

### Two production candidates ("Conservative vs Tactical")

The end of the notebook proposes **two** replicators, not one, because the bootstrap CIs on TE / IR / Beta of the top models overlap completely:

- **Conservative**: `adapt_fi_nnls_result` = Adaptive band ⊕ Fully-invested NNLS. Σw=1, long-only, low turnover. The `Portfolio_ReplicaPoliMI_v3_case1.ipynb` file is this notebook run with the Conservative pick as `chosen_model` in the Forward-looking section.
- **Tactical**: `composite_result` = Regime-aware composite. Beta closer to 1 in stress (more faithful tracking), but contains shorts during calm. The main `Portfolio_ReplicaPoliMI_v3.ipynb` defaults to this pick (via `chosen_model = hmm2_result` historically, then `adapt_fi_nnls_result` after our fix — verify before assuming).

The Forward-looking section (Idea 8 stress test, Idea D conformal prediction, Idea E RL, Idea 8b historical replay) is **model-agnostic**: it reads `chosen_model` set in one place and propagates. The two notebook files exist precisely to produce the two sets of forward-looking results side by side.

### Recurring bug: the intercept on raw-vs-standardised scale

This bug has resurfaced in **at least five places** during the project (Idea 4, Idea A V6, Idea B, Combined A+B, the EWMA experiment). Symptom: TE looks reasonable but the cumulative return chart shows the replica running 2–4%/yr above the target, with IR net inflated to ≈ +0.9.

Root cause: a custom estimator (NNLS, ConstrainedReplica, etc.) sets `self.intercept_ = y.mean()` after fitting on raw-scale `X`. That value double-counts the X-drift when the prediction is `X[t] @ beta + intercept_`.

**Correct formula** (this is what `fit_linear_weights(..., normalise=True)` produces internally via `StandardScaler`):

```python
self.intercept_ = float(y.mean() - X.mean(axis=0) @ self.coef_)
```

When auditing any new replicator, plot cumulative gross returns of `replica` vs `target` over OOS — if the replica drifts steadily above the target, suspect this bug first.

### Backtest engine conventions

Two engines coexist:

- **`backtest(model_factory, X, y, ...)`** in cell `c2aac4f4` — generic. `model_factory()` returns a fresh sklearn-style estimator at each refit; the engine handles `StandardScaler` round-trip when `normalise=True`, Cornish-Fisher VaR scaling, transaction-cost-net returns, gross exposure and turnover bookkeeping.
- **Custom engines** (`backtest_liquidity_aware`, `backtest_adaptive`, `backtest_liquidity_adaptive`, `kalman_replication`) for cases where the standard factory contract doesn't fit (stateful Kalman, fit needs `w_prev`, A+B share state, etc.).

All return the same dict shape: `weights, gross_returns, net_returns, target, gross_exposure, var, scaling`. Some custom engines add `lambda_history`, `rebalance_flags`, `theta`. `report(res)` works on any of them.

### Stale / duplicated content

The notebook went through several rounds of consolidation. Be aware:

- **HMM Idea 2 markdown** is duplicated: there's a brainstorming-style `### Idea 2` markdown (Cerro's original list at ~line 4241) and an `## Idea 2 — implemented` heading further down with the actual code.
- **Idea 5** ("Sparse Machine Learning Replication") is the collaborator's standalone implementation. Targets HFRXGL alone (not the Monster Index) and uses `window_size=52`. Treat its numbers as not comparable with the rest of the notebook unless explicitly retrofitted.
- **Cells `f1efa32f` (FINAL COMPARISON) and `dbe90b89` (REBASED COMPARISON PLOT)** were removed in a refactor; their needed variables (`adapt_fi_nnls_result`, `adapt_constrained_result`) were migrated to a dedicated section between Combined A+B and the LIQUIDITY-AWARE COST REEVALUATION cell.

## House style (assignment 3)

- Markdown is bilingual: Italian for design notes / post-mortems, English for "Reading the results" / takeaways. Don't normalise.
- "Reading the X Results: Key Takeaways" cells in the first half of the notebook end with a `> **Note.**` soft-cap pointing to the final Production Recommendation. Preserve these — they're load-bearing for the narrative.
- The "apex of the notebook" framing was deliberately softened. Don't reintroduce "winner" language for individual models — the final position is "two candidates, choose by mandate".
- Cell additions go through `_apply_edits.py`. Use `if 'X' not in globals()` guards when injecting variables that another cell might also produce — keeps cells idempotent on kernel-warm reruns.
