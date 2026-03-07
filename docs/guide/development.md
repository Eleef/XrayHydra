# **Development Guide**

Last Updated: 2026-03-07

## **1. Quick Start Commands (常用命令)**

* **Start Server (Web UI)**:
  ```bash
  # Windows
  .venv\Scripts\python.exe server.py

  # Linux / macOS
  source .venv/bin/activate
  python server.py
  # 或指定参数
  # python server.py --host 0.0.0.0 --port 8000 --reload
  ```
  OpenAPI 文档地址：
  `http://127.0.0.1:8000/docs`
  `http://127.0.0.1:8000/openapi.json`

* **Run Tests (Testing)**:
  ```bash
  # 推荐：运行核心单元测试（不依赖本地服务）
  .venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_fetcher.py tests/test_lease_service.py tests/test_runner.py tests/test_subscription_service.py tests/test_proxy_service.py -q
  
  # 运行租约 API 集成脚本（要求本地 server 已启动，且有可用健康代理）
  .venv\Scripts\python.exe tests/test_lease_client.py

  # 运行 OpenAPI / SDK 相关测试
  .venv\Scripts\python.exe -m pytest tests/test_openapi.py tests/test_python_sdk.py -q
  ```

* **Environment Setup**:
  ```bash
  # 创建项目虚拟环境
  python -m venv .venv

  # 安装依赖
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  
  # 配置环境变量 (复制 .env.example 或直接创建)
  # 必填: LEASE_API_TOKEN (如果需要测试 auth)
  cp .env.example .env 
  ```

* **Generate Python SDK**:
  ```bash
  # 从当前 FastAPI OpenAPI 契约重新生成 Python SDK
  .venv\Scripts\python.exe scripts/generate_python_sdk.py

  # 如需额外落盘 OpenAPI JSON，显式指定输出路径
  .venv\Scripts\python.exe scripts/generate_python_sdk.py --write-openapi .\tmp\openapi.json

  # 安装到当前虚拟环境
  .venv\Scripts\python.exe -m pip install -e .\sdk\python
  ```

* **Generate TypeScript SDK**:
  ```bash
  # 生成 source-first TypeScript SDK
  .venv\Scripts\python.exe scripts/generate_typescript_sdk.py

  # 如需本地编译验证
  cd sdk\typescript
  npm install
  npm run build
  ```

## **2. Environment Variables (环境变量)**

配置位于根目录 `.env` 文件中：

| Variable | Description | Default |
| :---- | :---- | :---- |
| `LEASE_API_TOKEN` | 代理租约 API 的认证 Token，为空则不启用认证 | (Empty) |
| `HOST` | Web 服务器监听地址 | `127.0.0.1` |
| `PORT` | Web 服务器端口 | `8000` |
| `DEBUG` | 调试模式开关 | `false` |

## **3. Project Structure**

* `src/xray_prism/`: 核心业务逻辑 (Fetcher, Parser, Monitor)。
* `api/`: FastAPI 路由与服务层。
* `web/`: 静态前端资源。

## **4. Runtime Notes (运行时约束)**

* Xray 进程管理支持 Windows / Linux，且只回收当前项目自己启动的 Xray 子进程。
* `server.py` 会在启动前检查目标 `host:port` 是否可绑定；如果端口被占用，会直接退出并提示当前地址不可用，而不是等到运行期再抛底层 bind 错误。
* 健康状态会和当前正在运行的代理端口同步；当 Xray 停止时，对应健康状态会被清空，避免租约系统继续发放失效端口。
* 新建订阅时采用“抓取成功后再落盘”的语义，抓取或解析失败不会生成空订阅记录。
* 当前本地代理端口由 Xray `socks` inbound 提供，单端口同时兼容 HTTP 与 SOCKS5 客户端；例如同一个 `127.0.0.1:10022` 可写成 `http://127.0.0.1:10022` 或 `socks5://127.0.0.1:10022`。
* 推荐始终通过仓库内 `.venv` 的 Python 执行服务和测试，避免系统 Python / Anaconda 环境污染。
* 面向客户端的接口契约以 `/openapi.json` 为准；Lease API 的鉴权会在 OpenAPI 中暴露为 `LeaseBearerAuth`。
* `sdk/python` 是从 OpenAPI 生成的 Python 客户端；服务端接口发生变化后，应同步重新生成并运行 `tests/test_python_sdk.py`。
* `sdk/typescript` 是从同一份 OpenAPI 契约生成的 TypeScript 客户端，适合浏览器端或 Node.js 调用方。
* 为避免大体积 JSON 影响 AI 上下文和代码审查，仓库默认不保留 `sdk/python/openapi.json`；只有在调试或对外分发契约文件时才按需导出。
* 新客户端不应只根据 `host:port` 猜测代理协议，应优先使用 API 返回的 `http_proxy_url` / `socks5_proxy_url` / `socks5h_proxy_url` 字段；如果目标是域名且本机 DNS 不可信，优先使用 `socks5h_proxy_url`。
* Web 前端的代理栏与租约栏共享当前 workspace 选择器；若要验证“手动冷却/召回”，先通过 Lease Playground 或客户端脚本创建至少一个 workspace 记录。
