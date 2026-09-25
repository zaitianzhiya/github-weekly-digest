"""github-weekly-digest specific tests: scorer, quality, dedup, trending, renderer."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.collectors.base import RepoRecord, SourceCitation  # noqa: E402
from src.collectors.github_trending import GitHubTrendingCollector  # noqa: E402
from src.filters.dedup import Deduplicator  # noqa: E402
from src.filters.quality import QualityFilter  # noqa: E402
from src.filters.scorer import Scorer  # noqa: E402
from src.render.markdown_weekly import MarkdownRenderer  # noqa: E402


def load_config() -> dict:
    cfg: dict = {}
    for fn in ("sources.yml", "keywords.yml", "quality.yml"):
        p = ROOT / "config" / fn
        if p.exists():
            cfg.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return cfg


CONFIG = load_config()


def make_repo(repo_id="owner/repo", citations=None, raw=None):
    return RepoRecord(repo_id=repo_id, full_name=repo_id,
                      html_url=f"https://github.com/{repo_id}",
                      description="d" * 50, language="Python", stars=100,
                      weekly_growth=20, daily_growth=3, forks=5, open_issues=2,
                      created_at="2026-01-01T00:00:00Z", pushed_at="2026-09-20T00:00:00Z",
                      license="MIT", readme_text="# Title\n\nUsage example",
                      topics=[], categories=[], confidence_score=0.0, confidence_grade="D",
                      citation_count=0, citations=citations or [], sources=[],
                      first_seen="", last_updated="", raw_data=raw or {})


def make_citation(source_key="s1", source_name="S1", tier=1, ecosystem="eco_a"):
    return SourceCitation(source_key=source_key, source_name=source_name,
                          source_url="https://example.com", source_type="citation",
                          tier=tier, ecosystem=ecosystem, cited_at="2026-09-25T00:00:00Z",
                          original_url="https://example.com/x", original_author="tester",
                          fetch_method="api", is_cross_ecosystem=False)


C1 = make_citation("s1", "S1", 1, "eco_a")
C2 = make_citation("s2", "S2", 1, "eco_b")
C3 = make_citation("s3", "S3", 2, "eco_a")


class TestScorer:
    def test_single_tier1_plus_cross_bonus(self):
        scorer = Scorer(CONFIG)
        r = make_repo(citations=[C1])
        scorer.score([r])
        assert 40 <= r.confidence_score <= 45
        assert r.confidence_grade == "C"

    def test_dual_tier1_reaches_a(self):
        scorer = Scorer(CONFIG)
        r = make_repo(citations=[C1, C2])
        scorer.score([r])
        assert r.confidence_score >= 80
        assert r.confidence_grade == "A"

    def test_tier2_capped_at_max(self):
        scorer = Scorer(CONFIG)
        citations = [make_citation(f"t{i}", f"T{i}", 2, f"eco_{i}") for i in range(10)]
        r = make_repo(citations=citations)
        scorer.score([r])
        tier2_contrib = r.confidence_score - min(10 * 5, 15)  # minus cross bonus
        assert tier2_contrib <= 45

    def test_quality_score_recorded(self):
        scorer = Scorer(CONFIG)
        r = make_repo(citations=[C1])
        scorer.score([r])
        assert "quality_score" in r.raw_data


class TestQuality:
    def test_fork_excluded(self):
        qf = QualityFilter(CONFIG)
        assert qf.filter([make_repo(raw={"fork": True})]) == []

    def test_inactive_excluded(self):
        qf = QualityFilter(CONFIG)
        old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = make_repo(raw={"pushed_at": old})
        r.pushed_at = old
        assert qf.filter([r]) == []


class TestDedup:
    def test_repo_seen_across_runs(self, tmp_path):
        state = tmp_path / "dedup_state.json"
        d1 = Deduplicator(str(state))
        new1, seen1 = d1.deduplicate([make_repo("a/b"), make_repo("c/d")])
        assert len(new1) == 2
        d1.save()
        d2 = Deduplicator(str(state))
        new2, seen2 = d2.deduplicate([make_repo("a/b")])
        assert seen2 == 1
        # seen earlier THIS week → still re-listed (daily mode semantics)
        assert len(new2) == 1

    def test_repo_seen_last_week_not_relisted(self, tmp_path):
        state = tmp_path / "dedup_state.json"
        d1 = Deduplicator(str(state))
        d1.deduplicate([make_repo("a/b")])
        d1.state["repos"]["a/b"]["first_seen_week"] = "2026-W30"
        d1.save()
        d2 = Deduplicator(str(state))
        new2, seen2 = d2.deduplicate([make_repo("a/b")])
        assert seen2 == 1
        assert new2 == []

    def test_corrupt_state_recovers(self, tmp_path):
        state = tmp_path / "dedup_state.json"
        state.write_text("{ bad", encoding="utf-8")
        d = Deduplicator(str(state))
        assert d.state == {"repos": {}}

    def test_report_week_validated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("REPORT_WEEK", "../../evil")
        d = Deduplicator(str(tmp_path / "dedup_state.json"))
        assert d.state_file.name == "dedup_state.json"
        monkeypatch.setenv("REPORT_WEEK", "2026-W37")
        d2 = Deduplicator(str(tmp_path / "dedup_state.json"))
        assert d2.state_file.name == "dedup_state_2026-W37.json"


class TestTrending:
    def test_sponsor_rows_excluded(self):
        html = ('<article class="Box-row">'
                '<h2><a href="/sponsors/AcmeCorp">sponsors/AcmeCorp</a></h2>'
                '<p class="col-9">Sponsored listing</p></article>'
                '<article class="Box-row">'
                '<h2><a href="/octo/cat">octo/cat</a></h2>'
                '<p class="col-9">A real repo</p></article>')
        gc = GitHubTrendingCollector(CONFIG)
        repos = gc._parse_trending_html(html)
        names = [r["full_name"] for r in repos]
        assert "sponsors/AcmeCorp" not in names
        assert "octo/cat" in names


class TestRenderer:
    def test_week_range_is_a_range(self):
        r = MarkdownRenderer(str(ROOT / "output"))
        assert "~" in r._week_range("2026-W36")

    def test_daily_output_path(self, tmp_path):
        r = MarkdownRenderer(str(tmp_path))
        r.render_weekly_report([make_repo(citations=[C1])],
                               output_path="daily/2026/2026-09-25.md")
        assert (tmp_path / "daily/2026/2026-09-25.md").exists()

    def test_weekly_output_uses_iso_year(self, tmp_path, monkeypatch):
        monkeypatch.setenv("REPORT_WEEK", "2027-W01")
        r = MarkdownRenderer(str(tmp_path))
        r.render_weekly_report([make_repo(citations=[C1])])
        assert (tmp_path / "weekly/2027/2027-W01.md").exists()
