"""Entry point for GitHub Actions - avoids relative import issues."""
import sys, os, argparse, yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import core modules directly
from src.collectors.github_trending import GitHubTrendingCollector
from src.collectors.citation_collectors import CitationCollector
from src.filters.dedup import Deduplicator
from src.filters.quality import QualityFilter
from src.filters.scorer import Scorer
from src.render.markdown_weekly import MarkdownRenderer
from src.main import _auto_categorize, _merge_records, _confidence_distribution, _language_distribution

def load_config():
    config = {}
    for f in ["sources.yml","keywords.yml","quality.yml"]:
        p = Path("config") / f
        if p.exists():
            config.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return config

def run(mode):
    config = load_config()
    print(f"[{mode}] Starting...")
    records = []

    # Collect
    gc = GitHubTrendingCollector(config)
    records.extend(gc.collect())
    print(f"  Trending: {len(gc.collect())} repos (refresh)")
    
    # Refetch properly
    records = []
    gc2 = GitHubTrendingCollector(config)
    records = gc2.collect()
    print(f"  Trending: {len(records)} repos")

    if mode == "weekly":
        for key in ["opengithubs","ruanyf_weekly"]:
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
    dedup = Deduplicator("data/state.json")
    merged, seen = dedup.deduplicate(merged)
    qf = QualityFilter(config)
    scorer = Scorer(config)
    merged = qf.filter(merged)
    merged = scorer.score(merged)
    merged.sort(key=lambda r: (r.confidence_score, r.raw_data.get('quality_score',0)), reverse=True)
    print(f"  Pipeline: {len(merged)} repos")

    # AI (optional)
    summary = ""
    analysis = ""
    try:
        from src.ai.llm_client import LLMClient
        from src.ai.summarizer import DailySummarizer
        client = LLMClient()
        ds = DailySummarizer(client, Path("prompts"))
        summary = ds.summarize(merged[:20])
        print(f"  AI Summary: {len(summary)} chars")
        if mode == "weekly":
            from src.ai.deep_analyzer import DeepAnalyzer
            da = DeepAnalyzer(client, Path("prompts"))
            analysis = da.analyze_top(merged[:10])
            print(f"  Deep Analysis: {len(analysis)} chars")
    except Exception as e:
        print(f"  AI: skipped - {e}")

    # Render
    renderer = MarkdownRenderer("output")
    a = sum(1 for r in merged if r.confidence_grade == 'A')
    b = sum(1 for r in merged if r.confidence_grade == 'B')
    stats = dedup.get_stats()
    stats.update({"Mode": mode, "Repos": len(merged), "Confidence": f"A:{a} B:{b}",
                  "AI": "enabled" if summary else "disabled"})
    renderer.render_weekly_report(merged, daily_summary=summary, deep_analysis=analysis, stats=stats)
    for r in merged[:15]:
        renderer.render_card(r)
    renderer.render_category_index(merged[:20])
    print(f"  Done: {len(list(Path('output').rglob('*.md')))} files")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily","weekly"], default="daily")
    args = parser.parse_args()
    run(args.mode)
