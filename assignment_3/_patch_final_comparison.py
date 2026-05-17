"""Insert a new code cell with the final candidates comparison.

Position: immediately after cell 84 ("# FINE IDEE CERRO"), so it becomes
cell 85 (forward-looking section shifts from 85 to 86 onwards).

The cell:
  1. Defensively resets TC_BPS = 2e-4 (in case cell 67 of Idea 5 polluted it).
  2. Computes two NEW combinations identified as Priority 2 in the report
     roadmap:
       - 2A: Adaptive band (B) on Fully-invested NNLS
       - 2C: Adaptive band (B) on Idea 4 (Constrained)
  3. Builds a single comparison table including all existing models +
     Stefano's regime-aware composite + the two new combinations.
  4. Extends the stationary bootstrap CI to every candidate.
  5. Plots cumulative net-of-cost returns for the most relevant models.

Idempotent: if a cell with the same opening header is already present,
the script does nothing.
"""
import json
from pathlib import Path

NB_PATH = Path(__file__).parent / "Portfolio_ReplicaPoliMI_v3.ipynb"
HEADER_ANCHOR = "FINAL COMPARISON — tutti i candidati di consegna"

CELL_SOURCE = r'''# ============================================================================
# FINAL COMPARISON — tutti i candidati di consegna sullo stesso protocollo
# ============================================================================
# Confronto a parità di:
#   - rolling_window = best_window (208 weeks)
#   - rebalance_every = 4 (monthly)
#   - TC_BPS = 2e-4 (defensive reset, vedi celle 74/80/82)
#   - report() come unica funzione di metriche
#   - stationary_bootstrap come unica funzione di CI
#
# Include due combinazioni nuove identificate come Priorità 2 della roadmap:
#   - 2A: Adaptive band (B) ⊕ Fully-invested NNLS
#   - 2C: Adaptive band (B) ⊕ Idea 4 (Constrained)
# Più Stefano's Regime-aware composite (cella 76) per il confronto diretto.

TC_BPS = 2e-4  # defensive reset (vedi celle 74/80/82)

# ── 1) Nuove combinazioni di Priorità 2 ────────────────────────────────────
print("Running adaptive band on Fully-invested NNLS (Priorità 2A)…")
adapt_fi_nnls_result = backtest_adaptive(
    fully_invested_nnls_factory, futures_ret, target,
    rolling_window=best_window, rebalance_every=4,
    theta_base=1.5, normalise=False,
)
_n_rb = int(adapt_fi_nnls_result['rebalance_flags'].sum())
_n_op = len(adapt_fi_nnls_result['rebalance_flags'])
print(f"  Rebalances executed: {_n_rb} / {_n_op}  ({_n_rb / _n_op:.1%})")

print("Running adaptive band on Idea 4 Constrained (Priorità 2C)…")
adapt_constrained_result = backtest_adaptive(
    constrained_factory, futures_ret, target,
    rolling_window=best_window, rebalance_every=4,
    theta_base=1.5, normalise=False,
)
_n_rb = int(adapt_constrained_result['rebalance_flags'].sum())
_n_op = len(adapt_constrained_result['rebalance_flags'])
print(f"  Rebalances executed: {_n_rb} / {_n_op}  ({_n_rb / _n_op:.1%})")

# ── 2) Tabella unica — tutti i candidati a parità di protocollo ────────────
candidates = {
    'EN tuned (riferimento)':           elnet_monthly,
    'NN-Lasso (long-only)':             nnls_result,
    'Fully-invested NNLS':              fi_nnls_result,
    f'Kalman (q={best_q:.0e})':         kalman_best,
    'Idea 4 (Constrained)':             res_constrained,
    'Liquidity-aware (A)':              liq_result,
    'Adaptive band on EN (B)':          adapt_result,
    'Adaptive band on Kalman':          adapt_result_kalman,
    'Adaptive band on NN-Lasso':        adapt_result_nnls,
    'Liq + Adaptive (A+B, EN base)':    combo_result,
    'Regime-aware composite (Stefano)': composite_result,
    'B ⊕ Fully-invested NNLS (2A)':     adapt_fi_nnls_result,
    'B ⊕ Idea 4 Constrained (2C)':     adapt_constrained_result,
}

print("\n=== Tabella unica dei candidati (stesso OOS) ===")
display(pd.DataFrame({n: report(r) for n, r in candidates.items()}).T.round(4))

# ── 3) Bootstrap CI esteso (TE, IR, Beta) ──────────────────────────────────
print("\nComputing stationary bootstrap CIs (500 reps, mean block = 8 weeks)…")
ci_rows = []
for name, res in candidates.items():
    ci = stationary_bootstrap(res['target'], res['net_returns'])
    ci_rows.append({
        'Model':      name,
        'TE mean':    ci['TE']['mean'],
        'TE 5%':      ci['TE']['lo'],
        'TE 95%':     ci['TE']['hi'],
        'IR mean':    ci['IR']['mean'],
        'IR 5%':      ci['IR']['lo'],
        'IR 95%':     ci['IR']['hi'],
        'Beta mean':  ci['Beta']['mean'],
        'Beta 5%':    ci['Beta']['lo'],
        'Beta 95%':   ci['Beta']['hi'],
    })

ci_df = pd.DataFrame(ci_rows).round(4)
print("=== Bootstrap 90% confidence intervals (TE, IR, Beta) ===")
display(ci_df)

# ── 4) Plot cumulativo finale — solo i candidati di interesse ──────────────
def _cum(s):
    return (1 + s).cumprod()

fig, ax = plt.subplots(figsize=(14, 6.5))
ax.plot(_cum(target), color='black', lw=2.2, label='Target (Monster Index)')

# Pre-scelta dei candidati realmente in gara per la consegna
to_plot = [
    ('EN tuned (riferimento)',           '#9e9e9e', 1.0, 0.55),
    ('Liquidity-aware (A)',              '#C45A4A', 1.8, 1.0),
    ('Fully-invested NNLS',              '#5A8FBF', 1.4, 0.85),
    ('Regime-aware composite (Stefano)', '#2E7D32', 2.0, 1.0),
    ('B ⊕ Fully-invested NNLS (2A)',     '#9C27B0', 1.6, 0.95),
    ('B ⊕ Idea 4 Constrained (2C)',      '#E08E45', 1.5, 0.9),
]
for name, col, lw, a in to_plot:
    if name in candidates:
        ax.plot(_cum(candidates[name]['net_returns']),
                color=col, lw=lw, alpha=a, label=name)

ax.set_title('Confronto finale — cumulato net-of-cost dei candidati di consegna')
ax.set_ylabel('Growth of 1')
ax.legend(loc='upper left', ncol=2, fontsize=9)
plt.tight_layout()
plt.show()
'''


nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

# Sanity: cell 84 should be "# FINE IDEE CERRO"
expected = "FINE IDEE CERRO"
c84_src = "".join(nb["cells"][84]["source"])
if expected not in c84_src:
    raise RuntimeError(
        f"Cell 84 does not look like the expected anchor.\n"
        f"Got: {c84_src[:120]!r}"
    )

# Idempotency check: scan all code cells for our header
already = any(
    HEADER_ANCHOR in "".join(c["source"])
    for c in nb["cells"]
    if c["cell_type"] == "code"
)
if already:
    print("Final-comparison cell already present — nothing to do.")
else:
    new_cell = {
        "cell_type": "code",
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": [CELL_SOURCE],
    }
    nb["cells"].insert(85, new_cell)
    NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Inserted final-comparison cell at index 85.")
    print(f"New total cells: {len(nb['cells'])}")
    print(f"Wrote {NB_PATH}")
