# CLAUDE.md

This file provides guidance to Claude Code (claude.ai) when working with code in this repository.

## Project overview

**GitHub Weekly Digest** is an automated pipeline that collects GitHub trending repositories daily, enriches them with API data, generates AI-powered Chinese summaries (via Gemini), and publishes structured Markdown reports to a GitHub Pages site. The workflow runs entirely on GitHub Actions with zero server infrastructure.

Key numbers: 3 information sources (GitHub Trending + OpenGithubs + Ruanyf Weekly), 5-dimension scoring, ~12,000-character weekly reports with AI summary + deep analysis.

## Architecture

```
Multi-source Collectors → Dedup/Merge → Quality Filter → 5-dim Scorer → Gemini AI (summary + deep analysis) → Markdown Renderer → GitHub Actions commit/push
```

**Entry point for GitHub Actions:** `run.py --mode {daily|weekly}`
**Local testing:** `python verify.py` or `python verify_phase2.py`

## Key modules

| Module | Path | Purpose |
|--------|------|---------|
| Collectors | `src/collectors/` | Scrape GitHub Trending, HN, citation sources (OpenGithubs, Ruanyf) |
| Filters | `src/filters/` | Dedup (JSON state file), quality gates, 5-dim scoring with confidence grades |
| AI | `src/ai/` | LLM client (multi-provider), daily summarizer, weekly deep analyzer, feedback loader |
| Render | `src/render/` | Markdown weekly reports, Obsidian-compatible project cards, category indexes |
| Config | `config/` | YAML: sources (Tier 1/2), keywords (positive/negative), quality thresholds + scoring weights |
| Prompts | `prompts/` | Editable Markdown files that define AI behavior (daily-summary, weekly-deep, taxonomy) |

## Data flow

1. **Collect**: `GitHubTrendingCollector` scrapes `github.com/trending?since=weekly`, enriches via GitHub API (stars, license, pushed_at), fetches README (6000 chars). `CitationCollector` pulls from OpenGithubs, Ruanyf Weekly, GitHubDaily.
2. **Filter**: `QualityFilter` checks: non-fork, license present, active (<90 days), README ≥200 chars. Graceful — missing data passes through.
3. **Score**: `Scorer` computes confidence (cross-ecosystem citation weighting) + quality (star growth 25%, multi-source 25%, documentation 20%, community 15%, novelty 15%).
4. **AI**: `DailySummarizer` sends top 20 repos + README snippets to Gemini 2.5 Flash with structured Chinese prompt (no bare jargon, 3-second hooks, two-layer reading). `DeepAnalyzer` does per-repo deep analysis + cross-repo trend discovery for weekly mode.
5. **Render**: `MarkdownRenderer` generates weekly report + individual Obsidian cards (with Dataview frontmatter) + category index pages. Table columns now include descriptions and source names.

## Configuration patterns

- **Sources** (`config/sources.yml`): Tier 1 (primary: trending, search, HN, RSS) vs Tier 2 (citation: OpenGithubs, Ruanyf, GitHubDaily). Each source has an ecosystem tag for cross-ecosystem independence weighting.
- **Keywords** (`config/keywords.yml`): Positive keywords boost category weighting; negative keywords (crypto, blockchain) demote. `tracked_authors` list for priority enrichment.
- **Quality** (`config/quality.yml`): All thresholds and scoring weights are tunable. `manual_multiplier` (0.5-2.0) allows human override on individual records.

## Prompt engineering

The system's "brain" lives in `prompts/*.md` — edited without code changes. Key rules baked into the prompts:

- **No naked jargon**: Every acronym/term must be translated to concrete benefit (e.g., "MVCC" → "multiple writers commit simultaneously without locking")
- **3-second hooks**: One sentence per repo saying "what it is + why you'd care"
- **Two-layer reading**: Hook layer for scanning + detail layer for deep reading
- **Custom topics**: Configurable lists for "explain in detail" and "keep short/skip" in daily-summary.md

## Important implementation details

- **Imports**: All modules use absolute imports (`from src.collectors.base import ...`) for compatibility with `run.py` at repo root. The old relative import approach caused runtime failures in Actions.
- **Null bytes**: Network drive writes (Z: drive) can inject null bytes into files. Always write Python source via bash heredoc (`cat > file << 'PYEOF'`) to avoid corruption. YAML workflow files are particularly sensitive.
- **GitHub Actions secrets**: Uses `GH_TOKEN` (not `GITHUB_TOKEN`) for API enrichment + push access. `GEMINI_API_KEY` for AI summaries. The checkout step must include `token: ${{ secrets.GH_TOKEN }}` for push to work.
- **Concurrency control**: Both workflows use `concurrency: group: {daily|weekly}-digest` with `cancel-in-progress: false` to prevent duplicate runs during GitHub scheduler issues.
- **Cron times**: Use off-peak minutes (daily: `23 8 * * *`, weekly: `37 10 * * 1`) to avoid GitHub's scheduler congestion at round hours. UTC, so 8:23 UTC = 16:23 Beijing time.
- **git add -f**: The `.gitignore` excludes `output/*`, so workflow commit step must use `git add -f output/` to force-include generated files.
- **Graceful degradation**: If Gemini API is unavailable (503), the pipeline falls back to data-only reports without AI summaries — never blocks on LLM failure.
- **Feedback loop**: Reports include a feedback section. Weekly `feedback/*.md` files can contain tier corrections and permanent rules that get injected into AI prompts via `FeedbackLoader`.

## Local development

```bash
# Install
pip install -r requirements.txt

# Quick test (no AI, just collect + pipeline + render)
python verify.py

# AI test (requires GEMINI_API_KEY)
export GEMINI_API_KEY="..."
python verify_phase3.py

# Run manually
export GH_TOKEN="ghp_..." GEMINI_API_KEY="..."
python run.py --mode daily   # Tier 1 only, fast summary
python run.py --mode weekly  # All tiers + deep analysis
```

## Deployment

Deployed at https://github.com/zaitianzhiya/github-weekly-digest. Three workflows active:

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| Daily Collection | UTC 8:23 daily | Tier 1 collect + AI summary + commit |
| Weekly Publish | UTC 10:37 Mondays | Full collection + deep analysis |
| Watchdog | 3× Monday | Self-healing: dispatches weekly if missed |

Manual trigger: GitHub Actions tab → select workflow → "Run workflow".

Reports published to `output/weekly/YYYY/YYYY-Www.md`, cards to `output/cards/`, indexes to `output/categories/`.
