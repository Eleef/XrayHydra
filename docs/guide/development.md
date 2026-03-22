# **Development Guide**

Last Updated: 2026-03-22

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
  一键启动脚本：
  ```bash
  # Windows（支持双击）
  start_windows.bat

  # Linux
  chmod +x start_linux.sh
  ./start_linux.sh

  # 透传参数
  start_windows.bat --port 8010
  ./start_linux.sh --host 0.0.0.0 --port 8010
  ```
  说明：
  `start_windows.bat` / `start_linux.sh` 会优先复用项目内 `.venv`；
  如果虚拟环境不存在，则自动创建并安装 `requirements.txt`。
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

* **Run Real Validation Flow (真实联调验收)**:
  ```bash
  # 前置条件：
  # 1) 本地 server 已启动
  # 2) 你有可用真实订阅 URL
  #
  # 这条脚本覆盖：
  # 真实订阅节点 -> 节点测试 -> 自动筛选成功节点 -> 加入代理池 -> 代理再测试

  # 基础用法（保留结果，便于手工检查）
  .venv\Scripts\python.exe scripts\scratch\run_real_node_to_proxy_flow.py ^
    --base-url http://127.0.0.1:8000 ^
    --subscription-url "<REAL_SUBSCRIPTION_URL>" ^
    --subscription-name "real-flow-check" ^
    --max-nodes 20

  # 验收后自动清理（删除本次新增订阅与代理）
  .venv\Scripts\python.exe scripts\scratch\run_real_node_to_proxy_flow.py ^
    --base-url http://127.0.0.1:8000 ^
    --subscription-url "<REAL_SUBSCRIPTION_URL>" ^
    --cleanup-subscription ^
    --cleanup-added-proxies
  ```

## **2. Node Filter Notes**

*   节点栏现在提供一个“排除关键词”区域（输入 + 标签），可以填 `香港` / `Hongkong` / `Hong Kong` 等关键词组合。输入多个关键字可使用逗号或换行，系统会优先过滤掉 `node.name` / `node.address` 里匹配这些关键词的节点，避免加入非目标出口。
*   每个排除关键词标签后会显示括号中的匹配数量（例如 `Hong Kong (5)`），数量反映当前节点列表中符合该关键词的项数，节点刷新或关键词更新后会自动同步，方便判断筛选器的过滤力度。
*   关键词仅指字符串本身，会以 `xray-prism.nodeExclusionKeywords` 写入浏览器 `localStorage`，有效期和其它本地状态一致；刷新页面后依然生效，但它只保存关键词列表（不带勾选结果、测试状态或排序）。
*   排除逻辑在搜索 / 已有 `onlyAvailable` / `onlyNotInPool` / `onlyFailed` 筛选之前执行，默认持续联动当前排序，关闭某个标签即可立即恢复对应节点。
*   节点测试进度条（工具栏总进度 + 行内追踪）展示完成节点 / 目标数量、成功/失败计数和当前活跃目标；前端会先调用 `POST /api/nodes/test-jobs` 创建测试任务，再轮询 `GET /api/nodes/test-jobs/{job_id}`，使用其中的 `status`、`progress_percent`、`active_target`、`target_index`、`target_total`、`current_target_completed`、`current_target_total`、`success_count`、`failed_count` 等字段驱动真实进度，替代原有的模拟推进逻辑。
*   代理栏现在提供手动 `出口IP去重` 按钮。按钮只在当前代理池存在重复出口 IP 时启用，并显示建议禁用数量；点击后会先弹出重复项预览，明确展示每组的“保留 / 禁用”代理，只有用户确认后才会把重复项标记为 `去重禁用`。
*   `去重禁用` 代理不会从代理池删除，因此节点栏仍会把对应节点显示为“已入池”，避免后续被重复加入；但这些代理不会进入 Xray 运行配置，也不会参与租约、健康测试或代理测试。

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
* Web 前端的代理栏与租约栏共享顶部范围选择器，并固定提供“所有代理”视图；即使还没有任何 workspace 记录，也可以在该视图下运行“测试全部”，并把失败代理加入全局冷却池。
* 在具体 workspace 视图下，代理栏支持手动冷却/召回；在租约的冷却池列表中，同样可以按单条记录执行召回。
* 具体 workspace 视图会展示“当前 workspace + 全局冷却”两个来源的冷却记录；其中全局冷却只会出现在列表里，不计入 workspace 摘要计数。
