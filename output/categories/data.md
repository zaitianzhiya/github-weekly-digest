---
type: category-moc
category: data
total_projects: 1
---

# data

> 1 projects

```dataview
TABLE language, stars, confidence_grade
FROM "output/cards"
WHERE contains(categories, "data")
SORT confidence_score DESC
```

## Projects

- [[alibaba--open-code-review|alibaba/open-code-review]] — Secure, fast, efficient, battle-tested at Alibaba's scale. Hybrid architecture code review tool: deterministic pipelines + LLM Agent, precise line-level comments, built-in multi-language ruleset (NPE, thread-safety, XSS, SQL injection), OpenAI &amp; Anthropic compatible.