# **Xray-Prism Technical Architecture**

Last Updated: 2026-01-02

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
    *   Generator: 生成 Xray JSON 配置 (Inbound <-> Routing <-> Outbound)
    *   Runner: 重启 Xray 进程加载新配置

3.  **Health Monitoring Flow**:
    *   Monitor (Background Thread): 周期性轮询
    *   Tester: 通过代理发送 HTTP 请求
    *   Monitor: 更新 `HealthState` (Failure Count / Penalty)

4.  **Lease Acquisition Flow**:
    *   Client -> API: `POST /lease/acquire`
    *   LeaseManager: 筛选 `Healthy` 节点
    *   LeaseManager: LRU 算法选择最久未使用节点
    *   LeaseManager: 创建 Lease 记录 (In-Memory)

## **4. Data Structures (关键数据)**

### **ProxyNode**
```python
class ProxyNode:
    name: str           # 节点名称
    protocol: Protocol  # vmess/vless/ss/trojan
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
