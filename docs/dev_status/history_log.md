# **Project History Log**

> **Rule**: 保持倒序排列，最新的内容放顶部。
> **Purpose**: 记录已完成任务的**技术决策**、**关键架构变更**和**踩坑记录**，作为开发者的长期记忆。
> **Difference**: CHANGELOG.md 面向用户（What），这里面向开发者（How & Why）。

Last Updated: 2026-03-07

## **Mixed-Port Proxy Compatibility (2026-03-07)**

### **1. Switch Local Proxy Ports to Xray Socks Inbound**
*   **Issue**: 旧实现把本地端口生成为纯 HTTP inbound，客户端一旦把 `host:port` 当作 SOCKS5 使用，就会出现“端口开着但代理全超时”的错觉。
*   **Decision**: 将本地端口统一切换为 Xray `socks` inbound，利用其对 HTTP/SOCKS 的兼容能力，把同一端口升级为 mixed-port 语义。
*   **Why**: 保留“一节点一端口”模型，同时减少客户端协议误用和接入成本。

### **2. Make Proxy Protocol Explicit in API**
*   **Issue**: 仅返回 `127.0.0.1:10022` 会迫使调用方自己猜这个端口到底该按 HTTP 还是 SOCKS5 使用。
*   **Decision**: 在 Proxy / Lease 响应中增加 `proxy_scheme`、`supported_proxy_protocols`、`http_proxy_url`、`socks5_proxy_url`。
*   **Why**: 把 mixed-port 能力变成正式客户端契约，而不是口头约定。

## **OpenAPI Contract & Python SDK (2026-03-07)**

### **1. Standardized Client-facing OpenAPI**
*   **Issue**: 虽然 FastAPI 会自动导出 OpenAPI，但客户端生成仍缺少稳定 `operationId`、标准 Bearer 安全声明和足够的 schema 示例。
*   **Decision**: 在路由和 schema 层补齐面向客户端的契约元数据，并增加 OpenAPI 回归测试。
*   **Why**: 让 `openapi.json` 从“可查看文档”升级为“可稳定生成客户端”的正式接口契约。

### **2. Generated Python SDK**
*   **Issue**: 调用方如果直接手写 `requests/httpx`，会重复维护 URL、请求模型和鉴权逻辑。
*   **Decision**: 以服务端 OpenAPI 为源，新增 `scripts/generate_python_sdk.py`，在仓库内生成 `sdk/python`。
*   **Why**: 降低客户端接入成本，并让后续接口演进可以通过重新生成 SDK 对齐。

### **3. Keep OpenAPI JSON Out of Repo**
*   **Issue**: `sdk/python/openapi.json` 体积较大，容易污染 AI 上下文窗口，也会增加代码审查噪音。
*   **Decision**: 生成脚本默认不再把 OpenAPI JSON 落盘到 SDK 目录，仅在显式传入 `--write-openapi` 时按需导出。
*   **Why**: 保留 SDK 生成能力，同时避免把大型契约文件当作常驻源码资产维护。

## **Runtime Consistency Fixes (2026-03-07)**

### **1. Project-scoped Xray Process Lifecycle**
*   **Issue**: 旧实现通过全局 `taskkill/pkill` 清理 Xray，存在误杀同机其他 Xray 实例的风险。
*   **Decision**: 改为项目级进程元数据跟踪，仅接管并停止本项目自己启动的 Xray 进程。
*   **Why**: 该策略在 Windows / Linux 下都可工作，并且不会破坏同机其他代理环境。

### **2. Atomic Subscription Creation**
*   **Issue**: 创建订阅时先写入订阅记录，再抓取节点；抓取失败会留下“空成功订阅”。
*   **Decision**: 调整为先抓取解析，再一次性写入订阅和节点；刷新时也只在新节点准备完成后替换旧节点。
*   **Why**: 让 API 语义与持久化结果一致，避免 UI 和调用方面对脏数据做额外补偿。

### **3. Proxy / Health / Lease State Alignment**
*   **Issue**: 删除代理或停止 Xray 后，健康状态文件仍可能保留旧端口，LeaseManager 会继续把它们当作可用。
*   **Decision**: 统一由 `ProxyService` 按当前真实运行端口同步健康状态；Xray 停止时清空可分配健康端口。
*   **Why**: 让租约分配只依赖“当前真的可路由”的端口，而不是历史缓存。

## **v0.5.1 - Lease Web UI (Phase 3) (2026-01-02)**

### **1. Lease Management Panel Implementation**
*   **Goal**: 在 Web UI 中实现代理租约的可视化监控与调试能力。
*   **Entry Point**: 在右侧 Proxies 面板顶部添加 Tab 切换 (代理 | 租约)，而非独立页面。
*   **UI Components**:
    *   **Dashboard**: 三个统计卡片（可用/活跃/冷却），5 秒自动刷新。
    *   **Active Leases Monitor**: 列表展示活跃租约，带实时倒计时。
    *   **Cooldown Pool**: 列表展示冷却中的代理。
    *   **Playground**: 调试表单，支持 Acquire/Release 操作并显示 JSON 响应。
*   **Key Decisions**:
    *   **Tab-based Design**: 避免页面跳转，保持单页应用体验。
    *   **Auto-fill Proxy Address**: Acquire 成功后自动填充 Release 所需的 proxy_address，提升调试效率。
    *   **Fixed Cooldown**: Release 操作硬编码 300s 冷却时间，简化 UI。
*   **Files Changed**:
    *   `web/js/api.js`: 新增 4 个 Lease API 客户端方法。
    *   `web/index.html`: 添加 Tab 切换和 Lease 面板 HTML。
    *   `web/js/app.js`: 添加 Tab 切换逻辑和 Lease 数据渲染。
    *   `web/css/style.css`: 新增 Tab 系统和 Lease 相关样式。

## **v0.5.0 - Proxy Lease API & DocOps (2026-01-02)**

### **1. Proxy Lease API Implementation**
*   **Goal**: 解决多爬虫任务并发争抢同一代理导致 IP 被封的问题。
*   **Key Decisions**:
    *   **In-Memory State**: 仅使用内存存储 Lease 状态，不引入 Redis，保持项目轻量化。
    *   **Threading Lock**: 在 `LeaseManager` 中使用粗粒度锁 (`threading.Lock`) 确保并发安全，实测支持 50+ 并发请求。
    *   **Workspace Isolation**: 引入 `workspace_id` 概念，允许不同业务域复用同一 IP（软隔离），而非物理隔离。
    *   **LRU Strategy**: 优先分配 `last_used_at` 最早的节点，实现简单的负载均衡。

### **2. Health Monitor Fix**
*   **Issue**: 本地测试时，所有代理均为 Healthy，但健康监测显示 Disabled。
*   **Root Cause**: 健康监测默认使用 `baidu.com` 作为测试目标，而该目标对 datacenter IP 极不友好（或被 GFW 策略影响），导致误判。
*   **Fix**: 将默认测试目标统一为 `http://ip-api.com/json`，与 Web UI 手动测试逻辑保持一致。修改了 `health_monitor.py` 和 `health_config.json`。

### **3. DocOps Restructuring**
*   **Goal**: 规范化文档管理，避免文档腐烂。
*   **Changes**:
    *   废弃 `docs/specs/` 目录。
    *   迁移 Spec 到 `docs/product/` (Requirements) 和 `docs/tech/` (Architecture/API)。
    *   引入 `history_log.md` 和 `todo.md` 作为标准开发过程文档。

## **v0.4.0 - UI Redesign & Health Monitor (2025-12-25)**

### **1. UI Overhaul**
*   **Decision**: 放弃之前的深色极客风，改为浅色三栏布局。
*   **Why**: 旧版 Flexbox 嵌套过深，维护困难。新版采用 CSS Grid 实现 Subscription | Nodes | Proxies 三栏，信息密度更高。

### **2. Health Engine**
*   **Algorithm**: 采用指数退避罚时 (5m -> 30m -> 150m)。
*   **Resilience**: 增加了 `check_network_connectivity`，防止本机断网导致全量代理被剔除。

## **v0.2.0 - Initial Web Interface**
*   **Tech Stack**: 选择 FastAPI + Vanilla JS。避免引入 React/Vue 构建流程，保持 Python 单语言栈的纯粹性。
