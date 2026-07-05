# 分类体系

## 主分类

每个项目必须分配到以下分类之一（可多选，最多 3 个）：

| 分类 | 标签 | 典型特征 |
|------|------|---------|
| AI | `#ai` | LLM、Agent、RAG、机器学习、模型部署、向量数据库、Prompt 工具 |
| 开发者工具 | `#devtools` | CLI 工具、IDE 插件、代码生成、调试、测试、API 工具 |
| 前端 | `#frontend` | UI 框架、React/Vue 组件、CSS 工具、设计系统、Web 构建 |
| 后端 | `#backend` | API 框架、数据库、消息队列、微服务、认证授权 |
| 基础设施 | `#infra` | 容器、K8s、CI/CD、监控、日志、网络 |
| 安全 | `#security` | 漏洞扫描、渗透测试、加密、身份验证、安全审计 |
| 数据 | `#data` | 数据库、数据分析、ETL、可视化、数据工程 |
| 移动 | `#mobile` | iOS/Android 开发、跨平台框架、移动端工具 |
| 设计 | `#design` | 设计工具、原型、图表、动画 |
| 媒体 | `#media` | 视频处理、音频处理、图像生成、流媒体 |
| 编程语言 | `#lang` | 新语言、编译器、解释器、类型系统 |
| 开源替代 | `#oss-alt` | 对标商业产品的开源版 |
| 文档/知识 | `#docs` | 文档工具、知识管理、技术写作 |

## 自动分类 Prompt 规则

当你看到以下信号时，分配到对应分类：

- **README 中包含 "LLM", "GPT", "transformer", "agent", "RAG", "vector database", "embedding"** → 主分类 `AI`
- **README 中包含 "CLI", "command line", "shell", "terminal"** → 加分 `devtools`
- **README 中提到 "alternative to [商业产品]"** → 加分 `oss-alt`
- **项目语言为 Rust** 且涉及底层 → 可能是性能工具，注意 `devtools` 或 `infra`

## 可追加的反馈规则

<!-- 以下规则由每周反馈自动追加，请勿手动编辑 -->
<!-- FEEDBACK_RULES_START -->
<!-- FEEDBACK_RULES_END -->
