# Changelog

本文件记录 Xray-Prism 项目的所有重要变更。

## [0.5.0] - 2025-12-25

### Added - 代理租约管理 API
- **api/services/lease_service.py**: 租约管理服务
  - Workspace 隔离：不同业务域可同时使用同一代理
  - TTL 租约：自动过期防止资源死锁
  - 客户端冷却：调用方指定冷却时间
  - LRU 选择：优先分配最久未使用的代理
  - 线程安全：threading.Lock 保证并发安全
- **api/routes/lease.py**: 租约 API 路由
  - `POST /api/lease/acquire` - 申请代理租约
  - `POST /api/lease/release` - 归还代理租约
  - `GET /api/lease/status` - 查看租约状态
  - `GET /api/lease/stats` - 获取租约统计
- **api/schemas/lease_models.py**: Pydantic 请求/响应模型
- **可配置 Token 认证**: 
  - 默认关闭，开箱即用
  - 设置 `LEASE_API_TOKEN` 环境变量启用

### Features
- 🔐 **Workspace 隔离**: 多业务域可并行使用同一代理池
- ⏱️ **TTL 租约**: 防止调用方崩溃导致资源死锁
- ❄️ **客户端冷却**: 调用方控制代理休息时间
- 📊 **LRU 负载均衡**: 自动选择最久未使用的代理
- 🔑 **可选认证**: 支持 Bearer Token 认证（默认关闭）
- 📝 **日志可配置**: 支持启用调试日志

### Technical
- 内存存储 + threading.Lock，无外部依赖
- 幂等设计：重复归还不报错
- 与 HealthService 集成：仅分配健康节点

## [0.4.0] - 2025-12-25


### Changed - UI 重新设计
- **全新简约明亮主题**: 从暗黑风格改为清新简约的浅色主题
  - 浅色配色方案（白色/浅灰色背景）
  - 更清晰的视觉层次和文字对比度
  - 柔和的阴影和边框效果
- **三栏并排布局**: 优化空间利用率
  - 左栏：订阅管理（260px 固定宽度）
  - 中栏：节点列表（自适应宽度）
  - 右栏：代理管理（自适应宽度）
  - 三栏独立滚动，互不影响
- **紧凑设计**: 大幅减少空间浪费
  - padding 从 1.5-2rem 降至 0.75-1rem
  - 列表项 padding 从 1rem 降至 0.5rem
  - 更小的图标尺寸（18px → 14-16px）
  - 更紧凑的按钮和徽章
  - 精简按钮文本（如"添加到代理"改为"添加"）
- **web/css/style.css**: 完全重写样式表
  - 使用 CSS Grid 三栏布局替代 Flexbox 嵌套
  - 统一的颜色变量系统
  - 优化的响应式断点
  - 更高效的滚动和性能优化
- **web/index.html**: 简化 HTML 结构
  - 移除不必要的嵌套容器
  - 直接三栏平级布局
  - 精简文本和标签

### Features
- 📐 **三栏并排**: 订阅、节点、代理一览无余
- 🌟 **明亮主题**: 清新简约的视觉风格
- 💾 **空间优化**: 紧凑设计，减少约40%的空白浪费
- 📱 **响应式优化**: 在不同屏幕尺寸下自适应布局

## [0.3.0] - 2025-12-25

### Added - 健康监测系统
- **health_monitor.py**: 核心健康监测模块
  - 实时代理连通性探测
  - 递进式罚时机制（5分钟 → 30分钟 → 150分钟）
  - 网络中断容错，避免误判
  - 可配置的测试目标和间隔
- **api/services/health_service.py**: 健康监测服务层
  - 后台监测线程管理
  - 健康状态持久化
  - 配置管理和同步
- **api/routes/health.py**: 健康监测 API 路由
  - `/api/health/status` - 获取所有代理健康状态
  - `/api/health/config` - 获取/更新监测配置
  - `/api/health/reset/{port}` - 重置指定代理状态
  - `/api/health/check` - 手动触发健康检测
- **data/health_config.json**: 默认健康监测配置
  - 国内外测试目标预设
  - 罚时等级配置

### Enhanced
- **models.py**: 添加健康状态相关模型
  - `HealthStatus` 枚举（healthy/degraded/disabled）
  - `ProxyHealthState` 数据类
- **api/schemas/models.py**: 添加健康监测 API 模型
  - `ProxyHealthResponse` - 代理健康状态响应
  - `HealthConfigResponse` - 配置响应
  - `HealthStatusListResponse` - 状态列表响应
- **proxy_service.py**: 集成健康监测
  - Xray 启动时自动开始健康监测
  - Xray 停止时自动停止监测
  - 动态同步代理列表
- **web/css/style.css**: 健康状态视觉样式
  - 健康指示器（绿色/黄色/灰色脉冲动画）
  - 右键菜单样式
  - 罚时计时器显示
- **web/js/api.js**: 健康监测 API 调用方法
  - 获取健康状态
  - 配置管理
  - 重置状态
- **web/js/app.js**: 前端健康监测集成
  - 实时健康状态刷新（10秒间隔）
  - 健康指示器显示
  - 右键菜单支持（重置健康状态）
  - 罚时倒计时显示

### Features
- 🏥 **实时健康监测**: 后台自动检测代理连通性
- 🔴 **自动剔除**: 失败节点自动进入冷却期，不影响下游
- 🟢 **自动恢复**: 罚时结束后自动重新检测
- 📉 **递进罚时**: 5min → 30min → 150min 指数递增
- 🌐 **网络容错**: 检测本机网络状态，避免误判
- 🎯 **可配置目标**: 支持自定义测试地址，预设国内外地址
- 🔄 **手动重置**: 用户可右键重置节点健康状态
- 📊 **状态可视化**: Web 界面彩色指示器（绿/黄/灰）

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

