"""Markdown renderer - weekly report, project cards, category index."""

from datetime import datetime
from pathlib import Path
from src.collectors.base import RepoRecord


class MarkdownRenderer:
    """Generate Markdown output: weekly reports, Obsidian cards, and category indexes."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _source_names(record):
        """Get unique source names as a comma-separated string."""
        names = []
        seen = set()
        for c in record.citations:
            if c.source_name not in seen:
                seen.add(c.source_name)
                names.append(c.source_name)
        return ", ".join(names) if names else "-"

    @staticmethod
    def _short_desc(record, maxlen=60):
        """Get a shortened description for table cells."""
        desc = record.description or ""
        if len(desc) > maxlen:
            desc = desc[:maxlen-3] + "..."
        return desc or "-"

    def render_weekly_report(self, records, daily_summary="", deep_analysis="", stats=None):
        now = datetime.utcnow()
        week_str = now.strftime("%Y-W%V")
        week_start = now.strftime("%Y.%m.%d")

        lines = [
            "---",
            f"date: {now.strftime('%Y-%m-%d')}",
            "type: weekly-moc",
            f"week_range: {week_start}",
            f"total_projects: {len(records)}",
            "---",
            "",
            f"# GitHub 周报 | {week_start}",
            "",
            f"> 本期共收录 **{len(records)}** 个项目",
            f"> 生成时间: {now.strftime('%Y-%m-%d %H:%M')} UTC",
            "",
            "---",
            "",
        ]

        # AI daily summary
        if daily_summary:
            lines.append("## AI 快速摘要")
            lines.append("")
            lines.append(daily_summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        # ---- Top N table (WITH description and source names) ----
        top_n = min(len(records), 20)
        lines.append(f"## Top {top_n} 项目")
        lines.append("")
        lines.append("| # | 项目 | 描述 | 语言 | 本周 ⭐ | 总 ⭐ | 可信度 | 来源 |")
        lines.append("|---|------|------|------|---------|-------|--------|------|")

        for i, r in enumerate(records[:top_n], 1):
            desc = self._short_desc(r)
            sources = self._source_names(r)
            lines.append(
                f"| {i} | [{r.full_name}]({r.html_url}) | {desc} | {r.language or '-'} | "
                f"+{r.weekly_growth:,} | {r.stars:,} | "
                f"{r.confidence_grade}({r.confidence_score:.0f}) | {sources} |"
            )

        lines.extend(["", "---", ""])

        # ---- Categories (with source names + descriptions) ----
        lines.append("## 分类精选")
        lines.append("")
        cats = self._group_by_category(records)
        for cat, crecs in sorted(cats.items()):
            lines.append(f"### {cat}")
            lines.append("")
            lines.append("| # | 项目 | 描述 | 本周 ⭐ | 可信度 | 来源 |")
            lines.append("|---|------|------|---------|--------|------|")
            for i, r in enumerate(crecs, 1):
                desc = self._short_desc(r)
                sources = self._source_names(r)
                lines.append(
                    f"| {i} | [{r.full_name}]({r.html_url}) | {desc} | "
                    f"+{r.weekly_growth:,} | {r.confidence_grade} | {sources} |"
                )
            lines.append("")

        lines.extend(["---", ""])

        # Deep analysis
        if deep_analysis:
            lines.append("## AI 深度分析")
            lines.append("")
            lines.append(deep_analysis)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Stats
        if stats:
            lines.append("## 数据洞察")
            lines.append("")
            for k, v in stats.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

        # Feedback prompt
        lines.extend([
            "---",
            "",
            "## 反馈",
            "",
            f"> 对本期周报有意见？请提交到 `feedback/{week_str}.md`",
            "> 格式：`- [ ] repo_id: 正确分类 (理由)`",
            "> 标记为 `[x]` 表示已确认的永久规则",
            "",
            f"*本期由 GitHub Weekly Digest 自动生成 | {now.strftime('%Y-%m-%d')}*",
        ])

        content = "\n".join(lines)
        week_dir = self.output_dir / "weekly" / now.strftime("%Y")
        week_dir.mkdir(parents=True, exist_ok=True)
        (week_dir / f"{week_str}.md").write_text(content, encoding="utf-8")
        return content

    def render_card(self, record):
        fm = record.to_frontmatter()
        lines = ["---"]
        for k, v in fm.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            elif isinstance(v, str) and "\n" in v:
                lines.append(f"{k}: |")
                for line in v.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(f"{k}: {v}")
        lines.append("aliases:")
        lines.append(f"  - {record.full_name}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {record.full_name}")
        lines.append("")
        lines.append(f"> {record.description or '(no description)'}")
        lines.append("")

        tags = ["#github-project", f"#lang-{(record.language or 'unknown').lower()}",
                f"#grade-{record.confidence_grade.lower()}"]
        for cat in record.categories:
            tags.append(f"#{(cat.lower().replace(' ','-'))}")
        lines.append(" ".join(tags))
        lines.append("")

        lines.extend([
            "## Info",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Language** | {record.language or '?'} |",
            f"| **Stars** | {record.stars:,} |",
            f"| **Weekly** | +{record.weekly_growth:,} |",
            f"| **Forks** | {record.forks:,} |",
            f"| **Issues** | {record.open_issues} |",
            f"| **Confidence** | {record.confidence_grade} ({record.confidence_score:.0f}/100) |",
            f"| **Citations** | {record.citation_count} |",
            "",
            "## Links",
            "",
            f"- [GitHub]({record.html_url})",
            f"- [Star History](https://star-history.com/#{record.full_name})",
            "",
            "## Sources",
            "",
        ])
        for c in record.citations:
            lines.append(f"- {c.source_name} (Tier {c.tier})")

        if record.categories:
            lines.extend(["", "## Categories", ""])
            for cat in record.categories:
                lines.append(f"- [[{cat}]]")

        lines.extend([
            "",
            "---",
            "",
            f"*First seen: {record.first_seen[:19]}*  ",
            f"*Updated: {record.last_updated[:19]}*",
        ])

        content = "\n".join(lines)
        cards_dir = self.output_dir / "cards"
        cards_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{record.full_name.replace('/', '--')}.md"
        (cards_dir / filename).write_text(content, encoding="utf-8")
        return content

    def render_category_index(self, records):
        cats = self._group_by_category(records)
        results = {}
        cat_dir = self.output_dir / "categories"
        cat_dir.mkdir(parents=True, exist_ok=True)
        for cat, crecs in cats.items():
            lines = [
                "---",
                "type: category-moc",
                f"category: {cat}",
                f"total_projects: {len(crecs)}",
                "---",
                "",
                f"# {cat}",
                "",
                f"> {len(crecs)} projects",
                "",
                "```dataview",
                "TABLE language, stargazers_count, confidence_grade",
                'FROM "10 - GitHub Trending/项目卡片"',
                f'WHERE contains(categories, "{cat}")',
                "SORT confidence_score DESC",
                "```",
                "",
                "## Projects",
                "",
            ]
            for r in crecs:
                lines.append(f"- [[{r.full_name.replace('/', '--')}|{r.full_name}]] — {r.description or '?'}")
            content = "\n".join(lines)
            filename = f"{cat.lower().replace(' ','-')}.md"
            (cat_dir / filename).write_text(content, encoding="utf-8")
            results[cat] = content
        return results

    def _group_by_category(self, records):
        cats = {}
        for r in records:
            for c in r.categories:
                if c not in cats:
                    cats[c] = []
                cats[c].append(r)
        uncat = [r for r in records if not r.categories]
        if uncat:
            cats["未分类"] = uncat
        return cats
