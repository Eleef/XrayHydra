# **Active Task Context (Live State)**

Last Updated: 2026-03-07

## **🎯 Current Objective (当前目标)**

* 完成跨平台运行时修复、OpenAPI 契约标准化、mixed-port 代理兼容改造与 Python SDK 落地，并同步代码文档。

## **🧩 Context Dump (关键上下文)**

* **相关文件**:
  * `src/xray_prism/runner.py`
  * `src/xray_prism/generator.py`
  * `api/services/subscription_service.py`
  * `api/services/proxy_service.py`
  * `api/routes/lease.py`
  * `api/routes/proxies.py`
  * `api/schemas/lease_models.py`
  * `api/schemas/models.py`
  * `scripts/generate_python_sdk.py`
  * `sdk/python/`
  * `docs/guide/development.md`
  * `docs/tech/api_specs.md`
  * `docs/tech/architecture.md`
* **最近修改**: 修复跨平台 Xray 进程回收、订阅创建原子性、代理健康状态同步；补齐 OpenAPI 标准化元数据并生成 Python SDK，同时将本地代理端口切换为 mixed-port 语义并显式返回 HTTP/SOCKS5 URL。

## **🚧 Progress Checklist (进度)**

* [x] 修复跨平台 Xray 进程管理为项目级回收。
* [x] 修复订阅创建失败仍落空记录的问题。
* [x] 修复代理/Xray/健康状态不同步导致的失效端口泄露问题。
* [x] 补齐客户端 OpenAPI 契约（Bearer/Auth、operationId、示例、错误模型）。
* [x] 将本地代理端口切换为 Xray `socks` inbound，以单端口同时兼容 HTTP 与 SOCKS5。
* [x] 在 Proxy / Lease API 中补充 `proxy_scheme`、`http_proxy_url`、`socks5_proxy_url` 等显式客户端字段。
* [x] 基于 OpenAPI 生成 Python SDK 并增加契约回归测试。
* [x] 更新开发与技术文档。

## **💥 Known Issues / Blockers (遇到的阻碍)**

* 无

## **⏭️ Next Actions (下一步计划)**

1.  等待用户验收 mixed-port 兼容改造与 SDK 契约更新结果。
2.  若继续迭代，优先补充 TypeScript SDK、前端“复制 HTTP/SOCKS5 地址”按钮，或整理 `tests/test_lease_client.py` 的默认收集行为。
