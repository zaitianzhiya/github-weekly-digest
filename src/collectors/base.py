"""采集器基类 — 统一接口，所有采集器继承此类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class SourceCitation:
    """引用来源标记"""
    source_key: str           # 来源标识，如 "opengithubs"
    source_name: str          # 来源名称，如 "OpenGithubs 周榜"
    source_url: str           # 来源平台链接
    source_type: str          # "primary" 或 "citation"
    tier: int                 # 1=原始, 2=引用
    ecosystem: str            # 所属生态
    cited_at: str             # 引用时间 ISO 格式
    original_url: str         # 原始平台内容链接
    original_author: str      # 原始推荐者
    fetch_method: str         # api / scraper / rss / manual
    is_cross_ecosystem: bool  # 是否跨生态引用


@dataclass
class RepoRecord:
    """仓库记录"""
    repo_id: str                      # owner/repo
    full_name: str                    # owner/repo
    html_url: str                     # GitHub 链接
    description: str                  # 项目描述
    language: str                     # 主编程语言
    stars: int                        # 总 Star 数
    weekly_growth: int                # 本周 Star 增长
    daily_growth: int                 # 今日 Star 增长
    forks: int                        # Fork 数
    open_issues: int                  # Open Issue 数
    created_at: str                   # 创建时间 ISO
    pushed_at: str                    # 最后推送时间 ISO
    license: str                      # 许可证
    readme_text: str                  # README 内容（截取）
    topics: list                      # GitHub Topics
    categories: list                  # 分类标签
    confidence_score: float           # 可信度评分
    confidence_grade: str             # 可信度等级 A/B/C/D
    citation_count: int               # 引用来源数
    citations: list                   # SourceCitation 列表
    sources: list                     # 来源名称列表（去重）
    first_seen: str                   # 首次出现时间 ISO
    last_updated: str                 # 最后更新时间 ISO
    raw_data: dict                    # 原始数据

    def to_dict(self) -> dict:
        d = asdict(self)
        d["citations"] = [asdict(c) for c in self.citations]
        return d

    def to_frontmatter(self) -> dict:
        """转为 Obsidian frontmatter 格式"""
        return {
            "repo_id": self.repo_id,
            "full_name": self.full_name,
            "language": self.language,
            "stars": self.stars,
            "weekly_growth": self.weekly_growth,
            "daily_growth": self.daily_growth,
            "forks": self.forks,
            "open_issues": self.open_issues,
            "confidence_score": round(self.confidence_score, 1),
            "confidence_grade": self.confidence_grade,
            "citation_count": self.citation_count,
            "categories": self.categories,
            "sources": self.sources,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "html_url": self.html_url,
        }


class BaseCollector(ABC):
    """采集器基类"""

    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def collect(self) -> list[RepoRecord]:
        """执行采集，返回 RepoRecord 列表"""
        pass

    def create_citation(self, source_key: str) -> SourceCitation:
        """根据 sources.yml 配置创建引用标记"""
        source_config = None
        if source_key in self.config.get("sources", {}):
            source_config = self.config["sources"][source_key]
        else:
            # 在原始数据源中查找
            for k, v in self.config.get("sources", {}).items():
                if v.get("name") == source_key:
                    source_config = v
                    source_key = k
                    break

        if not source_config:
            raise ValueError(f"Unknown source: {source_key}")

        return SourceCitation(
            source_key=source_key,
            source_name=source_config.get("name", source_key),
            source_url=source_config.get("url", ""),
            source_type="primary" if source_config.get("tier") == 1 else "citation",
            tier=source_config.get("tier", 1),
            ecosystem=source_config.get("ecosystem", "unknown"),
            cited_at=datetime.utcnow().isoformat(),
            original_url=source_config.get("url", ""),
            original_author=source_config.get("name", ""),
            fetch_method=source_config.get("type", "api"),
            is_cross_ecosystem=source_config.get("is_cross_ecosystem", False),
        )
