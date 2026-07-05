"""Orchestrator: collect -> filter -> score -> AI -> render pipeline."""

import argparse, os, sys, yaml
from datetime import datetime
from pathlib import Path

from .collectors.github_trending import GitHubTrendingCollector
from .collectors.hackernews import HackerNewsCollector
from .collectors.citation_collectors import CitationCollector
from .filters.dedup import Deduplicator
from .filters.quality import QualityFilter
from .filters.scorer import Scorer
from .render.markdown_weekly import MarkdownRenderer

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    config = {}
    for f in ["sources.yml","keywords.yml","quality.yml"]:
        p = ROOT / "config" / f
        if p.exists():
            config.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return config


def _auto_categorize(record):
    """Auto-classify based on description, language, and topics."""
    text = f"{record.description or ''} {record.language or ''} {' '.join(record.topics)}".lower()
    cats = []
    mapping = {
        "AI": ["ai ","llm","agent","rag","vector","embedding","transformer","machine learning","deep learning","neural","gpt","claude","gemini"],
        "devtools": ["cli","command line","terminal","shell","sdk","api ","debug","profiler","linter","ide","editor","plugin","extension"],
        "frontend": ["react","vue","angular","svelte","css","html","tailwind","ui ","frontend","web component"],
        "backend": ["api server","microservice","rest","graphql","grpc","backend","orm","middleware"],
        "infra": ["docker","kubernetes","k8s","container","ci/cd","pipeline","monitoring","logging","proxy","load balancer"],
        "security": ["security","vulnerability","penetration","encrypt","auth","firewall","exploit","scan"],
        "data": ["database","sql","nosql","etl","analytics","visualization","pipeline","data warehouse"],
        "media": ["video","audio","image","stream","media","ffmpeg","screenshot","recording"],
        "design": ["design","figma","sketch","prototype","animation","css art","svg"],
        "docs": ["documentation","docs","knowledge base","wiki","note","writing"],
    }
    for cat, kws in mapping.items():
        if any(kw in text for kw in kws):
            cats.append(cat)
    return cats if cats else []


def _merge_records(records):
    """Merge records with same repo_id, combining citation chains."""
    from .collectors.base import RepoRecord
    merged = {}
    for r in records:
        if r.repo_id in merged:
            existing = merged[r.repo_id]
            existing_keys = {c.source_key for c in existing.citations}
            for c in r.citations:
                if c.source_key not in existing_keys:
                    existing.citations.append(c)
            if r.readme_text and not existing.readme_text:
                existing.readme_text = r.readme_text
            if r.description and not existing.description:
                existing.description = r.description
            if r.stars > existing.stars:
                existing.stars = r.stars
                existing.weekly_growth = r.weekly_growth
            # Merge categories
            for cat in r.categories:
                if cat not in existing.categories:
                    existing.categories.append(cat)
        else:
            merged[r.repo_id] = r
    return list(merged.values())


def _confidence_distribution(records):
    grades = {"A":0,"B":0,"C":0,"D":0}
    for r in records:
        grades[r.confidence_grade] = grades.get(r.confidence_grade,0) + 1
    return ", ".join(f"{k}:{v}" for k,v in grades.items() if v>0)

def _language_distribution(records):
    langs = {}
    for r in records:
        l = r.language or "unknown"
        langs[l] = langs.get(l,0)+1
    return ", ".join(f"{k}:{v}" for k,v in sorted(langs.items(),key=lambda x:-x[1])[:5])


def run_daily(config):
    print("[Daily] Starting...")
    records = []

    # Tier 1 collectors
    for name, cls in [("github_trending",GitHubTrendingCollector)]:
        try:
            c = cls(config)
            items = c.collect()
            print(f"  [{name}] {len(items)} repos")
            records.extend(items)
        except Exception as e:
            print(f"  [{name}] FAILED: {e}")

    if not records:
        print("[Daily] No records."); return

    # Auto-categorize
    for r in records:
        r.categories = _auto_categorize(r)

    # Dedup
    dedup = Deduplicator(str(ROOT/"data"/"state.json"))
    merged, seen = dedup.deduplicate(records)
    print(f"[Daily] Dedup: {len(merged)} new / {seen} seen")

    if not merged:
        print("[Daily] All seen."); return

    # Filter + score
    qf = QualityFilter(config)
    scorer = Scorer(config)
    merged = qf.filter(merged)
    merged = scorer.score(merged)
    merged.sort(key=lambda r: (r.confidence_score, r.raw_data.get("quality_score",0)), reverse=True)
    print(f"[Daily] Filtered: {len(merged)}")

    # Render
    renderer = MarkdownRenderer(str(ROOT/"output"))
    stats = dedup.get_stats()
    stats.update({"本周采集":len(merged),"可信度分布":_confidence_distribution(merged),
                  "语言分布":_language_distribution(merged)})
    renderer.render_weekly_report(merged, stats=stats)
    top_n = min(len(merged), 30)
    for r in merged[:top_n]:
        renderer.render_card(r)
    renderer.render_category_index(merged[:top_n])
    print(f"[Daily] Done: {top_n} cards rendered.")


def run_weekly(config):
    print("[Weekly] Starting full collection...")
    records = []

    # Tier 1
    for name, cls in [("github_trending",GitHubTrendingCollector)]:
        try:
            c = cls(config)
            items = c.collect()
            print(f"  [{name}] {len(items)} repos")
            records.extend(items)
        except Exception as e:
            print(f"  [{name}] FAILED: {e}")

    # Tier 2 citations
    for key in ["opengithubs","ruanyf_weekly","githubdaily"]:
        if not config.get("sources",{}).get(key,{}).get("enabled",True):
            continue
        try:
            c = CitationCollector(config, key)
            items = c.collect()
            print(f"  [{key}] {len(items)} repos")
            records.extend(items)
        except Exception as e:
            print(f"  [{key}] FAILED: {e}")

    # Auto-categorize
    for r in records:
        r.categories = _auto_categorize(r)

    # Merge + dedup
    merged = _merge_records(records)
    print(f"[Weekly] Merged: {len(merged)} unique")
    dedup = Deduplicator(str(ROOT/"data"/"state.json"))
    merged, seen = dedup.deduplicate(merged)
    print(f"[Weekly] Dedup: {len(merged)} new / {seen} seen")

    if not merged:
        print("[Weekly] All seen."); return

    # Filter + score
    qf = QualityFilter(config)
    scorer = Scorer(config)
    merged = qf.filter(merged)
    merged = scorer.score(merged)
    merged.sort(key=lambda r: (r.confidence_score, r.raw_data.get("quality_score",0)), reverse=True)
    print(f"[Weekly] Filtered: {len(merged)}, A:{sum(1 for r in merged if r.confidence_grade=='A')}, B:{sum(1 for r in merged if r.confidence_grade=='B')}")

    # AI summary (optional, graceful)
    daily_summary = ""
    deep_analysis = ""
    try:
        from .ai.llm_client import LLMClient
        from .ai.summarizer import DailySummarizer
        from .ai.deep_analyzer import DeepAnalyzer
        client = LLMClient()
        ds = DailySummarizer(client, ROOT/"prompts")
        daily_summary = ds.summarize(merged[:20])
        da = DeepAnalyzer(client, ROOT/"prompts")
        deep_analysis = da.analyze_top(merged[:15])
        print("[Weekly] AI summary + deep analysis generated.")
    except Exception as e:
        print(f"[Weekly] AI skipped: {e}")

    # Render
    renderer = MarkdownRenderer(str(ROOT/"output"))
    stats = dedup.get_stats()
    stats.update({
        "本周采集": len(merged), "本周新项目": stats["new_this_week"],
        "可信度分布": _confidence_distribution(merged),
        "语言分布": _language_distribution(merged),
        "多源验证项目": sum(1 for r in merged if r.citation_count >= 2),
        "时间": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    })
    renderer.render_weekly_report(merged, daily_summary=daily_summary, deep_analysis=deep_analysis, stats=stats)
    top_n = min(len(merged), 30)
    for r in merged[:top_n]:
        renderer.render_card(r)
    renderer.render_category_index(merged[:top_n])
    print(f"[Weekly] Done: {top_n} cards, {len(list(Path(ROOT/'output').rglob('*.md')))} files total.")


def main():
    parser = argparse.ArgumentParser(description="GitHub Weekly Digest")
    parser.add_argument("--mode", choices=["daily","weekly"], default="daily")
    args = parser.parse_args()
    config = load_config()
    if args.mode == "daily":
        run_daily(config)
    else:
        run_weekly(config)

if __name__ == "__main__":
    main()
