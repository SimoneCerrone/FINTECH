"""Defensive fix: restore TC_BPS = 2e-4 at the top of cells 73, 75, 77.

Cell 66 (Idea 5) overwrites the global TC_BPS to 5 (treating it as raw bps,
incompatible with the rest of the notebook which uses 2e-4 as a fraction).
When cells 73/75/77 are executed AFTER cell 66, their function defaults
`tc_bps=TC_BPS` are captured at def time with the polluted value of 5,
producing catastrophically wrong net_returns in the adaptive band paths
(first-week cost ≈ 5 × 0.6 = 3.0, cumprod((1 + r)) drops from 1 to −2).

We do not modify cell 66 (it is Idea-5 owner's code); instead, each of our
cells defensively resets TC_BPS to its canonical value before defining any
function that captures it as a default argument.

The patch inserts a 2-line block (one comment + one assignment) right after
each cell's leading header. Idempotent: skips cells where the block is
already present.
"""
import json
from pathlib import Path

NB_PATH = Path(__file__).parent / "Portfolio_ReplicaPoliMI_v3.ipynb"

MARKER = "TC_BPS = 2e-4  # defensive reset"
INSERT = (
    "\n"
    "# Defensive reset: cell 66 (Idea 5) overwrites the global TC_BPS to 5\n"
    "# treating it as raw bps. We restore the canonical 2bps-as-fraction\n"
    "# value here so the function defaults below capture the right number\n"
    "# regardless of the cell execution order.\n"
    "TC_BPS = 2e-4  # defensive reset (canonical 2 bps as fraction)\n"
)

TARGETS = {
    73: "# IDEA A — FIXED VERSION (V6) — sostituire la cella precedente con questa",
    75: "# IDEA B — FIXED VERSION — sostituire la cella precedente con questa",
    77: "# COMBINED (Idea A + Idea B) — FIXED VERSION",
}


nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

changed = []
for cell_idx, header_line in TARGETS.items():
    cell = nb["cells"][cell_idx]
    src = "".join(cell["source"])

    if MARKER in src:
        print(f"  cell {cell_idx}: already patched, skipping")
        continue

    # The header line is preceded by a "# ==========" decorator and followed
    # by another. We insert right after the SECOND "# ==========" (which closes
    # the header block).
    if header_line not in src:
        raise RuntimeError(
            f"cell {cell_idx}: header line not found:\n  {header_line!r}"
        )

    # Split by lines to locate the position
    lines = src.split("\n")
    # Find index of the header line, then the next decorator line
    h_idx = next(i for i, l in enumerate(lines) if header_line in l)
    # Locate the closing decorator line (next "# ====...")
    close_idx = next(
        i for i in range(h_idx + 1, len(lines))
        if lines[i].startswith("# ===")
    )
    # Re-insert: take lines[:close_idx+1], then INSERT block, then rest
    new_lines = (
        lines[: close_idx + 1]
        + INSERT.rstrip("\n").split("\n")
        + lines[close_idx + 1:]
    )
    new_src = "\n".join(new_lines)

    cell["source"] = [new_src]
    changed.append(cell_idx)
    print(f"  cell {cell_idx}: patched")

if changed:
    NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    print(f"\nWrote {NB_PATH}")
else:
    print("\nNo changes.")
