# **Project History Log**

> **Rule**: 保持倒序排列，最新的内容放顶部。
> 记录已完成任务的摘要和关键决策。

Last Updated: 2026-01-02

## **v0.5.0 - Proxy Lease API Implementation (2026-01-02)**

*   **Feature**: 完成了代理租约管理 API (`/api/lease/*`) 的开发。
    *   实现了 Workspace 隔离、TTL 自动过期、客户端冷却机制。
    *   实现了 LRU (Least Recently Used) 代理分配策略。
*   **Fix**: 修复了健康监测系统 (`health_monitor.py`) 的默认测试目标问题。
    *   将默认测试目标从 `baidu.com` 更换为 `ip-api.com`，解决了因百度阻断导致的误判。
*   **Infrastructure**: 引入了 `.env` 环境配置支持 (`python-dotenv`)。
*   **Documentation**: 全面更新了 SPEC 文档和 README。

## **v0.4.0 - UI Redesign & Health Monitor (2025-12-25)**

*   **UI**: 重构了 Web 前端界面。
    *   采用了浅色明亮主题。
    *   实现了三栏并排布局 (Subscriptions / Nodes / Proxies)。
*   **Feature**: 实现了核心健康监测引擎。
    *   支持递进式罚时 (5m -> 30m -> 150m)。
    *   支持网络容错检测。

## **v0.2.0 - Initial Web Interface**

*   **Feature**: 提供了基于 FastAPI 及其原生 HTML/JS 的基础 Web 管理界面。
