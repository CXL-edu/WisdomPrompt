# API Collaboration / 联调细则

## 文档摘要

补充 AGENTS.md 中的高层规则，聚焦 API 设计与联调细则（错误体、版本、Mock）。文档路径：`.project_info_for_ai/api-collaboration.md`（单一来源），被主文档引用，不再重复项目目录规则。

---

## 目录索引

1. [核心原则](#核心原则)
2. [API 文档要点](#api-文档要点)
3. [API 设计规范补充](#api-设计规范补充)
4. [联调与 Mock 策略](#联调与-mock-策略)
5. [参考与延伸阅读](#参考与延伸阅读)

---

## 核心原则

- **API-First**：先定契约（`api_development.md` / OpenAPI），再实现。契约是单一事实来源。
- **并行开发**：后端可先提供 Mock/占位实现，前端可基于契约生成类型或使用 Mock 独立开发。
- **文档即契约**：API 描述纳入版本控制与评审，并与实现保持同步。

---

## API 文档要点（api_development.md）

该文档是前后端联调的**核心契约**，应包含以下内容（可根据项目规模裁剪，但建议至少包含带 ★ 的项）：

### 必备内容

- **★ 接口列表**：接口名称、请求方法、路径（URL）、简要说明。
- **★ 请求参数**：参数名、类型、必填/可选、默认值、说明；若有枚举或取值范围需写明。
- **★ 响应格式**：成功时的数据结构（字段说明、类型、示例）；若为分页，约定分页字段与含义。
- **★ 错误与状态码**：HTTP 状态码含义、业务错误码（若有）及说明；统一错误体格式（见第 6 节）。
- **认证与安全**：接口是否需鉴权、鉴权方式（如 Bearer、API Key）、获取与使用方式（可引用项目内文档链接）。

### 建议内容

- **版本与兼容**：当前 API 版本、版本策略（如 URL 路径 `/v1/`、Header）、向后兼容与弃用说明。
- **变更记录**：与 `changelog.md` 可联动，在本文档中保留「最近接口变更」小结，或直接引用 changelog。

### 格式建议

- 若使用 **OpenAPI（Swagger）**：可维护 YAML/JSON 描述文件，并保证与 `api_development.md` 中文字说明一致；用同一份 OpenAPI 生成 Mock、类型或客户端代码。
- 文档内命名风格建议统一（如请求/响应体字段使用 lowerCamelCase），与前端/后端实际使用一致。

---

## API 设计规范补充

以下为联调时易产生歧义的部分，建议在 `api_development.md` 或团队规范中统一。

### 错误响应统一格式

- **分层设计**：**HTTP 状态码** 表示协议层结果（2xx 成功、4xx 客户端错误、5xx 服务端错误），**业务错误码** 表示具体业务失败原因。
- **响应体建议**：包含 `code`（业务错误码）、`message`（错误描述）、必要时 `reference`（文档或排查链接）。字段命名建议统一 lowerCamelCase。
- **避免**：所有请求都返回 200、仅用 body 表示错误，易导致前端与监控难以统一处理。

### 版本与兼容

- 仅在 **不兼容变更**（如删除/重命名字段、改变类型）时升级主版本；新端点或新增可选参数可用次版本。
- 建议提前约定版本策略（如 URL `/v1/`、Header `Accept-Version`），并在文档中写明当前版本与弃用计划。

### 文档与实现一致

- 将 API 描述纳入版本控制与 Code Review；若有 OpenAPI，可通过 CI 做契约测试或与实现对比，减少文档与代码漂移。

## 联调与 Mock 策略

- **Mock 用途**：后端未就绪时，前端可基于契约用 Mock 数据或 Mock 服务（如 MSW、Mirage.js、或 Postman Mock Server）独立开发与自测。
- **契约一致**：Mock 的请求/响应格式应与 `api_development.md` 或 OpenAPI 一致，避免联调时大量返工。
- **环境区分**：Mock 仅用于本地或测试环境，上线前确认关闭或切换为真实 API，且 Mock 配置不随生产构建发布。

## 参考与延伸阅读

- **API 文档与 OpenAPI**：  
  [OpenAPI 最佳实践](https://learn.openapis.org.cn/best-practices.html)、  
  [API 文档最佳实践](https://swagger.org.cn/blog/api-documentation/api-documentation-best-practices)
- **契约优先与代码生成**：  
  [Contract-First API Development](https://devguide.dev/blog/contract-first-api-development)、  
  [OpenAPI 与 API-First 开发](https://openapispec.com/docs/how/how-can-openapi-support-api-first-development/)
- **前后端解耦与 Mock**：  
  [使用 Mock 解耦前后端开发](https://www.port.io/blog/decoupling-backend-from-frontend-development-using-mocks)、  
  [MSW - API Mocking](https://mswjs.io/)
- **REST 版本与错误规范**：  
  [REST API 版本控制](https://restful.p2hp.com/learn/versioning)、  
  [RESTful API 业务错误处理规范](https://jianghushinian.cn/2023/03/04/how-to-standardize-the-handling-of-restful-api-business-errors/)
- **Changelog 与版本**：  
  [版本规范与 Changelog](https://developer.aliyun.com/article/1126245)

---*本文档旨在为前后端及多 Agent 协作提供统一约定，减少联调摩擦并提高开发效率。可根据项目实际情况增删章节或链接到更细的规范文档。*
