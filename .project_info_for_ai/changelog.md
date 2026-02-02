# Changelog

**文档摘要**：记录 API/功能变更，时间倒序。遵循 Keep a Changelog 风格；行为/契约变更必须在此登记，并与 `api_development.md`、实现保持一致。

**目录索引**
- [Unreleased](#unreleased)
- [2026-02-01] 初始模板

## Unreleased
### Added
- 新增 Jina Reader API Key 开关（默认走免费模式）。

### Changed
- 搜索提供方选择改为动态自适应：成功率/延迟评分 + 429 冷却窗口。
- 搜索结果加入短期缓存以减少限额消耗（默认 5 分钟）。
- 内容抓取对 CSDN/知乎等站点启用更快超时与失败策略。

### Fixed
- 处理 r.jina.ai 直传链接的双重包裹问题。

### Removed / Deprecated
- 无

## 2026-02-01
### Added
- 初始化 changelog 模板。
