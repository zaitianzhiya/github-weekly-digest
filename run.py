"""Entry point for GitHub Actions - avoids relative import issues."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

# Windows GBK consoles cannot encode emoji — degrade gracefully
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from src.collectors.citation_collectors import CitationCollector
from src.collectors.github_trending import GitHubTrendingCollector
from src.filters.dedup import Deduplicator
from src.filters.quality import QualityFilter
from src.filters.scorer import Scorer
from src.main import _auto_categorize, _merge_records
from src.render.markdown_weekly import MarkdownRenderer


def load_config():
    config = {}
    for f in ["sources.yml", "keywords.yml", "quality.yml"]:
        p = Path("config") / f
        if p.exists():
            config.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return config


def run(mode):
    config = load_config()
    print(f"[{mode}] Starting...")

    # Collect (single pass — trending scraping is rate-limited)
    records = GitHubTrendingCollector(config).collect()
    print(f"  Trending: {len(records)} repos")

    if mode == "weekly":
        for key in ["opengithubs", "ruanyf_weekly"]:
            try:
                items = CitationCollector(config, key).collect()
                records.extend(items)
                print(f"  {key}: {len(items)} repos")
            except Exception as e:
                print(f"  {key}: skipped - {e}")

    # Categorize + pipeline
    for r in records:
        r.categories = _auto_categorize(r)

    merged = _merge_records(records)
    if not merged:
        print(f"[{mode}] No records collected — aborting without touching output/")
        return

    merged = QualityFilter(config).filter(merged)
    merged = Scorer(config).score(merged)
    merged.sort(key=lambda r: (r.confidence_score, r.raw_data.get("quality_score", 0)), reverse=True)
    print(f"  Pipeline: {len(merged)} repos")

    if not merged:
        print(f"[{mode}] No records passed filters — aborting without touching output/")
        return

    dedup = Deduplicator(str(Path("data") / "dedup_state.json"))
    merged, seen = dedup.deduplicate(merged)
    print(f"  Dedup: {len(merged)} this-cycle / {seen} seen")

    if not merged:
        print(f"[{mode}] All repos already seen this week — aborting without touching output/")
        return

    # AI (optional)
    summary = ""
    analysis = ""
    ai_available = False
    try:
        from src.ai.llm_client import LLMClient
        client = LLMClient()
        ai_available = True
        if mode == "daily":
            from src.ai.summarizer import DailySummarizer
            summary = DailySummarizer(client, Path("prompts")).summarize(merged[:20])
            print(f"  AI Summary: {len(summary)} chars")
        else:
            from src.ai.deep_analyzer import DeepAnalyzer
            analysis = DeepAnalyzer(client, Path("prompts")).analyze_top(merged[:15])
            print(f"  Deep Analysis: {len(analysis)} chars")
    except Exception as e:
        print(f"  AI: skipped - {e}")

    # Render: daily writes a dated snapshot, weekly writes the week file
    renderer = MarkdownRenderer("output")
    a = sum(1 for r in merged if r.confidence_grade == "A")
    b = sum(1 for r in merged if r.confidence_grade == "B")
    stats = dedup.get_stats()
    stats.update({
        "Mode": mode,
        "Repos": len(merged),
        "Confidence": f"A:{a} B:{b}",
        "AI": "enabled" if ai_available else "disabled",
        "AvgQualityScore": round(sum(r.raw_data.get("quality_score", 0) for r in merged) / len(merged), 1) if merged else 0.0,
    })
    if mode == "daily":
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        renderer.render_weekly_report(merged, daily_summary=summary, stats=stats,
                                      output_path=f"daily/{today[:4]}/{today}.md")
        dedup.save()
    else:
        renderer.render_weekly_report(merged, daily_summary=summary, deep_analysis=analysis, stats=stats)
        for r in merged[:15]:
            renderer.render_card(r)
        renderer.render_category_index(merged[:20])
        dedup.save()
    print(f"  Done: mode={mode}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()
    run(args.mode)
