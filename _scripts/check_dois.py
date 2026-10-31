"""Check every DOI and arXiv ID in library.bib against Crossref / arXiv.

Reference managers sometimes merge an entry with another paper and carry that
paper's DOI or arXiv ID along. This looks each
identifier up and compares the registered title, first author and year with
the bib entry, writing _reports/doi-check.md.

    python3 _scripts/check_dois.py [CACHE_DIR]

Read-only against library.bib. Responses are cached (default .cache/doi,
gitignored) so re-runs only fetch what is new. Uses curl, not urllib: some
Python installs ship without CA certificates. Flags you've reviewed go in
_reports/doi-accepted.txt (key<TAB>kind per line) and aren't listed again.
"""
import json
import re
import time
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import bib
from latex import decode

ROOT = Path(__file__).resolve().parent.parent
NS = {"a": "http://www.w3.org/2005/Atom"}


def norm(s):
    s = decode(s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\$[^$]*\$", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:                      # subtitle present on one side only
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    return max(SequenceMatcher(None, a, b).ratio(), len(ta & tb) / max(1, min(len(ta), len(tb))))


def clean_doi(d):
    d = d.strip().replace("{_}", "_").replace("{", "").replace("}", "").replace("\\_", "_")
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    return d.split()[0] if d else ""


def curl(url):
    r = subprocess.run(["curl", "-sL", "-m", "40", "-A", "paper-brain doi-check (curl)", url],
                       capture_output=True)
    return r.stdout


def crossref(doi, cache):
    f = cache / ("crossref_" + re.sub(r"[^\w.-]", "_", doi) + ".json")
    if not f.exists():
        msg = {"_status": "error"}
        for attempt in range(5):             # Crossref throttles bursts; back off and retry
            r = subprocess.run(["curl", "-sL", "-m", "40", "-w", "\n%{http_code}", "-A",
                                "paper-brain doi-check (curl)", "https://api.crossref.org/works/" + doi],
                               capture_output=True)
            body, _, code = r.stdout.rpartition(b"\n")
            if code == b"200":
                msg = json.loads(body)["message"]
                break
            if code == b"404":
                msg = {"_status": "not-found"}
                break
            time.sleep(2 ** attempt)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(msg))
        tmp.replace(f)                       # atomic: no half-written cache files
    try:
        return json.loads(f.read_text())
    except ValueError:                       # a corrupt file from an earlier run
        f.unlink()
        return crossref(doi, cache)


def arxiv_file(cache, aid):
    return cache / ("arxiv_" + aid.replace("/", "_") + ".json")   # old-style IDs contain a slash


def arxiv_batch(ids, cache):
    """Fetch arXiv records in small batches; an ID missing from a response is retried
    alone before it counts as not found (the API returns empty feeds when throttled)."""
    def fetch(chunk):
        raw = curl("https://export.arxiv.org/api/query?max_results=50&id_list=" + ",".join(chunk))
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return set()
        got = set()
        for e in root.findall("a:entry", NS):
            aid = re.sub(r"^https?://arxiv\.org/abs/", "", e.find("a:id", NS).text)
            aid = re.sub(r"v\d+$", "", aid)
            t, au, pub = e.find("a:title", NS), e.find("a:author/a:name", NS), e.find("a:published", NS)
            summ = e.find("a:summary", NS)
            if t is None or aid not in chunk:
                continue
            arxiv_file(cache, aid).write_text(json.dumps({
                "title": " ".join(t.text.split()), "author": au.text if au is not None else "",
                "year": pub.text[:4] if pub is not None else "",
                "summary": " ".join(summ.text.split()) if summ is not None else ""}))
            got.add(aid)
        return got

    todo = [i for i in ids if not arxiv_file(cache, i).exists()]
    for k in range(0, len(todo), 20):
        chunk = todo[k:k + 20]
        missing = set(chunk) - fetch(chunk)
        time.sleep(3)
        for i in missing:                    # retry singly, then give up
            for attempt in range(3):
                if fetch([i]):
                    break
                time.sleep(3 * (attempt + 1))
            else:
                arxiv_file(cache, i).write_text(json.dumps({"_status": "not-found"}))
    return {i: json.loads(arxiv_file(cache, i).read_text()) for i in ids}


def first_surname(author_field):
    first = re.split(r"\s+and\s+", author_field or "")[0]
    last = first.split(",")[0] if "," in first else (first.split()[-1] if first.split() else "")
    return norm(last)


def main():
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".cache" / "doi"
    cache.mkdir(parents=True, exist_ok=True)
    _, entries = bib.read(ROOT / "library.bib")
    notes = {p.stem for p in (ROOT / "references").glob("*.md")}

    with_doi = [(e, clean_doi(e.get("doi"))) for e in entries if e.get("doi").strip()]
    malformed = [(e, d) for e, d in with_doi if not d.startswith("10.")]
    valid = [(e, d) for e, d in with_doi if d.startswith("10.")]
    unique = sorted({d for _, d in valid})
    with ThreadPoolExecutor(3) as pool:
        fetched = dict(zip(unique, pool.map(lambda d: crossref(d, cache), unique)))
    records = [fetched[d] for _, d in valid]

    arx = {}
    for e in entries:
        a = (e.get("arxivId") or (e.get("eprint") if e.get("archivePrefix").lower() == "arxiv" else "")).strip()
        a = re.sub(r"v\d+$", "", re.sub(r"^arxiv:\s*", "", a, flags=re.I))
        if re.fullmatch(r"\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7}", a):
            arx[e.key] = (e, a)
    arecs = arxiv_batch(sorted({a for _, a in arx.values()}), cache)

    rows, stats = [], {"doi_ok": 0, "doi_mismatch": 0, "doi_unresolved": 0, "arxiv_ok": 0, "arxiv_mismatch": 0}

    def judge(e, kind, ident, title, author, year):
        sim = similarity(e.get("title"), title)
        same_author = bool(author) and first_surname(e.get("author")) in norm(author).split()
        if sim >= 0.8 or (sim >= 0.6 and same_author):
            return None
        return {"key": e.key, "note": e.key in notes, "kind": kind, "id": ident, "sim": round(sim, 2),
                "bib_title": norm(e.get("title"))[:90], "registered": norm(title)[:90],
                "registered_by": f"{author} {year}".strip()}

    for (e, d), m in zip(valid, records):
        if m.get("_status"):
            stats["doi_unresolved"] += 1
            rows.append({"key": e.key, "note": e.key in notes, "kind": "doi-unresolved", "id": d, "sim": "",
                         "bib_title": norm(e.get("title"))[:90], "registered": m["_status"], "registered_by": ""})
            continue
        title = (m.get("title") or [""])[0]
        if m.get("subtitle"):
            title += " " + m["subtitle"][0]
        author = (m.get("author") or [{}])[0].get("family", "")
        year = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0] or ""
        r = judge(e, "doi", d, title, author, year)
        stats["doi_mismatch" if r else "doi_ok"] += 1
        if r:
            rows.append(r)
    for key, (e, a) in arx.items():
        m = arecs.get(a, {})
        if m.get("_status"):
            rows.append({"key": key, "note": key in notes, "kind": "arxiv-unresolved", "id": a, "sim": "",
                         "bib_title": norm(e.get("title"))[:90], "registered": "not found", "registered_by": ""})
            continue
        r = judge(e, "arxiv", a, m.get("title", ""), m.get("author", ""), m.get("year", ""))
        stats["arxiv_mismatch" if r else "arxiv_ok"] += 1
        if r:
            rows.append(r)

    accepted_file = ROOT / "_reports" / "doi-accepted.txt"
    accepted = {tuple(l.split("\t")) for l in accepted_file.read_text().splitlines()
                if l and not l.startswith("#")} if accepted_file.exists() else set()
    n_accepted = sum(1 for r in rows if (r["key"], r["kind"]) in accepted)
    rows = [r for r in rows if (r["key"], r["kind"]) not in accepted]
    rows.sort(key=lambda r: (r["kind"], r["sim"] if r["sim"] != "" else 9))
    out = ["# DOI and arXiv check", "",
           "Generated by `_scripts/check_dois.py`: each identifier's registered title (Crossref / arXiv) "
           "compared with the bib title. Low similarity usually means the reference manager attached another paper's "
           "identifier; some are only a book/chapter or preprint/journal title difference. Review before fixing.", "",
           f"- DOIs: {len(with_doi)} ({stats['doi_ok']} match, {stats['doi_mismatch']} mismatch, "
           f"{stats['doi_unresolved']} unresolved, {len(malformed)} malformed)",
           f"- arXiv IDs: {len(arx)} ({stats['arxiv_ok']} match, {stats['arxiv_mismatch']} mismatch)",
           f"- {n_accepted} flags reviewed and accepted (`_reports/doi-accepted.txt`); listed below: only new ones", "",
           "| Key | Note | Check | Identifier | Sim | Bib title | Registered title | Registered first author, year |",
           "|---|---|---|---|---|---|---|---|"]
    out += [f"| `{r['key']}` | {'✓' if r['note'] else ''} | {r['kind']} | `{r['id']}` | {r['sim']} | "
            f"{r['bib_title']} | {r['registered']} | {r['registered_by']} |" for r in rows]
    out += ["", f"## Malformed DOIs: {len(malformed)}", ""] + [f"- `{e.key}`: `{e.get('doi')}`" for e, _ in malformed]
    (ROOT / "_reports").mkdir(exist_ok=True)
    (ROOT / "_reports" / "doi-check.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(stats, "malformed", len(malformed), "-> _reports/doi-check.md")


if __name__ == "__main__":
    main()
