# **Xray-Prism Technical Architecture**

Last Updated: 2026-03-24

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
        SubService --> Decoder[Subscription Decoder]
        Decoder --> Parser[Protocol Parser Registry]
        Parser --> Capability[Capability Evaluator]
        ProxyService --> Generator[Config Generator]
        Generator --> Adapter[Xray Runtime Adapter Registry]
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
    *   Subscription Decoder: 归一化为可解析的订阅文本 / Clash 节点项
    *   Protocol Parser Registry: 解析为 `ProxyNode` 对象列表
    *   Capability Evaluator: 标记 `runtime_supported` / `runtime_support_reason`
    *   Storage: 保存至 `subscriptions.json`

2.  **Proxy Activation Flow**:
    *   Client -> API: 选择节点并激活
    *   Capability Evaluator: 拒绝当前运行链路不支持的节点
    *   Generator: 为每个节点分配本地端口 (Base Port + Index)
    *   Xray Runtime Adapter Registry: 按协议生成 outbound
    *   Generator: 组装完整 Xray JSON 配置 (Socks Inbound <-> Routing <-> Outbound)
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
    protocol: Protocol  # vmess/vless/ss/trojan/hysteria2/ssr
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

解析层当前可以识别 `vmess`、`vless`、`shadowsocks`、`trojan`、`hysteria2` 和 `ssr`。运行层当前接受 `RUNTIME_SUPPORTED_PROTOCOLS` 中的协议，也就是 `vmess/vless/shadowsocks/trojan/hysteria2`。

这意味着“能识别订阅内容”和“能被当前 Xray 运行”是两个不同阶段。`hysteria2://` 会进入正常运行链路；`ssr://` 会被识别并保留在节点列表中，但仍不会进入 Xray 运行链路。不兼容协议节点也会保留在节点列表中，避免前端误以为订阅“丢了节点”。

当前实现已经把这两个阶段拆成独立模块：
- `subscription_decoders/*`: 处理 Base64、多行 URI、Clash YAML 等订阅格式
- `protocol_parsers/*`: 按协议拆分 URI/Clash 节点解析
- `capabilities.py`: 单点给出 `runtime_supported` 与原因
- `runtime_adapters/xray/*`: 按协议生成 Xray outbound

这样以后新增协议时，不再需要同时修改 API、前端和运行服务里的多处分支判断；优先新增 parser 和 capability 规则，只有真正可运行时才再补 Xray adapter。

能力判定已经不是单纯“按协议名”布尔判断。像 `shadowsocks` 这类协议，当前会继续识别并展示 `plugin`、`UoT`、`SS2022` 等字段，其中：
- 基础 SS / SS2022 / UoT 节点进入运行链路
- 带当前未映射的 SS plugin 节点会保留在列表中，但标记为 `runtime_supported = false`

## **7. SSR Handling**

SSR（ShadowsocksR）节点会被正常解析并持久化，这样前端可以把它们显示出来，避免用户误以为订阅“只解析出了少量节点”。

但 SSR 仍不会进入代理池、节点测试或 Xray 配置生成链路。前端会将这些节点标记为不兼容协议，并以灰色不可选状态展示；后端若收到直接的“加代理/测试”请求，也会明确拒绝。

## **8. Hysteria2 Support**

`hysteria2://` / `hy2://` 节点会被解析为 `Protocol.HYSTERIA2`，并进入当前可运行协议集合。

运行时配置遵循 Xray 官方 `hysteria2` 出站与 `hysteria` 传输层模型：出站协议为 `hysteria2`，`streamSettings.network = "hysteria"`，同时携带 `hysteriaSettings.version = 2` 与认证参数 `auth`。
