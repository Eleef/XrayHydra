# **Xray-Prism Context Map**

Last Updated: 2026-03-07

## **1. Project Overview (项目简介)**

Xray-Prism 是一个 Python 编写的高性能并发代理管理工具，能够将 VPN 订阅中的每个节点映射为本地独立监听端口，实现 IP 的高并发使用。

## **2. Documentation Navigation (文档导航)**

### **📘 Product & Requirements (产品)**

* **[Requirements](../product/requirements.md)**: 产品需求文档 (PRD)，包含 Core Engine 和 Health Monitor 的功能定义。
* **[Frontend Requirements](../product/frontend_spec.md)**: Web 管理界面设计规范。

### **🏗️ Technical Architecture (技术)**

* **[System Architecture](../tech/architecture.md)**: 包含架构拓扑图、数据流向和核心数据结构。
* **[API Specifications](../tech/api_specs.md)**: 标准化 API 接口定义 (Lease, Health, Proxy, Subscription)。
* **[Python SDK](../../sdk/python/README.md)**: 基于 `openapi.json` 生成的 Python 客户端使用说明。
* **[Fetcher Design](../tech/designs/fetcher_design.md)**: 订阅获取模块设计。
* **[Health Monitor Design](../tech/designs/health_monitor_design.md)**: 健康监测系统实现细节。

### **🛠️ Guides & Norms (规范与指南)**

* **[Development Guide](guide/development.md)**: ⚡ 开发环境搭建与常用命令。

### **🚦 Development Status (状态)**

* **[Active Task](dev_status/active_task.md)**: 🚧 当前正在进行的上下文 (实时更新)。
* **[Todo List](dev_status/todo.md)**: 💡 待办事项与积压的灵感 (Backlog)。
* **[History Log](dev_status/history_log.md)**: 📜 已完成任务流水账。
* **[Changelog](../../CHANGELOG.md)**: 版本发布日志。

## **3. Key Environment Variables (关键环境)**

* `LEASE_API_TOKEN`: (Optional) 代理租约 API 认证令牌。
* `HOST`: Web 服务监听地址。
* `PORT`: Web 服务端口。
