"""每周深度分析生成器"""

from pathlib import Path
from typing import Optional

from .llm_client import LLMClient
from ..collectors.base import RepoRecord


class DeepAnalyzer:
    """每周深度分析：对 Top 项目逐条深度分析"""

    def __init__(self, client: LLMClient, prompts_dir: Path):
        self.client = client
        self.prompts_dir = prompts_dir
        self.instructions = self._load_instructions()

    def _load_instructions(self) -> str:
        prompt_file = self.prompts_dir / "weekly-deep.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return "你是一个资深技术分析师，请对以下 GitHub 项目进行深度分析。"

    def analyze_top(self, records: list[RepoRecord], max_count: int = 15) -> str:
        """对 Top N 个项目进行深度分析"""
        top_records = records[:max_count]
        if not top_records:
            return "本期无项目需要深度分析。"

        # 构建输入
        repos_text = self._format_for_deep_analysis(top_records)
        user_message = f"以下是要深度分析的项目列表：\n\n{repos_text}\n\n请逐项目生成深度分析，并在最后给出本周趋势洞察。"

        try:
            result = self.client.chat(
                system_prompt=self.instructions,
                user_message=user_message,
                temperature=0.5,  # 低温度，确保准确性
            )
            return result
        except Exception as e:
            print(f"[DeepAnalyzer] LLM call failed: {e}")
            return self._fallback_analysis(top_records)

    def _format_for_deep_analysis(self, records: list[RepoRecord]) -> str:
        """格式化为深度分析输入"""
        lines = []
        for i, r in enumerate(records, 1):
            lines.append(f"---")
            lines.append(f"### #{i} {r.full_name}")
            lines.append(f"**语言**: {r.language or '未知'}")
            lines.append(f"**本周增长**: ⭐ +{r.weekly_growth} | **总计**: ⭐ {r.stars}")
            lines.append(f"**可信度**: {r.confidence_grade} ({r.confidence_score:.0f}/100)")
            lines.append(f"**来源**: {', '.join(r.sources)}")
            lines.append(f"**项目描述**: {r.description or '（无描述）'}")
            if r.readme_text:
                lines.append(f"**README 全文**:\n```\n{r.readme_text[:4000]}\n```")
            lines.append(f"**链接**: {r.html_url}")
        return "\n".join(lines)

    def _fallback_analysis(self, records: list[RepoRecord]) -> str:
        """兜底分析"""
        lines = ["# 本周深度分析（AI 暂不可用）\n"]
        lines.append(f"> 本期 Top {len(records)} 项目列表\n")
        for r in records:
            lines.append(f"## {r.full_name}")
            lines.append(f"- ⭐ {r.stars} | 📈 +{r.weekly_growth} | 可信度: {r.confidence_grade}")
            lines.append(f"- {r.description or '（无描述）'}")
            lines.append("")
        return "\n".join(lines)
