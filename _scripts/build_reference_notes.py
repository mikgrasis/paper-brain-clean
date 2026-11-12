#!/usr/bin/env python3
"""Create or refresh reference notes, references/<bibkey>.md, from library.bib.

    python3 _scripts/build_reference_notes.py              # refresh every existing note
    python3 _scripts/build_reference_notes.py --add KEY …  # also create notes for these entries
    python3 _scripts/build_reference_notes.py --all        # a note for every entry
    python3 _scripts/build_reference_notes.py --check      # change nothing; exit 1 if a note would change
    python3 _scripts/build_reference_notes.py --root       # only write this machine's _fixups/library-root.md

Rewritten on every run: the generated frontmatter keys (title … pdf), `topics` (the most specific hubs whose
`covers:` match the note's tags), and the text between %% bib:start %% and %% bib:end %% (a citation callout
with PDF / doi / arXiv links and a collapsible abstract). Everything else — tags, tier, your notes — is kept.
New notes start as tier `stub`; set `full` by hand once a note has substantive notes.

`pdf` comes from the entry's `file` field (Mendeley, JabRef and Zotero forms, and bare Windows paths with a
drive letter). It is stored relative to `pdf_root` (a relative `file` path already is; an absolute one under
`pdf_root` is made relative), so the note reads the same on every machine. `pdf_root` is set in
_scripts/settings.json and, per machine, in the gitignored _scripts/settings.local.json (a drive letter, a mount
point, a network share). A PDF outside `pdf_root` keeps its absolute file:// URL. Without a `file` field, a
`pdf:` set by hand is kept.

Every run also writes _fixups/library-root.md (gitignored): this machine's file:// URL of `pdf_root`. The notes'
PDF links and the topic hubs read it (inline Dataview), so they open the PDF in the default application.
`--root` writes only that note.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

import bib
from latex import decode

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "references"


def load_settings():
    """settings.json, then the gitignored settings.local.json on top (per-machine paths)."""
    out = {}
    for name in ("settings.json", "settings.local.json"):
        f = ROOT / "_scripts" / name
        if f.exists():
            out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


SETTINGS = load_settings()
PDF_ROOT = Path(SETTINGS["pdf_root"]).expanduser() if SETTINGS.get("pdf_root") else None
GENERATED = ["title", "authors", "year", "kind", "venue", "doi", "arxiv", "pdf"]
START, END = "%% bib:start: generated from library.bib, edit the bib %%", "%% bib:end %%"
BLOCK = re.compile(r"%% bib:start[^%]*%%.*?%% bib:end %%", re.S)
KIND_LABEL = {"article": "Journal article", "inproceedings": "Conference paper", "conference": "Conference paper",
              "book": "Book", "inbook": "Book chapter", "incollection": "Book chapter", "chapter": "Book chapter",
              "phdthesis": "PhD thesis", "mastersthesis": "Master's thesis", "techreport": "Technical report",
              "misc": "Misc", "unpublished": "Unpublished", "repository": "Repository"}


def clean(s):
    s = decode(s)
    s = re.sub(r"\\([&%_#])", r"\1", s)            # LaTeX-escaped & % _ #
    s = s.replace("---", "—").replace("--", "–")
    s = re.sub(r"(?<!\\)[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def root_url():
    """file:// URL of pdf_root with a trailing slash (works for drive letters and UNC shares), or ""."""
    return PDF_ROOT.as_uri().rstrip("/") + "/" if PDF_ROOT and PDF_ROOT.is_absolute() else ""


def write_library_root():
    """_fixups/library-root.md: this machine's file:// URL of pdf_root, read by the PDF links."""
    url = root_url()
    out = ROOT / "_fixups" / "library-root.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        f'---\nurl: "{url}"\n---\n\n'
        "Machine-specific, gitignored. Written by `_scripts/build_reference_notes.py` from `pdf_root` in "
        "`_scripts/settings.json` / `settings.local.json`; read by the notes' PDF links and the topic hubs.\n",
        encoding="utf-8", newline="\n")
    return url


def pdf_path(e):
    """The entry's first PDF: relative to pdf_root when it lies under it, else an absolute file:// URL; "" if none."""
    for part in e.get("file").split(";"):
        part = part.strip()
        if re.match(r"^[A-Za-z]:[\\/]", part):           # a bare Windows path (Zotero, Better BibTeX): C:\...\x.pdf
            m = re.match(r"^(.+?\.pdf)(?::[^:]*)?$", part, re.I)
        else:                                             # name:path:type (Mendeley, JabRef, Zotero) or a bare path
            m = re.match(r"^(?:[^:]*:)?(.+?\.pdf)(?::[^:]*)?$", part, re.I)
        if not m:
            continue
        p = m.group(1).replace("\\:", ":").replace("\\\\", "\\")   # unescape C\: and doubled backslashes
        if p.startswith(("Users/", "Volumes/", "home/")):
            p = "/" + p                                   # Mendeley drops the leading slash
        path = Path(p)
        if not path.is_absolute():
            return path.as_posix()                        # recorded relative to pdf_root
        if PDF_ROOT:
            try:
                return path.relative_to(PDF_ROOT).as_posix()
            except ValueError:
                pass
        return path.as_uri()                              # outside pdf_root: machine-specific, kept as before
    return ""


def pdf_link():
    """Inline Dataview link from the note's own `pdf` field: a relative path resolves against this machine's
    pdf_root (_fixups/library-root.md), a file:// URL is used as it is."""
    enc = 'replace(replace(replace(replace(this.pdf, " ", "%20"), "[", "%5B"), "]", "%5D"), ",", "%2C")'
    return ('`= elink(choice(startswith(this.pdf, "file:"), this.pdf, '
            f'[[_fixups/library-root]].url + {enc}), "PDF")`')


def meta(e, old_pdf):
    t = e.type.lower()
    venue = e.get("journal") or e.get("booktitle") or (e.get("school") if "thesis" in t else "") \
        or e.get("institution") or e.get("publisher")
    arxiv = e.get("arxivId") or (e.get("eprint") if e.get("archivePrefix").lower() == "arxiv" else "")
    year = re.sub(r"\D", "", e.get("year"))[:4]
    return {
        "title": clean(e.get("title")),
        "authors": [clean(a) for a in re.split(r"\s+and\s+", e.get("author")) if a.strip()],
        "year": int(year) if year else None,
        "kind": t,
        "venue": clean(venue),
        "doi": e.get("doi").strip(),
        "arxiv": arxiv.strip(),
        "pdf": pdf_path(e) or old_pdf or "",
    }


def body(m, e):
    authors = m["authors"]
    who = "; ".join(authors) if len(authors) <= 8 else "; ".join(authors[:6]) + f"; … ({len(authors)} authors)"
    kind = KIND_LABEL.get(m["kind"], m["kind"])
    where = ", ".join(str(x) for x in (m["venue"], m["year"]) if x)
    links = [pdf_link()] if m["pdf"] else []
    links += [f"[doi](https://doi.org/{m['doi']})"] if m["doi"] else []
    links += [f"[arXiv](https://arxiv.org/abs/{m['arxiv']})"] if m["arxiv"] else []
    lines = [START, f"> [!cite] {who}", f"> {where} · {kind}" if where else f"> {kind}"]
    if links:
        lines.append("> " + " · ".join(links))
    abstract = clean(e.get("abstract"))
    if abstract:
        lines += ["", "> [!abstract]- Abstract", "> " + abstract]
    lines.append(END)
    return "\n".join(lines)


def load_hubs():
    """name -> (covers, parent name) from topics/*.md."""
    hubs = {}
    for p in (ROOT / "topics").glob("*.md"):
        m = re.match(r"---\n(.*?)\n---\n", p.read_text(encoding="utf-8"), re.S)
        fm = yaml.safe_load(m.group(1)) if m else {}
        parent = re.sub(r"^\[\[|\]\]$", "", fm.get("parent") or "") or None
        hubs[p.stem] = (fm.get("covers") or [], parent)
    return hubs


def hub_links(tags, hubs):
    """Wikilinks to the most specific hubs covering any of the tags (a sub-hub, not also its parent)."""
    hit = {h for h, (covers, _) in hubs.items() if any(t == c or t.startswith(c + "/") for t in tags for c in covers)}
    def ancestors(h):
        seen, p = set(), hubs[h][1]
        while p in hubs and p not in seen:
            seen.add(p)
            p = hubs[p][1]
        return seen
    covered = set().union(*(ancestors(h) for h in hit)) if hit else set()
    return [f"[[{h}]]" for h in sorted(hit - covered)]


def frontmatter(fm):
    order = ["type", "bibkey", "tier"] + GENERATED + ["tags", "topics", "studied_in", "collections", "created", "updated", "visibility"]
    out = ["---"]
    for k in order + [k for k in fm if k not in order]:
        if k not in fm:
            continue
        if k == "title":
            out.append("# generated from library.bib: edit the bib, not these")
        if k == "topics":
            out.append("# generated from tags and the hubs' covers: edit tags, not topics")
        v = fm[k]
        out.append(f"{k}: {json.dumps(v, ensure_ascii=False, default=lambda o: o.isoformat()) if v is not None else ''}")   # Obsidian rewrites quoted dates as YAML dates
        if k == "pdf":
            out.append("# end generated")
    return "\n".join(out + ["---"])


def main():
    if "--root" in sys.argv:
        print(write_library_root() or "pdf_root not set or not absolute: url left empty")
        return
    check = "--check" in sys.argv
    add = set(sys.argv[sys.argv.index("--add") + 1:]) if "--add" in sys.argv else set()
    _, entries = bib.read(ROOT / "library.bib")
    if "--all" in sys.argv:
        add = {e.key for e in entries}
    hubs, today = load_hubs(), date.today().isoformat()
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    OUT.mkdir(exist_ok=True)
    for e in entries:
        path = OUT / f"{e.key}.md"
        if not path.exists() and e.key not in add:
            continue
        if path.exists():
            text = path.read_text(encoding="utf-8")
            m_fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
            fm, rest = (yaml.safe_load(m_fm.group(1)) or {}), text[m_fm.end():]
        else:
            text, fm = None, {}
        m = meta(e, fm.get("pdf"))
        if text is None:
            rest = f"\n# {m['title']}\n\n{START}\n{END}\n\n## Notes\n"
        new_fm = {"type": "reference", "bibkey": e.key, "tier": fm.get("tier") or "stub", **m,
                  "tags": fm.get("tags") or [], "topics": [],
                  "studied_in": fm.get("studied_in") or [], "collections": fm.get("collections") or [],
                  "created": fm.get("created") or today, "updated": fm.get("updated") or today,
                  "visibility": fm.get("visibility") or "private"}
        new_fm["topics"] = hub_links(new_fm["tags"], hubs)
        for k, v in fm.items():
            new_fm.setdefault(k, v)
        rest = BLOCK.sub(lambda _: body(m, e), rest)
        new = frontmatter(new_fm) + "\n" + rest
        if new == text:
            counts["unchanged"] += 1
            continue
        if text is not None:
            new_fm["updated"] = today
            new = frontmatter(new_fm) + "\n" + rest
        counts["updated" if text is not None else "created"] += 1
        if not check:
            path.write_text(new, encoding="utf-8", newline="\n")
    print(counts)
    if not check:
        write_library_root()
    sys.exit(1 if check and (counts["created"] or counts["updated"]) else 0)


if __name__ == "__main__":
    main()
