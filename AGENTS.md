# AGENTS.md

Conventions for this library vault, for humans and agents: one bibliography and one note per paper, cited from any number of other vaults (made from [second-brain-clean](https://github.com/mikgrasis/second-brain-clean)).

If `AGENTS.local.md` exists, read it next; it wins where the two differ.

## What lives here

- **`library.bib` is the master bibliography.** UTF-8, nothing ever dropped. Reference notes are generated from it; fix an entry in the bib, never in its note.
- **Bibkeys are the paper ID across all vaults.** Existing keys never change. New keys: first author's surname + year + first non-stopword of the title, lowercase (`kolda2009tensor`), with an `a`/`b` suffix on collision — the same rule Google Scholar uses.
- **PDFs never go into git.** The bib's `file` field points at them; a relative path resolves against `pdf_root` in `_scripts/settings.json`.
- **Boundary:** if you would cite it in a paper, it goes in `library.bib` and gets a note here. Media you only learn from goes in a citing vault's `sources/`.

## Note types

```
references/   one note per citable thing: <bibkey>.md
topics/       reading-list hubs, grown from tags
collections/  hand-curated, ordered sets: a lab, a lineage, a series, a reading list
people/       only people who matter: co-authors, supervisors, authors you follow
molecules/    your own cross-reference insights
```

Support folders: `_vocab/` (the tag vocabulary), `_reports/` (generated reports), `csl/` (citation styles), `_scripts/`, `_templates/`.

## References

- **Tiers:** `stub` (new notes) and `full` (has substantive notes, set by hand). An entry without a note is fine.
- **`kind`** comes from the bib entry type: `article`, `inproceedings`, `book`, `phdthesis`, …
- **Generated parts** are rewritten by `build_reference_notes.py`: the frontmatter between the `generated` comments, `topics`, and the block between `%% bib:start %%` and `%% bib:end %%` (citation, PDF / doi / arXiv links, abstract). Everything else is yours.
- **`studied_in`** names the vaults where a paper's understanding lives; the reference note links there instead of repeating it.

## Tags

Hierarchical (`tensors/cp`), in frontmatter `tags:`. **Pick only from `_vocab/tags.md`;** a new tag is proposed there before it's used. The bib's `keywords` field is input for choosing tags, never copied in directly.

## Topic hubs

Hubs are reading lists that grow out of tags: Dataview queries over `covers:`, never hand-written member lists.

- A **hub** is a top-level tag whose subtree reaches **~25 references**; a **sub-hub** a deeper tag reaching **~15**, naming its hub in `parent:`. Tags with fewer than 3 references are merge candidates.
- `tag_report.py` proposes hubs in `_reports/hub-report.md`; a hub is created only on approval.
- Organizing tags (`by-dataset`, `by-method`) never become hubs; list them in `AXES` in `tag_report.py`.
- **Graph edges come from `topics:`:** the builder links each note to the most specific hubs its tags fall under. After adding a hub or changing `covers:`, rerun it.

## Collections

A hand-curated set with its own identity (`kind`: lab, lineage, series, reading-list, ledger). The ordered, annotated member list *is* the content, so collections may list members by hand.

## Cited in

`cited_in.py` adds a collapsed "Cited in" list after each note's bib block, from every vault in `citing_vaults` (`_scripts/settings.json`). Citing vaults write `[@key]` and build their References with `build_references.py --library <path to this vault>`.

## Scripts

| Script | Does |
|---|---|
| `build_reference_notes.py` | creates and refreshes reference notes (`--add KEY …`, `--all`, `--check`) |
| `cited_in.py` | writes the "Cited in" lists (`--check`) |
| `tag_report.py` | tag counts and hub proposals → `_reports/hub-report.md` |
| `check_dois.py` | every DOI and arXiv ID against Crossref / arXiv → `_reports/doi-check.md` |
| `bib.py`, `latex.py` | shared: format-preserving bib reader, LaTeX accent decoder |

Python 3 with PyYAML; `check_dois.py` also needs `curl`.

## Frontmatter

```yaml
# Reference
type: reference
bibkey: kolda2009tensor
tier: stub              # stub | full
# generated from library.bib: edit the bib, not these
title: ""
authors: []             # "Surname, Given"
year: 2009
kind: article
venue: ""
doi: ""
arxiv: ""
pdf: ""                 # file:// URL
# end generated
tags: []
# generated from tags and the hubs' covers: edit tags, not topics
topics: []
studied_in: []
collections: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
visibility: private

# Topic
type: topic
title: ""
parent: ""              # [[Hub]], sub-hubs only
covers: []              # tags this hub lists, children included
created: YYYY-MM-DD
updated: YYYY-MM-DD
visibility: private

# Collection
type: collection
title: ""
kind: lineage           # lab | lineage | series | reading-list | ledger
created: YYYY-MM-DD
updated: YYYY-MM-DD
visibility: private

# Person
type: person
title: ""               # full name
affiliation: ""
relation: followed      # co-author | supervisor | student | followed
created: YYYY-MM-DD
updated: YYYY-MM-DD
visibility: private
```

Molecules use second-brain-clean's frontmatter and kinds.

## visibility

Default `private`: a library reflects unpublished research directions. `shared` / `restricted` as in second-brain-clean.

## Conventions

- Wikilinks (`[[ ]]`) inside the vault. Link a reference by its bibkey: `[[kolda2009tensor]]`.
- Delete the example (`kolda2009tensor`, `Tensors`, the sample tags) once the library has real entries.
