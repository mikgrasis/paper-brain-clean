#!/usr/bin/env python3
"""
Applies the vault's graph color groups (from graph-colors.json)
to a vault's .obsidian/graph.json.

.obsidian/graph.json is gitignored in second-brain-clean (it also stores
per-session state like zoom/pan/search, which would otherwise create commit
noise). So a freshly scaffolded vault has no graph.json, and Obsidian creates
a colorless default the first time it's opened. This script applies the color
groups from graph-colors.json (next to this script) on top of whatever
graph.json currently exists at the target (or creates it if missing), without
touching any other graph settings.

Cross-platform port of restore-graph-colors.ps1 (which needs PowerShell —
not installed by default on macOS/Linux). Prefer this one unless you're
already in a pwsh session.

Usage:
    python3 restore_graph_colors.py <path-to-vault>
    python3 restore_graph_colors.py .                    # vault = cwd
    python3 restore_graph_colors.py ../../some-brain

Then fully quit and reopen Obsidian on that vault (a running Obsidian instance
won't pick up the file change until it's reloaded).

If colors ever look grey again (e.g. after Obsidian resets the file on some
future "first open"), just re-run this script the same way.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    vault = Path(sys.argv[1]).resolve()
    obsidian_dir = vault / ".obsidian"
    if not obsidian_dir.is_dir():
        print(f"No .obsidian/ found under {vault} — is this an Obsidian vault?")
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    seed_path = script_dir / "graph-colors.json"
    seed = json.loads(seed_path.read_text(encoding="utf-8"))

    graph_path = obsidian_dir / "graph.json"
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    else:
        graph = {}

    graph["collapse-color-groups"] = seed["collapse-color-groups"]
    graph["colorGroups"] = seed["colorGroups"]

    graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Graph color groups applied: {graph_path}")
    print("Fully quit and reopen Obsidian on this vault to see it.")


if __name__ == "__main__":
    main()
