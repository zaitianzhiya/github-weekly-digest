---
type: category-moc
category: AI
total_projects: 2
---

# AI

> 2 projects

```dataview
TABLE language, stars, confidence_grade
FROM "output/cards"
WHERE contains(categories, "AI")
SORT confidence_score DESC
```

## Projects

- [[Gaurav-Gosain--tuios|Gaurav-Gosain/tuios]] — A terminal window manager that knows what your agents are doing. Tiling panes, workspaces, sessions that survive restarts, and one Inbox for every coding agent.
- [[cloudflare--cloudflare-os|cloudflare/cloudflare-os]] — Agent workspace built on Cloudflare Workers for creating documents, building apps, and running agents with your company’s context and systems.