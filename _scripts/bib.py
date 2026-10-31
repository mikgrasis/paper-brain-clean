"""Minimal, format-preserving reader/writer for library.bib.

Every entry starts at column 0 with `@type{key,` (Mendeley, JabRef, Zotero and
Google Scholar exports all do). Field values may be braced (and span lines),
quoted, or bare (`year = 2009`). Entries are kept as raw text so a
rewrite only touches what a script deliberately changes, and git diffs stay
readable.
"""
import re
from pathlib import Path

HEAD = re.compile(r"^@(\w+)\{([^,\s]*),\s*$")


class Entry:
    def __init__(self, etype, key, fields, raw):
        self.type = etype          # as written, e.g. "article"
        self.key = key
        self.fields = fields       # list of [name, value] in file order; value is the brace content
        self.raw = raw             # original text, used when the entry is untouched
        self.dirty = False

    def get(self, name, default=""):
        for n, v in self.fields:
            if n.lower() == name.lower():
                return v
        return default

    def set(self, name, value):
        for f in self.fields:
            if f[0].lower() == name.lower():
                f[1] = value
                self.dirty = True
                return
        self.fields.append([name, value])
        self.fields.sort(key=lambda f: f[0].lower())   # keep fields alphabetical
        self.dirty = True

    def drop(self, name):
        before = len(self.fields)
        self.fields = [f for f in self.fields if f[0].lower() != name.lower()]
        self.dirty |= len(self.fields) != before

    def rekey(self, key):
        self.key = key
        self.dirty = True

    def text(self):
        if not self.dirty:
            return self.raw
        body = ",\n".join(f"{n} = {{{v}}}" for n, v in self.fields)
        return f"@{self.type}{{{self.key},\n{body}\n}}\n"


def _parse_fields(body):
    fields, i, n = [], 0, len(body)
    while i < n:
        m = re.compile(r"\s*([\w-]+)\s*=\s*").match(body, i)
        if not m or m.end() >= n:
            break
        name, j = m.group(1), m.end()
        if body[j] == "{":
            j, depth = j + 1, 1
            while depth:
                c = body[j]
                if c == "\\":
                    j += 2
                    continue
                depth += c == "{"
                depth -= c == "}"
                j += 1
            value = body[m.end() + 1:j - 1]
        elif body[j] == '"':
            k = j + 1
            while body[k] != '"' or body[k - 1] == "\\":
                k += 1
            value, j = body[j + 1:k], k + 1
        else:
            k = j
            while k < n and body[k] not in ",\n":
                k += 1
            value, j = body[j:k].strip(), k
        fields.append([name, value])
        i = j
        while i < n and body[i] in ",\n\r \t":
            i += 1
    return fields


def read(path):
    """Return (preamble_text, [Entry])."""
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    starts = [i for i, l in enumerate(lines) if HEAD.match(l)]
    preamble = "".join(lines[:starts[0]]) if starts else "".join(lines)
    entries = []
    for a, b in zip(starts, starts[1:] + [len(lines)]):
        raw = "".join(lines[a:b])
        m = HEAD.match(lines[a])
        inner = "".join(lines[a + 1:b]).rstrip()
        assert inner.endswith("}"), f"entry at line {a + 1} does not close"
        entries.append(Entry(m.group(1), m.group(2), _parse_fields(inner[:-1]), raw))
    return preamble, entries


def write(path, preamble, entries):
    Path(path).write_text(preamble + "".join(e.text() for e in entries), encoding="utf-8")
