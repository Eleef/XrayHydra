# **Development Guide**

Last Updated: 2026-01-02

## **1. Quick Start Commands (常用命令)**

* **Start Server (Web UI)**:
  ```bash
  python server.py
  # 或指定参数
  # python server.py --host 0.0.0.0 --port 8000 --reload
  ```

* **Run Tests (Testing)**:
  ```bash
  # 运行单元测试
  python -m pytest tests/test_lease_service.py -v
  
  # 运行并发集成测试
  python tests/test_lease_client.py
  ```

* **Environment Setup**:
  ```bash
  # 安装依赖
  pip install -r requirements.txt
  
  # 配置环境变量 (复制 .env.example 或直接创建)
  # 必填: LEASE_API_TOKEN (如果需要测试 auth)
  cp .env.example .env 
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
