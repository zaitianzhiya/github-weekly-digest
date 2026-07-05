"""Feedback loader - parse feedback files and build rule blocks for prompts."""

import re
from datetime import datetime, timedelta
from pathlib import Path


class FeedbackLoader:
    """Load weekly feedback and build context for the classifier/analyzer."""

    def __init__(self, feedback_dir=None):
        self.feedback_dir = Path(feedback_dir) if feedback_dir else Path("feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def get_recent_feedback(self, weeks=4):
        """Get feedback from the last N weeks."""
        now = datetime.utcnow()
        current_week = now.strftime("%Y-W%V")
        results = []
        for _ in range(weeks):
            fpath = self.feedback_dir / f"{current_week}.md"
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8")
                results.append({"week": current_week, "content": content, "path": str(fpath)})
            # Step back one week
            year, wk = current_week.split("-W")
            wk_num = int(wk) - 1
            if wk_num <= 0:
                year = int(year) - 1
                wk_num = 52
            current_week = f"{year}-W{wk_num:02d}"
        return results

    def build_prompt_context(self, weeks=4):
        """Build a prompt block from recent feedback for injection into AI prompts."""
        feedbacks = self.get_recent_feedback(weeks)
        if not feedbacks:
            return ""

        lines = [
            "",
            "## 反馈规则（最近 4 周读者反馈）",
            "",
            "以下是读者对往期分类和推荐质量的反馈，请在判断时参考：",
            "",
        ]
        for fb in feedbacks:
            content = fb["content"]
            # Extract tier corrections
            corrections = re.findall(r'-\s*\[x?\]\s*(.+?):\s*(.+?)\s*\((.+?)\)', content)
            if corrections:
                lines.append(f"### 第 {fb['week']} 周反馈")
                for repo, tier, reason in corrections:
                    lines.append(f"- {repo}: 应归类为 **{tier}** (理由: {reason})")

            # Extract new rules
            rules = re.findall(r'-\s*\[x?\]\s*Rule[：:]\s*(.+)', content)
            for rule in rules:
                lines.append(f"- 新规则: {rule}")

            # Extract permanent rules
            perm = re.findall(r'-\s*\[x\]\s*\*\*永久规则\*\*[：:]\s*(.+)', content)
            for p in perm:
                lines.append(f"- **永久规则**: {p}")

            lines.append("")

        lines.extend([
            "**请在本次分析中应用以上反馈规则。**",
            "",
        ])
        return "\n".join(lines)
