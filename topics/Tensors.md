---
type: topic
title: "Tensors"
parent: ""
covers: ["tensors"]
created: 2026-10-31
updated: 2026-10-31
visibility: private
---

# Tensors

Tensor algebra, decompositions and their applications. **Excludes:** plain matrix methods.

## Sub-hubs

```dataview
LIST FROM "topics" WHERE parent = this.file.link SORT file.name ASC
```

## Reading list

```dataview
TABLE WITHOUT ID
  link(file.link, title) AS "Title",
  choice(!authors, "", choice(length(authors) = 1, split(authors[0], ",")[0], choice(length(authors) = 2, split(authors[0], ",")[0] + " & " + split(authors[1], ",")[0], split(authors[0], ",")[0] + " et al."))) AS "Author",
  year AS "Year",
  choice(pdf, elink(pdf, "PDF"), "") AS "PDF"
FROM "references"
WHERE any(map(this.covers, (c) => any(map(tags, (t) => t = c OR startswith(t, c + "/")))))
SORT year DESC
```
