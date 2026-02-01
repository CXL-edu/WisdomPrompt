# API 开发文档（契约）

**文档摘要**：本文件是前后端联调的核心契约，定义接口路径、参数、响应、错误、认证与版本策略。更新后需与实现保持一致，并在变更时同步 `changelog.md`。

**目录索引**
- [接口列表总览](#接口列表总览)
- [认证与安全](#认证与安全)
- [错误与状态码](#错误与状态码)
- [版本与兼容](#版本与兼容)
- [端点详情模板](#端点详情模板)
- [变更记录（指向 changelog）](#变更记录指向-changelog)

## 接口列表总览
- （填充）列出接口名称、方法、路径、简要说明。

## 认证与安全
- （填充）鉴权方式：如 Bearer、API Key、Cookie 等；获取与使用方式。

## 错误与状态码
- HTTP 状态码约定：2xx 成功、4xx 客户端错误、5xx 服务端错误。
- 业务错误码格式：`code`（业务码）+ `message`（描述）+ 可选 `reference`。
- 统一错误体示例：
```json
{
  "code": "<BUSINESS_CODE>",
  "message": "<human readable>",
  "reference": "<optional doc link>"
}
```

## 版本与兼容
- 当前版本：v1 （示例）
- 策略：如 URL `/v1/` 或 Header `Accept-Version`。
- 不兼容变更需提升主版本；新增可选字段可在次版本内发布。

## 端点详情模板
> 按需复制多次，每个端点一节。

### GET /example (示例，替换)
- 描述：
- 请求参数：
  - Query：
    - `q` (string, optional) — 搜索关键词
  - Path：无
  - Header：鉴权/版本等，如需
- 请求示例：
```http
GET /example?q=foo HTTP/1.1
Authorization: Bearer <token>
Accept-Version: v1
```
- 响应 200：
```json
{
  "items": [],
  "total": 0
}
```
- 错误示例 400/401/500：参考统一错误体。
- 备注：分页/排序/限流等特殊约定。

## 变更记录（指向 changelog）
- 所有对外行为或契约变更必须同步至 `.project_info_for_ai/changelog.md`，此处可选列出最近几条或直接引用。
