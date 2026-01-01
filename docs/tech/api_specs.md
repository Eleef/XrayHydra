# **Xray-Prism API Specifications**

Last Updated: 2026-01-02

## **1. Proxy Lease API (代理租约)**

> Base Path: `/api/lease`
> Auth: Optional Bearer Token (Configured via `LEASE_API_TOKEN`)

### **Acquire Lease**
*   **Endpoint**: `POST /acquire`
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
      "expires_at": "timestamp"
    }
    ```
*   **Response (503)**: 无可用健康代理。

### **Release Lease**
*   **Endpoint**: `POST /release`
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

### **List Active Proxies**
*   **Endpoint**: `GET /`
*   **Summary**: 获取当前正在监听的代理列表。

### **Add Proxies**
*   **Endpoint**: `POST /`
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
*   **Request**:
    ```json
    {
      "url": "https://example.com/sub",
      "name": "My Sub"
    }
    ```
