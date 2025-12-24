# Changelog

本文件记录 Xray-Prism 项目的所有重要变更。

## [0.2.0] - 2025-12-24

### Added
- **Web 管理界面**: 现代化的暗色主题 Web UI，支持通过浏览器管理所有功能
- **server.py**: Web 服务入口脚本，支持命令行参数配置
- **api/**: 完整的 FastAPI 后端层
  - **main.py**: FastAPI 应用，配置 CORS、路由和静态文件服务
  - **routes/**: RESTful API 路由 (subscriptions, nodes, proxies, system)
  - **schemas/**: Pydantic 数据验证模型
  - **services/**: 业务逻辑层 (subscription_service, proxy_service)
- **web/**: 前端静态文件
  - **index.html**: 主界面，包含订阅管理、节点列表、代理管理三大模块
  - **css/style.css**: 现代暗色主题样式，紫色渐变配色
  - **js/api.js**: API 客户端封装
  - **js/components.js**: UI 组件渲染函数
  - **js/app.js**: 主应用逻辑和状态管理
- **data/**: JSON 数据存储目录 (subscriptions.json, active_proxies.json)

### Features
- 📋 订阅管理：添加、删除、刷新订阅
- 📡 节点列表：查看、搜索、选择节点
- 🚀 代理管理：添加节点到代理列表、测试连通性、查看出口 IP
- ⚡ Xray 控制：一键启动/停止/重启 Xray 服务
- 📊 实时状态监控：自动刷新系统状态
- 🎨 响应式设计：支持桌面和移动设备

### Enhanced
- **generator.py**: 添加 `generate_with_mappings` 和 `generate_and_save_with_mappings` 方法支持外部端口映射
- **requirements.txt**: 添加 FastAPI、uvicorn、pydantic 依赖
- **README.md**: 更新文档，添加 Web 界面使用说明

### Fixed
- 修复 `subscription_service.py` 中 ProxyNode 字段映射问题 (path/host/service_name)
- 修复 `proxy_service.py` 中 PortMapping 创建方式和 TestResult 字段引用

## [0.1.0] - 2025-12-23

### Added
- **models.py**: 数据模型层，定义 Protocol/NetworkType 枚举、ProxyNode/TestResult/PortMapping 数据类
- **fetcher.py**: 网络层，支持 URL 获取和文件读取，自动 Base64 解码（含 URL-safe 和 padding 修复）
- **parser.py**: 核心解析层，支持 VMess/VLess/Shadowsocks/Trojan 协议解析，具备容错机制
- **generator.py**: 配置生成层，生成 Xray config.json，每节点一端口，路由 1 对 1 硬绑定
- **runner.py**: 进程管理层，自动查找/下载 Xray 内核，优雅管理子进程生命周期
- **tester.py**: 验证测试层，ThreadPoolExecutor 并发测试，获取出口 IP 和延迟
- **main.py**: 主程序入口，argparse CLI，完整执行流程，信号处理和优雅退出

