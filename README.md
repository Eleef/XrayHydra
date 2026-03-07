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
  - **手动冷却 / 召回**: Web UI 和 OpenAPI 均支持按 workspace 手动冷却代理，并在需要时召回。
  - **LRU 负载均衡**: 智能分配最久未使用的代理端口。
- 🔀 **Mixed-Port 本地代理**: 每个本地端口由 Xray `socks` inbound 提供，客户端可对同一端口使用 `http://` 或 `socks5://`。
- 🪟🐧 **跨平台进程管理**: Windows / Linux 下都只回收本项目启动的 Xray 进程，不会全局误杀同机其他实例。
- 1️⃣ **Web 服务端口冲突检测**: 启动前会检查目标 `host:port` 是否可绑定，避免重复占用同一端口时才在运行阶段报错。
- 🎨 **现代化 UI**: 简约明亮的浅色三栏式布局，代理栏更宽，并支持 workspace 视角下的租约与冷却管理。
- ⚙️ **环境隔离**: 支持 `.env` 配置，支持 Bearer Token API 认证。

## 🚀 快速开始

### 1. 安装依赖

```bash
python -m venv .venv

# Windows
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Linux / macOS
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
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
# Windows
.venv\Scripts\python.exe server.py

# Linux / macOS
source .venv/bin/activate
python server.py
```
- 访问地址: `http://localhost:8000/`
- API 文档: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**命令行模式：**
```bash
# 获取并测试订阅节点
.venv\Scripts\python.exe main.py --url "YOUR_SUBSCRIPTION_URL" --test --keep-running
```

### 4. 测试

```bash
# 推荐：单元测试（不依赖本地已启动服务）
.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_fetcher.py tests/test_lease_service.py tests/test_runner.py tests/test_subscription_service.py tests/test_proxy_service.py -q

# 集成脚本：需要先启动 Web 服务，并准备可用代理
.venv\Scripts\python.exe tests/test_lease_client.py
```

### 5. Python / TypeScript SDK

项目已基于 `openapi.json` 生成 Python / TypeScript SDK，目录分别位于 `sdk/python` 与 `sdk/typescript`。

它的主要用途：
- 让 Python 调用方直接用类型化方法访问 API，而不是手写 `requests/httpx` 和 URL。
- 把服务端 OpenAPI 契约复用到客户端，减少字段名、鉴权头、请求结构漂移。
- 让前端工具、Node.js 脚本或其他 TypeScript 客户端也能直接复用同一份契约。
- 后续接口变更时，可以通过重新生成 SDK 同步给爬虫、调度器或外部业务系统。

```bash
# 重新生成 SDK
.venv\Scripts\python.exe scripts/generate_python_sdk.py

# 重新生成 TypeScript SDK
.venv\Scripts\python.exe scripts/generate_typescript_sdk.py

# 如需额外导出 OpenAPI 文件（默认不落盘，避免大 JSON 进入仓库）
.venv\Scripts\python.exe scripts/generate_python_sdk.py --write-openapi .\tmp\openapi.json

# 安装本地 SDK（开发模式）
.venv\Scripts\python.exe -m pip install -e .\sdk\python
```

更多使用说明见 `sdk/python/README.md` 和 `sdk/typescript/README.md`。

## 📌 行为说明

- 添加订阅时，如果订阅抓取或解析失败，API 会直接返回错误，不再创建“空订阅”记录。
- 代理健康状态只反映当前 Xray 实际可路由的端口；Xray 停止后会清空对应健康状态，避免租约系统分配失效端口。
- 客户端接口基于 FastAPI 生成标准 OpenAPI，包含稳定 `operationId`、请求示例和 Lease API 的标准 Bearer 安全方案声明。
- Python 客户端 SDK 已由 OpenAPI 契约生成，适合内部自动化脚本、测试工具和外部业务接入。
- TypeScript SDK 已由同一份 OpenAPI 契约生成，适合浏览器端控制台、Node.js 自动化和其他 TS 客户端接入。
- 本地代理端口采用 Xray `socks` inbound，以单端口 mixed-port 方式同时兼容 HTTP 和 SOCKS5 客户端；新客户端应优先使用接口返回的 `http_proxy_url` / `socks5_proxy_url`，不要只拿 `host:port` 自行猜协议。
- Web 前端右侧代理栏现在基于当前 workspace 展示租约与冷却状态，并支持对可用代理手动冷却、对冷却代理手动召回。
- `server.py` 现在会在启动前先检查目标端口是否已被占用；如果冲突，会直接提示当前地址不可用，并建议换端口或先停止占用进程。

## 🔌 代理租约 API 使用示例

代理租约 API 是专为自动化爬虫/脚本设计的接口，确保不同任务不会抢占同一个代理。

### 申请代理
```bash
curl -X POST http://localhost:8000/api/lease/acquire \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "amazon_crawler", "ttl": 60}'
```

典型返回：
```json
{
  "success": true,
  "lease_id": "uuid",
  "proxy_address": "127.0.0.1:10022",
  "proxy_scheme": "http",
  "supported_proxy_protocols": ["http", "socks5"],
  "http_proxy_url": "http://127.0.0.1:10022",
  "socks5_proxy_url": "socks5://127.0.0.1:10022",
  "socks5h_proxy_url": "socks5h://127.0.0.1:10022",
  "expires_at": "2026-03-07T03:10:00"
}
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
