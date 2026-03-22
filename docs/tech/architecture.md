# **Xray-Prism Technical Architecture**

Last Updated: 2026-03-22

## **1. Overview (概述)**

Xray-Prism 采用分层架构设计，核心是利用 Python 动态生成 Xray 配置文件，并通过子进程管理 Xray 内核。Web 层基于 FastAPI 构建，提供 RESTful API 和静态资源服务。

## **2. Architecture Topology (架构拓扑)**

```mermaid
graph TD
    User[User / Client] --> WebUI[Web Frontend]
    User --> API[FastAPI Backend]
    
    subgraph "Core Services"
        API --> SubService[Subscription Service]
        API --> ProxyService[Proxy Service]
        API --> HealthService[Health Service]
        API --> LeaseService[Lease Manager]
    end
    
    subgraph "Engine Layer"
        SubService --> Fetcher[Fetcher]
        SubService --> Parser[Parser]
        ProxyService --> Generator[Config Generator]
        ProxyService --> Runner[Process Runner]
        HealthService --> Monitor[Health Monitor]
        Monitor --> Tester[Connectivity Tester]
    end
    
    subgraph "External"
        Runner --> XrayCore[Xray Kernel Process]
        Fetcher --> Web[Subscription URL]
        Tester --> Target[Test Target (ip-api.com)]
    end
```

## **3. Data Flow (数据流向)**

1.  **Subscription Flow**:
    *   Client -> API: 添加订阅 URL
    *   Fetcher: 下载内容
    *   Parser: 解析为 `ProxyNode` 对象列表
    *   Storage: 保存至 `subscriptions.json`

2.  **Proxy Activation Flow**:
    *   Client -> API: 选择节点并激活
    *   Generator: 为每个节点分配本地端口 (Base Port + Index)
    *   Generator: 生成 Xray JSON 配置 (Socks Inbound <-> Routing <-> Outbound)
    *   Runner: 重启 Xray 进程加载新配置
    *   HealthService: 仅同步当前正在运行的代理端口，移除已删除或未启动的端口健康状态

3.  **Health Monitoring Flow**:
    *   Monitor (Background Thread): 周期性轮询
    *   Tester: 通过代理发送 HTTP 请求
    *   Monitor: 更新 `HealthState` (Failure Count / Penalty)

4.  **Lease Acquisition Flow**:
    *   Client -> API: `POST /lease/acquire`
    *   LeaseManager: 筛选当前 `Healthy/Degraded` 且仍由活跃 Xray 进程承载的端口
    *   LeaseManager: LRU 算法选择最久未使用节点
    *   LeaseManager: 创建 Lease 记录 (In-Memory)
    *   API: 返回同一端口的 `http_proxy_url` / `socks5_proxy_url`，避免调用方误判协议

## **4. Runtime Safety Rules (运行时安全规则)**

1. **Project-scoped Process Control**:
   * Runner 只停止当前项目自己启动并记录过的 Xray 进程。
   * Windows / Linux 都避免使用全局 `taskkill` / `pkill` 策略，以免误伤同机其他实例。

2. **Atomic Subscription Persistence**:
   * 创建订阅时先抓取和解析，再落盘订阅与节点数据。
   * 刷新订阅时仅在新节点准备完成后才替换旧节点，避免数据被半途清空。

3. **Health State Consistency**:
   * 健康状态与实际运行中的代理端口保持一致。
   * Xray 停止后会清空可分配健康端口，防止 LeaseManager 继续发放失效地址。

4. **Single-port Mixed Proxy Access**:
   * 当前每个本地代理端口由 Xray `socks` inbound 提供。
   * 同一 `127.0.0.1:<port>` 同时兼容 HTTP 和 SOCKS5 客户端。
   * API 会显式返回 `http_proxy_url` 与 `socks5_proxy_url`，而不是要求客户端自己猜测协议。

## **5. Data Structures (关键数据)**

### **ProxyNode**
```python
class ProxyNode:
    name: str           # 节点名称
    protocol: Protocol  # vmess/vless/ss/trojan/ssr(仅用于识别)
    address: str        # 目标服务器 IP
    port: int           # 目标服务器端口
    uuid: str           # 身份凭证
    # ... 其他协议特定字段
```

### **ProxyHealthState**
```python
class ProxyHealthState:
    proxy_port: int     # 本地监听端口
    status: HealthStatus # HEALTHY, DEGRADED, DISABLED
    failure_count: int  # 连续失败次数
    penalty_level: int  # 当前罚时等级
    penalty_until: datetime # 罚时结束时间
```

## **6. Protocol Recognition vs Runtime Support**

解析层当前可以识别 `vmess`、`vless`、`shadowsocks`、`trojan` 和 `ssr`。但运行层仍只接受 `RUNTIME_SUPPORTED_PROTOCOLS` 中的协议，也就是 `vmess/vless/shadowsocks/trojan`。

这意味着“能识别订阅内容”和“能被当前 Xray 运行”是两个不同阶段。`ssr://` 会被识别出来，用于给用户返回准确错误，而不会再被误判成“空订阅”。

## **7. SSR Handling**

当订阅只包含 SSR 节点时，创建或刷新订阅会直接返回明确错误：`订阅仅包含当前 Xray 不支持的协议: ssr`。

当订阅同时包含可运行协议和 SSR 时，系统只导入可运行节点，忽略 SSR 节点，并记录一条日志说明哪些协议被跳过。这样代理池、节点测试和 Xray 配置始终只处理当前真正可运行的节点。
