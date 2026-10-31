---
type: person
title: "{{title}}"
affiliation: ""
relation: followed
created: {{date:YYYY-MM-DD}}
updated: {{date:YYYY-MM-DD}}
visibility: private
---

# {{title}}

Why this person matters.

## References

```dataview
LIST FROM "references" WHERE contains(authors, this.title) SORT year DESC
```
