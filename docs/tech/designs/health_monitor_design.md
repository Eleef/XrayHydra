# **Health Monitoring Technical Design**

> **Moved from**: `docs/specs/005_health_monitoring_implementation.md`
> **Last Updated**: 2026-01-02

## **1. Core Mechanism (核心机制)**

### **1.1 Progressive Penalty (递进式罚时)**
采用指数退避算法处理不健康节点，避免频繁探测死节点。
*   Level 1: **5 minutes** (Failure count >= 1)
*   Level 2: **30 minutes**
*   Level 3: **150 minutes** (Max)
*   **Reset**: 只要有一次探测成功，立即重置罚时等级。

### **1.2 Network Resilience (网络容错)**
在执行代理检测前，先检查本机互联网连接（通过直连访问 `network_check_targets`）。
*   **Logic**: 如果本机断网，**暂停所有健康更新**，保持代理状态不变，避免误报导致全量 Disabled。

## **2. Data Structures (数据结构)**

### **HealthStatus Enum**
*   `HEALTHY (Green)`: 节点可用且响应迅速。
*   `DEGRADED (Yellow)`: 刚从失败中恢复，或响应较慢（预留状态）。
*   `DISABLED (Gray)`: 处于罚时冷却期，**不分配给 Lease API**。

### **ProxyHealthState**
```python
class ProxyHealthState:
    proxy_port: int
    status: HealthStatus
    failure_count: int
    penalty_level: int
    penalty_until: Optional[datetime]
    last_check: datetime
    last_success: datetime
    last_latency_ms: float
```
## **3. Integration (集成)**

*   **Background Thread**: `HealthMonitor` 在后台独立线程运行，不阻塞主 API。
*   **Startup/Shutdown**: 随 `ProxyService` (Xray) 启停自动管理生命周期。
*   **Persistence**: 状态定期保存至 `data/health_state.json`。
