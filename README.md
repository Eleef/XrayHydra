# Xray-Prism 🌐

将 VPN 订阅中的每个节点映射为本地独立端口，实现并发使用不同 IP。内置强大的健康监测系统与代理租约管理 API，专为自动化采集与多任务并发场景设计。

## 🌟 功能特性

- 🧪 **全协议支持**: 完美解析 VMess / VLess / Shadowsocks / Trojan 协议（含 Clash YAML 格式）。
- 🏗️ **端口映射**: 每个节点映射为独立本地端口，路由 1 对 1 硬绑定，真正实现多 IP 并发。
- 🏥 **自动健康监测**: 
  - 实时连通性探测，自动剔除失效节点。
  - **递进式罚时**: 5min → 30min → 150min，确保资源高效利用。
  - 网络中断容错，避免误判。
- 🔑 **代理租约 API (v0.5.0)**:
  - **Workspace 隔离**: 不同业务域可同时使用同一代理，互不干扰。
  - **TTL 机制**: 租约自动过期，防止调用方崩溃导致资源僵死。
  - **客户端冷却**: 支持自定义回收后的冷却时间，精细控制使用频率。
  - **LRU 负载均衡**: 智能分配最久未使用的代理端口。
- 🎨 **现代化 UI**: 简约明亮的浅色三栏式布局，状态一目了然。
- ⚙️ **环境隔离**: 支持 `.env` 配置，支持 Bearer Token API 认证。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 环境配置

直接编辑根目录下的 `.env` 文件进行配置：
```env
LEASE_API_TOKEN=your_secret_token
PORT=8000
```
在 `.env` 中你可以配置：
- `LEASE_API_TOKEN`: 启用租约 API 的认证 Token
- `HOST` / `PORT`: Web 服务器启动参数

### 3. 运行项目

**Web 管理界面（推荐）：**
```bash
python server.py
```
- 访问地址: `http://localhost:8000/`
- API 文档: `http://localhost:8000/docs`

**命令行模式：**
```bash
# 获取并测试订阅节点
python main.py --url "YOUR_SUBSCRIPTION_URL" --test --keep-running
```

## 🔌 代理租约 API 使用示例

代理租约 API 是专为自动化爬虫/脚本设计的接口，确保不同任务不会抢占同一个代理。

### 申请代理
```bash
curl -X POST http://localhost:8000/api/lease/acquire \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "amazon_crawler", "ttl": 60}'
```

### 归还代理（带 5 分钟冷却）
```bash
curl -X POST http://localhost:8000/api/lease/release \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "amazon_crawler", 
    "proxy_address": "127.0.0.1:10001", 
    "cooldown_seconds": 300
  }'
```

## 🛠️ 项目结构

```
XrayHydra/
├── server.py            # Web 服务入口（支持 .env）
├── main.py              # CLI 核心逻辑
├── .env                 # 环境配置文件
├── api/                 # Web API 层
│   ├── routes/          # 路由 (lease, health, proxies, ...)
│   ├── services/        # 业务逻辑 (lease_service, health_service, ...)
│   └── schemas/         # Pydantic 模型
├── src/xray_prism/      # 核心逻辑模块
│   ├── health_monitor.py# 健康监测核心
│   ├── runner.py        # Xray 进程管理
│   └── ...
├── web/                 # 前端 (HTML/JS/CSS)
└── tests/               # 完整的测试组件 (Unit/Integration/Demo)
```

## 📦 依赖项

- Python 3.10+
- `fastapi`, `uvicorn`, `pydantic` - 高性能 Web 框架
- `python-dotenv` - 环境配置管理
- `requests`, `pyyaml` - 网络与数据解析
- `Xray-core` - 自动下载管理
