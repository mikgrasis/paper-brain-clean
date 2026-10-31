---
type: topic
title: "{{title}}"
parent: ""
covers: []
created: {{date:YYYY-MM-DD}}
updated: {{date:YYYY-MM-DD}}
visibility: private
---

# {{title}}

Scope in one line. **Excludes:** what belongs elsewhere.

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
