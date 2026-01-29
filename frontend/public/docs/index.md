# WisdomPrompt 文档

## 简介

WisdomPrompt 提供联网搜索、知识库检索与提示词生成能力。

## 产品页工作流

1. **Query 拆解**：将用户问题拆成 1～4 个子任务
2. **检索**：每个子任务做向量检索（top3，相似度≥0.7），不足则联网搜索并拉取正文
3. **整理**：对每个子任务的检索结果做汇总
4. **最终答案**：基于子任务与汇总结果生成 Markdown 答案，支持流式展示与一键复制

## 技术栈

- 前端：Vite、React、Tailwind CSS
- 后端：FastAPI、DuckDB + VSS、OpenAI LLM、Gemini Embedding
- 搜索：Brave / Exa / Serper 三选一；正文拉取：webfetch + Jina Reader 备用
