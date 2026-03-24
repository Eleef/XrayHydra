# **Xray-Prism API Specifications**

Last Updated: 2026-03-22

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
      "ttl": 60,                // 租约有效期(秒)
      "initial_port_ordering": "random"
    }
    ```
*   **Optional Field**: `initial_port_ordering`
    *   `random`: 默认值。仅当候选端口都没有使用历史时，随机挑选一个端口。
    *   `port_asc`: 仅当候选端口都没有使用历史时，按端口升序挑选。
*   **Selection Rule**: 一旦端口已有使用历史，仍按 LRU 分配；该字段只影响首次无历史场景下的 tie-break。
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

### **Manual Cooldown**
*   **Endpoint**: `POST /cooldown/manual`
*   **OperationId**: `setManualLeaseCooldown`
*   **Summary**: 为指定 `workspace + proxy_port` 建立手动冷却。
*   **Request**:
    ```json
    {
      "workspace_id": "string",
      "proxy_port": 10000
    }
    ```
*   **Behavior**: `manual` 冷却不自动过期，只能通过召回接口结束。
*   **Global Scope**: 若 `workspace_id = "__global__"`，表示全局冷却；它会阻止所有 workspace 获取该代理端口。

### **Recall Cooldown**
*   **Endpoint**: `POST /cooldown/recall`
*   **OperationId**: `recallLeaseCooldown`
*   **Summary**: 移除指定 `workspace + proxy_port` 的冷却记录。
*   **Behavior**: 可用于结束手动冷却，或提前结束原本会自动过期的定时冷却。

### **Batch Timed Cooldown**
*   **Endpoint**: `POST /cooldown/timed/batch`
*   **OperationId**: `applyTimedLeaseCooldownBatch`
*   **Summary**: 按 workspace 批量为多个代理端口加入定时冷却。
*   **Request**:
    ```json
    {
      "workspace_id": "string",
      "proxy_ports": [10001, 10002],
      "cooldown_seconds": 300
    }
    ```
*   **Behavior**: 活跃租约中的端口会被跳过，不会被强制释放。
*   **Global Scope**: 当前端在“所有代理”视图下，或当前没有激活具体 workspace 时确认测试失败候选清单，会传入 `workspace_id = "__global__"`，表示对全部 workspace 生效的全局定时冷却。

### **Get Status**
*   **Endpoint**: `GET /status`
*   **OperationId**: `getLeaseStatus`
*   **Summary**: 获取当前租约状态和 workspace 摘要。
*   **Compatibility**: `workspaces` 摘要数组不包含 `__global__`；但当客户端按具体 workspace 过滤时，响应中的 `cooldowns` 仍会同时返回该 workspace 冷却和全局冷却，便于前端在单个 workspace 视图中显示全局影响。
*   **Response Highlights**:
    ```json
    {
      "active_leases": [
        {
          "workspace_id": "crawler_a",
          "proxy_port": 10022,
          "expires_at": "timestamp"
        }
      ],
      "cooldowns": [
        {
          "workspace_id": "crawler_a",
          "proxy_port": 10022,
          "source": "manual",
          "until": null
        }
      ],
      "workspaces": [
        {
          "workspace_id": "crawler_a",
          "active_count": 1,
          "cooldown_count": 1,
          "last_activity_at": "timestamp"
        }
      ]
    }
    ```

> Note: Web 前端中的“所有代理”是一个纯前端伪选项，不会直接写入 `workspaces` 摘要；真正落到后端的全局冷却 scope 使用 `__global__`。

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

### **Preview Exit-IP Duplicates**
*   **Endpoint**: `GET /duplicates/exit-ip`
*   **OperationId**: `previewProxyExitIpDuplicates`
*   **Summary**: 预览当前代理池中按出口 IP 分组后的重复代理，供前端弹窗确认。
*   **Response Highlights**:
    ```json
    {
      "duplicate_group_count": 46,
      "duplicate_proxy_count": 51,
      "groups": [
        {
          "exit_ip": "1.2.3.4",
          "keep_proxy": {
            "port": 10000,
            "node_name": "TW-01",
            "test_status": "success",
            "latency_ms": 469
          },
          "remove_proxies": [
            {
              "port": 10003,
              "node_name": "TW-01-Backup",
              "test_status": "success",
              "latency_ms": 499
            }
          ]
        }
      ]
    }
    ```
*   **Selection Rule**: 服务端按 `test_status == success` 优先、其次更低 `latency_ms`、最后更小 `port` 的顺序确定 `keep_proxy`。

### **Apply Exit-IP Dedupe**
*   **Endpoint**: `POST /dedupe/exit-ip`
*   **OperationId**: `dedupeProxiesByExitIp`
*   **Summary**: 根据用户确认的端口列表禁用重复代理，只处理预览结果中的重复项。
*   **Request**:
    ```json
    {
      "disable_ports": [10003, 10089]
    }
    ```
*   **Response Highlights**:
    ```json
    {
      "disabled_count": 2,
      "disabled_ports": [10003, 10089],
      "kept_ports": [10000, 10030]
    }
    ```
*   **Behavior**:
*   该接口不会自动触发测试，也不会自动补充新代理。
*   被命中的重复代理不会从池中删除，而是标记为 `pool_status = "dedupe_disabled"`、`disabled_reason = "exit_ip_duplicate"`。
*   `dedupe_disabled` 代理仍会在节点栏中被识别为“已入池”，但不会进入 Xray 运行配置，也不会参与租约、健康检查或代理测试。
*   如果当前 Xray 正在运行，应用去重后会刷新运行配置；未运行时只同步持久化状态。

---

## **4. Node API (节点管理与测试)**

> Base Path: `/api/nodes`
> OpenAPI 约定：所有客户端接口提供稳定 `operationId` 以便生成 SDK。

### **Get Node**
*   **Endpoint**: `GET /{node_id}`
*   **OperationId**: `getNode`
*   **Summary**: 获取单个节点详情。
*   **Response Fields (新增)**:
    ```json
    {
      "id": "node_xxx",
      "group_id": "sub_xxx",
      "group_type": "subscription",
      "subscription_id": "sub_xxx",
      "name": "HK-01",
      "test_status": "pending",
      "in_proxy_pool": false,
      "proxy_port": null
    }
    ```
*   **Notes**:
    *   `group_id` / `group_type` 用于前端统一渲染“节点组”视图。
    *   订阅节点保留 `subscription_id`；自定义组节点的 `subscription_id = null`。

### **Test Nodes (Batch / Single)**
*   **Endpoint**: `POST /test`
*   **OperationId**: `testNodes`
*   **Summary**: 批量测试节点连通性。单节点测试通过传入单元素 `node_ids` 实现。
*   **Request**:
    ```json
    {
      "node_ids": ["node_1", "node_2"],
      "timeout": 5,
      "test_profile": "multi_target"
    }
    ```

### **Start Node Test Job**
*   **Endpoint**: `POST /test-jobs`
*   **OperationId**: `startNodeTestJob`
*   **Summary**: 创建异步节点测试任务，供前端轮询真实进度。
*   **Request**: 与 `POST /test` 相同。
*   **Response Highlights**:
    ```json
    {
      "job_id": "f6f6b4d8b99f4f43887b0d6e0d8f9a34",
      "status": "queued",
      "total": 53,
      "progress_percent": 0,
      "success_count": 0,
      "failed_count": 0,
      "current_target_completed": 0,
      "current_target_total": 0
    }
    ```

### **Get Node Test Job**
*   **Endpoint**: `GET /test-jobs/{job_id}`
*   **OperationId**: `getNodeTestJob`
*   **Summary**: 轮询异步节点测试任务的当前进度和最终结果。
*   **Response Highlights**:
    ```json
    {
      "job_id": "f6f6b4d8b99f4f43887b0d6e0d8f9a34",
      "status": "running",
      "total": 53,
      "completed_count": 45,
      "success_count": 45,
      "failed_count": 0,
      "progress_percent": 67,
      "active_target": "https://httpbin.org/ip",
      "target_index": 2,
      "target_total": 3,
      "current_target_completed": 4,
      "current_target_total": 8,
      "note": "目标 2/3 已检测 4/8"
    }
    ```
*   **Completion**: 当 `status = completed` 时，响应中的 `results` 字段会携带与 `POST /test` 相同的最终测试结果数组。
*   **Behavior**:
    *   `test_profile` 默认值为 `multi_target`。
    *   多目标策略下，同一节点按主/备目标依次测试。
    *   任一目标成功即 `status=success`，仅当全部目标失败时 `status=failed`。
    *   该测试链路使用独立临时运行时，不应影响主 Xray runner 的生命周期与元数据跟踪。
*   **Response**:
    ```json
    {
      "results": [
        {
          "node_id": "node_1",
          "status": "success",
          "latency_ms": 231,
          "exit_ip": "203.0.113.2",
          "successful_target": "http://ip-api.com/json"
        },
        {
          "node_id": "node_2",
          "status": "failed",
          "error": "all targets failed",
          "tested_target": "https://api.ipify.org?format=json"
        }
      ],
      "success_count": 1,
      "failed_count": 1,
      "test_profile": "multi_target"
    }
    ```

---

## **5. Subscription API (订阅管理)**

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

---

## **6. Custom Group API (自定义节点组)**

> Base Path: `/api/custom-groups`

### **List Custom Groups**
*   **Endpoint**: `GET /`
*   **OperationId**: `listCustomGroups`
*   **Summary**: 获取所有自定义节点组元数据。

### **Create Custom Group**
*   **Endpoint**: `POST /`
*   **OperationId**: `createCustomGroup`
*   **Summary**: 创建一个空的自定义节点组。

### **Rename Custom Group**
*   **Endpoint**: `PATCH /{group_id}`
*   **OperationId**: `renameCustomGroup`
*   **Summary**: 重命名自定义节点组。

### **Delete Custom Group**
*   **Endpoint**: `DELETE /{group_id}`
*   **OperationId**: `deleteCustomGroup`
*   **Summary**: 删除自定义节点组及其快照节点。

### **List Custom Group Nodes**
*   **Endpoint**: `GET /{group_id}/nodes`
*   **OperationId**: `listCustomGroupNodes`
*   **Summary**: 获取某个自定义组的快照节点列表，返回结构与订阅节点一致。

### **Import Custom Group Nodes**
*   **Endpoint**: `POST /{group_id}/nodes/import`
*   **OperationId**: `importCustomGroupNodes`
*   **Summary**: 通过粘贴多行节点链接导入到指定自定义组。
*   **Behavior**:
    *   只接受当前 Xray 可运行协议。
    *   `SSR` 等不支持协议会沿用现有明确报错逻辑；若为混合内容，则忽略不支持协议并继续导入可运行节点。
    *   同组内按连接语义去重。
*   **Response Fields**:
    *   `imported_count`: 实际新增节点数。
    *   `skipped_duplicates`: 因组内语义去重而跳过的数量。
    *   `total_parsed`: 本次解析出的总节点数。
    *   `ignored_unsupported_count`: 混合内容中被忽略的不支持协议节点数。

### **Copy Nodes To Custom Group**
*   **Endpoint**: `POST /{group_id}/nodes/copy`
*   **OperationId**: `copyNodesToCustomGroup`
*   **Summary**: 从当前节点列表复制快照到指定自定义组，支持来源为订阅节点或另一个自定义组节点。
*   **Behavior**:
    *   工具栏批量复制只作用于当前筛选结果中显式勾选的节点。
    *   行内 `复制到分组` 可用于已入池或勾选禁用节点的单节点复制。

### **Delete Custom Group Node**
*   **Endpoint**: `DELETE /{group_id}/nodes/{node_id}`
*   **OperationId**: `deleteCustomGroupNode`
*   **Summary**: 从自定义组中移除单个节点快照，不影响来源订阅或其他自定义组。

### **Refresh Subscription**
*   **Endpoint**: `POST /{sub_id}/refresh`
*   **OperationId**: `refreshSubscription`
*   **Summary**: 重新抓取并替换该订阅的节点。只有新内容成功解析后，旧节点才会被替换。

---

## **6. Runtime Guarantees (运行时保证)**

*   **Lease Availability Source**: Lease API 只基于当前活跃代理对应的健康状态分配端口；Xray 停止后不会继续发放旧端口。
*   **Process Scope**: Xray 进程回收限定在当前项目实例自身，避免影响同机其他 Xray 进程。
*   **Client Contract Stability**: OpenAPI 输出包含稳定 `operationId`、Pydantic schema 示例和标准化错误模型，适合客户端代码生成。
*   **Mixed-Port Contract**: 本地代理端口改为 Xray `socks` inbound，允许同一 `host:port` 同时服务 HTTP 与 SOCKS5 客户端；API 通过显式 URL 字段消除协议猜测。
*   **Node Test Isolation**: 节点测试使用独立临时运行时，不应触发主 runner 的 stop/restart，也不应覆盖主进程跟踪元数据。

---

## **7. SDK Generation (客户端 SDK 生成)**

*   **Contract Source**: 以服务端 `/openapi.json` 为唯一契约源。
*   **Current Output**: 仓库内已提供 `sdk/python` 目录，包含基于当前 OpenAPI 生成的 Python SDK。
*   **Current Output**: 仓库内同时提供 `sdk/python` 与 `sdk/typescript`，分别用于 Python 与 TypeScript 调用方。
*   **Generator**: `scripts/generate_python_sdk.py`、`scripts/generate_typescript_sdk.py`
*   **Artifact Policy**: 仓库默认不提交 `sdk/python/openapi.json` 这类大体积契约副本；OpenAPI 以运行中的 `/openapi.json` 和按需导出为准。
*   **Why**:
    *   避免调用方重复手写 URL、鉴权头和请求体结构。
    *   降低服务端接口变更后客户端漂移的风险。
    *   让 Python / TypeScript 两侧统一消费同一份 Lease / Proxy / Health / System 契约。
*   **Regeneration Flow**:
    ```bash
    .venv\Scripts\python.exe scripts/generate_python_sdk.py
    .venv\Scripts\python.exe scripts/generate_typescript_sdk.py
    .venv\Scripts\python.exe -m pip install -e .\sdk\python
    ```
