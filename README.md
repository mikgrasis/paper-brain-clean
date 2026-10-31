# Paper Brain (clean)

An Obsidian library vault: one BibTeX file, one note per paper, reading-list hubs grown from tags, and a "Cited in" list of every note that cites a paper — across all the vaults you write in. The companion of [second-brain-clean](https://github.com/mikgrasis/second-brain-clean), for you and AI agents alike. Conventions are in `AGENTS.md`.

Plugins: Dataview and Templater. Scripts: Python 3 with PyYAML.

## Start

1. Open this folder in [Obsidian](https://obsidian.md) as a vault and enable the community plugins.
2. Replace `library.bib` with your own export (Zotero, JabRef, Mendeley and Google Scholar all work).
3. Create notes for the papers you care about: `python3 _scripts/build_reference_notes.py --add <bibkey> …` (or `--all`).
4. Tag them from `_vocab/tags.md`; `python3 _scripts/tag_report.py` proposes hubs once tags fill up.
5. In each citing vault, build References against this library: `python3 _scripts/build_references.py --bib <path to this vault>/library.bib`. List those vaults in `_scripts/settings.json`, then run `python3 _scripts/cited_in.py` here.

The example — [[kolda2009tensor]] in the hub [[Tensors]] — shows the shape. Delete it once you've started.

## Graph colors

`.obsidian/graph.json` is not tracked. Restore the color groups once after cloning:

```sh
python3 _scripts/restore_graph_colors.py .
```
