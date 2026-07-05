"""每日快速摘要生成器 — 借鉴 oranger0611 digest 模式"""

from pathlib import Path

from src.ai.llm_client import LLMClient
from src.collectors.base import RepoRecord


class DailySummarizer:
    """每日快速摘要：单次 LLM 调用处理所有条目"""

    def __init__(self, client: LLMClient, prompts_dir: Path):
        self.client = client
        self.prompts_dir = prompts_dir
        self.instructions = self._load_instructions()

    def _load_instructions(self) -> str:
        """加载每日摘要 Prompt（借鉴 oranger0611: Prompt 与代码分离）"""
        prompt_file = self.prompts_dir / "daily-summary.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return "你是一个技术编辑，请为以下 GitHub 项目生成简洁的中文摘要。"

    def summarize(self, records: list[RepoRecord]) -> str:
        """对一批项目生成摘要"""
        if not records:
            return "本期没有新项目。"

        # 构建输入
        repos_text = self._format_repos_for_llm(records)
        user_message = f"以下是今天的热门 GitHub 项目列表：\n\n{repos_text}\n\n请按指令生成每日摘要。"

        try:
            result = self.client.chat(
                system_prompt=self.instructions,
                user_message=user_message,
                temperature=0.7,
            )
            return result
        except Exception as e:
            print(f"[DailySummarizer] LLM call failed: {e}")
            return self._fallback_summary(records)

    def _format_repos_for_llm(self, records: list[RepoRecord]) -> str:
        """将 RepoRecord 列表格式化为 LLM 输入"""
        lines = []
        for i, r in enumerate(records, 1):
            lines.append(f"---")
            lines.append(f"#{i} {r.full_name}")
            lines.append(f"语言: {r.language or '未知'}")
            lines.append(f"本周 ⭐ +{r.weekly_growth} | 总 ⭐ {r.stars}")
            lines.append(f"描述: {r.description or '（无描述）'}")
            if r.readme_text:
                # 截取 README 开头给 LLM 参考
                readme_preview = r.readme_text[:2000]
                lines.append(f"README 摘要: {readme_preview}")
            lines.append(f"链接: {r.html_url}")
        return "\n".join(lines)

    def _fallback_summary(self, records: list[RepoRecord]) -> str:
        """LLM 调用失败时的兜底摘要"""
        lines = ["# 今日 GitHub Trending 项目\n"]
        lines.append(f"> 共 {len(records)} 个项目（AI 摘要暂不可用，仅展示原始数据）\n")
        for r in records[:20]:
            lines.append(f"## {r.full_name}")
            lines.append(f"- **语言**: {r.language or '未知'}")
            lines.append(f"- **本周增长**: ⭐ +{r.weekly_growth} | **总计**: ⭐ {r.stars}")
            lines.append(f"- **描述**: {r.description or '（无描述）'}")
            lines.append(f"- **链接**: {r.html_url}")
            lines.append("")
        return "\n".join(lines)
