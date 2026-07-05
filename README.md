# GitHub Weekly Digest

自动采集 GitHub Trending + OpenGithubs 周榜 + 阮一峰周刊，结合 Gemini AI 生成中文摘要和深度分析。

## 工作原理

- **每日** (UTC 8:00)：采集 GitHub Trending，去重评分，生成项目卡片
- **每周一** (UTC 10:17)：全量采集（含引用源）+ AI 摘要 + 深度分析 + 反馈闭环

## 部署

1. Fork 或克隆本仓库
2. 在 Settings → Secrets and variables → Actions 中添加：
   - `GITHUB_TOKEN`：用于 API 速率限制（自动创建 PAT 即可）
   - `GEMINI_API_KEY`：从 https://aistudio.google.com/apikey 获取
3. 启用 Actions（Settings → Actions → Allow all）
4. 手动触发一次 `Daily Collection` workflow 验证

## 输出

周报保存在 `output/weekly/YYYY/YYYY-Www.md`，可直接导入 Obsidian 使用。
