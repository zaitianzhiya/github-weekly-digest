---
type: category-moc
category: AI
total_projects: 4
---

# AI

> 4 projects

```dataview
TABLE language, stars, confidence_grade
FROM "output/cards"
WHERE contains(categories, "AI")
SORT confidence_score DESC
```

## Projects

- [[openai--codex-security|openai/codex-security]] — OpenAI's Codex Security CLI and TypeScript SDK for finding, validating, and fixing security vulnerabilities. npm: https://www.npmjs.com/package/@openai/codex-security
- [[GoogleChrome--modern-web-guidance-src|GoogleChrome/modern-web-guidance-src]] — Keep your coding agent up to date with the latest web best practices
- [[QwenLM--qwen-code|QwenLM/qwen-code]] — An open-source AI coding agent that lives in your terminal.
- [[alibaba--open-code-review|alibaba/open-code-review]] — Secure, fast, efficient, battle-tested at Alibaba's scale. Hybrid architecture code review tool: deterministic pipelines + LLM Agent, precise line-level comments, built-in multi-language ruleset (NPE, thread-safety, XSS, SQL injection), OpenAI &amp; Anthropic compatible.