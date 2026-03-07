# **Xray-Prism API Specifications**

Last Updated: 2026-03-07

## **1. Proxy Lease API (代理租约)**

> Base Path: `/api/lease`
> Auth: Optional Bearer Token (Configured via `LEASE_API_TOKEN`)
> OpenAPI: `/openapi.json`（包含标准 `http bearer` 安全方案 `LeaseBearerAuth`）

### **Acquire Lease**
*   **Endpoint**: `POST /acquire`
*   **OperationId**: `acquireLease`
*   **Summary**: 申请一个可用代理。
*   **Request**:
    ```json
    {
      "workspace_id": "string", // 业务标识
      "ttl": 60                 // 租约有效期(秒)
    }
    ```
*   **Response (200)**:
    ```json
    {
      "success": true,
      "lease_id": "uuid",
      "proxy_address": "127.0.0.1:10000",
      "proxy_scheme": "http",
      "supported_proxy_protocols": ["http", "socks5"],
      "http_proxy_url": "http://127.0.0.1:10000",
      "socks5_proxy_url": "socks5://127.0.0.1:10000",
      "socks5h_proxy_url": "socks5h://127.0.0.1:10000",
      "expires_at": "timestamp"
    }
    ```
*   **Response (503)**: 无可用健康代理。

> Note: 本地代理端口采用 Xray `socks` inbound，因此单端口同时兼容 HTTP 和 SOCKS5；`proxy_scheme` 当前保留为默认的向后兼容入口，调用方应优先使用显式 URL 字段。

### **Release Lease**
*   **Endpoint**: `POST /release`
*   **OperationId**: `releaseLease`
*   **Summary**: 归还代理并设置冷却。
*   **Request**:
    ```json
    {
      "workspace_id": "string",
      "proxy_address": "127.0.0.1:10000",
      "cooldown_seconds": 300   // 冷却时间(秒)
    }
    ```

### **Get Stats**
*   **Endpoint**: `GET /stats`
*   **OperationId**: `getLeaseStats`
*   **Summary**: 系统统计信息（可用数、活跃租约、Top 使用率）。

---

## **2. Health Monitoring API (健康监测)**

> Base Path: `/api/health`

### **Get Status**
*   **Endpoint**: `GET /status`
*   **Response**:
    ```json
    {
      "states": [
        {
          "proxy_port": 10000,
          "status": "healthy", // or degraded, disabled
          "failure_count": 0,
          "latency_ms": 150
        }
      ],
      "total": 50,
      "healthy_count": 45
    }
    ```

### **Manual Check**
*   **Endpoint**: `POST /check`
*   **Summary**: 立即触发一轮全量健康检测。

---

## **3. Proxy Management API (代理管理)**

> Base Path: `/api/proxies`
> OpenAPI 约定：所有客户端接口提供稳定 `operationId` 以便生成 SDK。

### **List Active Proxies**
*   **Endpoint**: `GET /`
*   **OperationId**: `listProxies`
*   **Summary**: 获取当前正在监听的代理列表。
*   **Response Fields**:
    ```json
    {
      "port": 10022,
      "proxy_address": "127.0.0.1:10022",
      "proxy_scheme": "http",
      "supported_proxy_protocols": ["http", "socks5"],
      "http_proxy_url": "http://127.0.0.1:10022",
      "socks5_proxy_url": "socks5://127.0.0.1:10022"
      "socks5h_proxy_url": "socks5h://127.0.0.1:10022"
    }
    ```

### **Add Proxies**
*   **Endpoint**: `POST /`
*   **OperationId**: `addProxies`
*   **Request**:
    ```json
    {
      "node_ids": ["node_1", "node_2"],
      "start_port": 10000
    }
    ```

---

## **4. Subscription API (订阅管理)**

> Base Path: `/api/subscriptions`

### **Add Subscription**
*   **Endpoint**: `POST /`
*   **OperationId**: `createSubscription`
*   **Summary**: 添加订阅并立即抓取节点；如果抓取或解析失败，请求返回错误且不会创建空订阅记录。
*   **Request**:
    ```json
    {
      "url": "https://example.com/sub",
      "name": "My Sub"
    }
    ```

### **Refresh Subscription**
*   **Endpoint**: `POST /{sub_id}/refresh`
*   **OperationId**: `refreshSubscription`
*   **Summary**: 重新抓取并替换该订阅的节点。只有新内容成功解析后，旧节点才会被替换。

---

## **5. Runtime Guarantees (运行时保证)**

*   **Lease Availability Source**: Lease API 只基于当前活跃代理对应的健康状态分配端口；Xray 停止后不会继续发放旧端口。
*   **Process Scope**: Xray 进程回收限定在当前项目实例自身，避免影响同机其他 Xray 进程。
*   **Client Contract Stability**: OpenAPI 输出包含稳定 `operationId`、Pydantic schema 示例和标准化错误模型，适合客户端代码生成。
*   **Mixed-Port Contract**: 本地代理端口改为 Xray `socks` inbound，允许同一 `host:port` 同时服务 HTTP 与 SOCKS5 客户端；API 通过显式 URL 字段消除协议猜测。

---

## **6. SDK Generation (客户端 SDK 生成)**

*   **Contract Source**: 以服务端 `/openapi.json` 为唯一契约源。
*   **Current Output**: 仓库内已提供 `sdk/python` 目录，包含基于当前 OpenAPI 生成的 Python SDK。
*   **Generator**: `scripts/generate_python_sdk.py`
*   **Artifact Policy**: 仓库默认不提交 `sdk/python/openapi.json` 这类大体积契约副本；OpenAPI 以运行中的 `/openapi.json` 和按需导出为准。
*   **Why**:
    *   避免调用方重复手写 URL、鉴权头和请求体结构。
    *   降低服务端接口变更后客户端漂移的风险。
    *   便于后续继续扩展 TypeScript SDK 或其他语言 SDK。
*   **Regeneration Flow**:
    ```bash
    .venv\Scripts\python.exe scripts/generate_python_sdk.py
    .venv\Scripts\python.exe -m pip install -e .\sdk\python
    ```
