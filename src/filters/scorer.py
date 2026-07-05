"""五维量化评分 + 可信度计算"""

from datetime import datetime

from src.collectors.base import RepoRecord


class Scorer:
    """量化评分器：综合 5 维度评分 + 可信度评级"""

    def __init__(self, config: dict):
        self.scoring = config.get("scoring", {})
        self.confidence_cfg = config.get("confidence", {})
        self.ecosystems = config.get("ecosystems", {})

    def score(self, records: list[RepoRecord]) -> list[RepoRecord]:
        """对所有记录进行评分和可信度计算"""
        for record in records:
            self._compute_confidence(record)
            self._compute_quality_score(record)
        return records

    def _compute_confidence(self, record: RepoRecord):
        """计算可信度评分"""
        score = 0
        seen_ecosystems = set()

        for citation in record.citations:
            source_key = citation.source_key

            if citation.tier == 1:
                # Tier 1 原始来源基础分
                score += self.confidence_cfg.get("tier1_bonus", 40)
            else:
                # Tier 2 每个引用 +15（上限 45）
                per_citation = self.confidence_cfg.get("tier2_per_citation", 15)
                max_tier2 = self.confidence_cfg.get("tier2_max", 45)
                score += per_citation

            # 跨生态加分
            if citation.ecosystem not in seen_ecosystems:
                seen_ecosystems.add(citation.ecosystem)

        # 跨生态额外加分
        cross_bonus = self.confidence_cfg.get("cross_ecosystem_bonus", 5)
        cross_max = self.confidence_cfg.get("cross_ecosystem_max", 15)
        cross_eco_count = len(seen_ecosystems)
        score += min(cross_eco_count * cross_bonus, cross_max)

        # 计算等级
        grades = self.confidence_cfg.get("grades", {})
        for grade in ["A", "B", "C", "D"]:
            cfg = grades.get(grade, {})
            if score >= cfg.get("min", 0):
                record.confidence_score = min(score, 100)
                record.confidence_grade = grade
                break
        else:
            record.confidence_score = min(score, 100)
            record.confidence_grade = "D"

        record.citation_count = len(set(c.source_key for c in record.citations))
        record.sources = list(set(c.source_name for c in record.citations))

    def _compute_quality_score(self, record: RepoRecord):
        """计算五维质量评分（存储在 raw_data 中供排序使用）"""
        score = 0.0

        # 1. Star 增长（25%）
        star_weight = self.scoring.get("star_growth", 25)
        star_growth = record.weekly_growth or record.raw_data.get("weekly_growth", 0)
        score += min(star_growth / 100.0 * star_weight, star_weight)

        # 2. 多源验证（25%）— 已通过 confidence_score 体现
        multi_weight = self.scoring.get("multi_source", 25)
        source_count = len(set(c.source_key for c in record.citations))
        score += min(source_count * 5.0 * multi_weight / 25.0, multi_weight)

        # 3. 文档完整性（20%）
        doc_weight = self.scoring.get("documentation", 20)
        readme = record.readme_text or ""
        doc_score = 0
        if "# " in readme:
            doc_score += 5
        if "## " in readme:
            doc_score += 5
        if any(w in readme.lower() for w in ["install", "安装", "quick start", "快速开始"]):
            doc_score += 5
        if any(w in readme.lower() for w in ["usage", "使用", "example", "示例"]):
            doc_score += 5
        score += min(doc_score * doc_weight / 20.0, doc_weight)

        # 4. 社区活跃度（15%）
        comm_weight = self.scoring.get("community", 15)
        commits = record.raw_data.get("commits_last_month", 0)
        score += min(commits * 1.5 * comm_weight / 15.0, comm_weight)

        # 5. 新颖度（15%）
        novel_weight = self.scoring.get("novelty", 15)
        created_at = record.created_at or record.raw_data.get("created_at", "")
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                days_since = (datetime.utcnow() - created.replace(tzinfo=None)).days
                if days_since < 30:
                    score += novel_weight
                elif days_since < 90:
                    score += novel_weight * 0.7
                elif days_since < 180:
                    score += novel_weight * 0.3
            except (ValueError, TypeError):
                pass

        record.raw_data["quality_score"] = round(score, 1)
