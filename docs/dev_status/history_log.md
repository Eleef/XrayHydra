# **Project History Log**

> **Rule**: 保持倒序排列，最新的内容放顶部。
> **Purpose**: 记录已完成任务的**技术决策**、**关键架构变更**和**踩坑记录**，作为开发者的长期记忆。
> **Difference**: CHANGELOG.md 面向用户（What），这里面向开发者（How & Why）。

Last Updated: 2026-01-02

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
