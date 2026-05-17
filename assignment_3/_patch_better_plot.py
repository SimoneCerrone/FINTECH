"""Insert a fixed comparison plot cell (position: right after the
final-comparison cell, so it becomes cell 86).

The plot has two panels:
  1. Growth of 1, re-based on the common OOS start so target and replicas
     all start at 1.0 at the same date (avoids the 2008-2011 head-start
     artifact).
  2. Cumulative gap (replica - target) in growth-of-1 units: the curve
     closest to the zero line throughout the OOS is the replica that
     tracks the target most tightly.

Idempotent.
"""
import json
from pathlib import Path

NB_PATH = Path(__file__).parent / "Portfolio_ReplicaPoliMI_v3.ipynb"
HEADER_ANCHOR = "REBASED COMPARISON PLOT"

CELL_SOURCE = r'''# ============================================================================
# REBASED COMPARISON PLOT — target e repliche partono dallo stesso istante
# ============================================================================
# Il plot della cella precedente confrontava il target (dal 2008) con le
# repliche (OOS solo dal 2011): visivamente sembrava che le repliche
# battessero il target, ma è solo perché il target ha dovuto vivere il
# drawdown 2008-09 mentre le repliche no.
#
# Qui ri-basiamo target e repliche su un punto di partenza comune (il primo
# giorno OOS condiviso) e affianchiamo un secondo pannello col GAP cumulato
# replica − target: la curva più vicina allo zero è la replica più simile
# al target. Questa è la diagnostica visiva corretta.

oos_start = elnet_monthly['target'].index[0]  # tutti i modelli condividono lo stesso OOS

to_plot = [
    # (label, color, lw, alpha, series_of_net_returns)
    ('Target (Monster Index)',           'black',   2.4, 1.00, elnet_monthly['target']),
    ('EN tuned (riferimento)',           '#9e9e9e', 1.0, 0.55, elnet_monthly['net_returns']),
    ('Liquidity-aware (A)',              '#C45A4A', 1.6, 0.95, liq_result['net_returns']),
    ('Fully-invested NNLS',              '#5A8FBF', 1.4, 0.90, fi_nnls_result['net_returns']),
    ('Regime-aware composite (Stefano)', '#2E7D32', 1.8, 1.00, composite_result['net_returns']),
    ('B ⊕ Fully-invested NNLS (2A)',     '#9C27B0', 1.8, 1.00, adapt_fi_nnls_result['net_returns']),
    ('B ⊕ Idea 4 Constrained (2C)',      '#E08E45', 1.4, 0.85, adapt_constrained_result['net_returns']),
]

# Allineo tutto sul comune OOS index
target_oos = elnet_monthly['target'].loc[oos_start:]
cum_target = (1 + target_oos).cumprod()

fig, axes = plt.subplots(2, 1, figsize=(14, 11), sharex=True)

# ── Pannello 1: growth of 1 ri-basato ────────────────────────────────────
ax = axes[0]
for name, col, lw, a, series in to_plot:
    s = series.loc[oos_start:]
    cum = (1 + s).cumprod()
    ax.plot(cum, color=col, lw=lw, alpha=a, label=name)
ax.axhline(1.0, color='black', ls=':', lw=0.6, alpha=0.4)
ax.set_title('Growth of 1 — ri-basato sull\'OOS comune (tutti partono da 1.0 nello stesso istante)')
ax.set_ylabel('Growth of 1')
ax.legend(loc='upper left', ncol=2, fontsize=9)
ax.grid(alpha=0.3)

# ── Pannello 2: gap cumulato (replica − target), in growth-of-1 ──────────
ax = axes[1]
ax.axhline(0, color='black', ls='--', lw=1.0, alpha=0.7)
for name, col, lw, a, series in to_plot:
    if 'Target' in name:
        continue  # target è la baseline (linea zero)
    s = series.loc[oos_start:]
    cum_repl = (1 + s).cumprod()
    gap = cum_repl - cum_target
    ax.plot(gap, color=col, lw=lw, alpha=a, label=name)
ax.set_title('Gap cumulato (replica − target) — la curva più vicina allo zero traccia meglio')
ax.set_ylabel('Gap in growth of 1')
ax.set_xlabel('Date')
ax.legend(loc='upper left', ncol=2, fontsize=9)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ── Riepilogo numerico del gap finale ─────────────────────────────────────
final_target = cum_target.iloc[-1]
print(f"\nGap finale (replica − target) — valore di 1€ investito a {oos_start.date()}:")
print(f"  Target finale:                       {final_target:.4f}")
print()
rows = []
for name, _, _, _, series in to_plot:
    if 'Target' in name:
        continue
    s = series.loc[oos_start:]
    final_repl = (1 + s).cumprod().iloc[-1]
    gap = final_repl - final_target
    rows.append({
        'Modello':       name,
        'Replica fine':  round(final_repl, 4),
        'Gap finale':    round(gap, 4),
        'Gap (%)':       round(100 * gap / final_target, 2),
    })
display(pd.DataFrame(rows).sort_values('Gap (%)', key=lambda c: c.abs()))
'''


nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

# Idempotency: skip if header already present
already = any(
    HEADER_ANCHOR in "".join(c["source"])
    for c in nb["cells"]
    if c["cell_type"] == "code"
)
if already:
    print("Rebased-plot cell already present — nothing to do.")
else:
    # Find the position of the final-comparison cell to insert right after it
    target_idx = None
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] == "code" and \
           "FINAL COMPARISON — tutti i candidati di consegna" in "".join(c["source"]):
            target_idx = i
            break
    if target_idx is None:
        raise RuntimeError("Final-comparison cell not found.")

    new_cell = {
        "cell_type": "code",
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": [CELL_SOURCE],
    }
    nb["cells"].insert(target_idx + 1, new_cell)
    NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Inserted rebased-plot cell at index {target_idx + 1}.")
    print(f"New total cells: {len(nb['cells'])}")
