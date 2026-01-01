# **Xray-Prism Product Requirements**

Last Updated: 2026-01-02

## **1. Background & Value (背景与价值)**

* **User Story**: 作为一名数据采集工程师或爬虫开发者，我希望能够将单一的 VPN 订阅拆解为多个本地独立的 HTTP/Socks5 代理端口，以便于在爬虫任务中实现多 IP 并发请求，规避反爬策略。同时，我需要自动化的健康监测和租约管理，确保业务流程不因代理失效而中断。
* **Priority**: P0 (Core Functionality)

## **2. Functional Requirements (功能需求)**

### **Core Proxy Engine (核心代理引擎)**
| ID | Feature Point | Description | Acceptance Criteria |
| :---- | :---- | :---- | :---- |
| F1 | 订阅解析 | 支持 vmess/vless/ss/trojan 协议及 Clash YAML 格式 | 能正确识别并解析节点信息，自动 Base64 解码 |
| F2 | 端口映射 | 将每个节点映射为本地独立端口 (如 10000, 10001...) | Xray 配置文件生成正确，路由规则 1:1 绑定 |
| F3 | 进程管理 | 自动下载并管理 Xray 内核进程 | 支持 Windows/Linux/macOS，自动拉起和优雅停止 |

### **Health Monitoring (健康监测)**
| ID | Feature Point | Description | Acceptance Criteria |
| :---- | :---- | :---- | :---- |
| H1 | 实时探测 | 定期通过代理请求目标地址 (如 ip-api.com) | 能够识别连通性，计算延迟 |
| H2 | 递进罚时 | 失败节点进入冷却期 (5m -> 30m -> 150m) | 失败次数累计，罚时时间指数递增，期间不分配流量 |
| H3 | 网络容错 | 检测本机网络连接 | 本机断网时暂停健康检测，避免误判 |

### **Lease Management (租约管理) - v0.5.0**
| ID | Feature Point | Description | Acceptance Criteria |
| :---- | :---- | :---- | :---- |
| L1 | 租约申请 | 为 Workspace 申请可用代理 | 返回 IP:Port 和 LeaseID，支持 LRU 选择 |
| L2 | 自动过期 | TTL 机制 | 租约超时后自动释放，状态变为可用 |
| L3 | 业务隔离 | Workspace 概念 | 不同 Workspace 可复用同一代理，互不干扰 |

### **Web Interface (Web 界面)**
| ID | Feature Point | Description | Acceptance Criteria |
| :---- | :---- | :---- | :---- |
| W1 | 仪表盘 | 三栏布局 (订阅/节点/代理) | 清晰展示资源状态，实时刷新 |
| W2 | 交互操作 | 增删改查 | 支持添加订阅、测试节点、重置健康状态 |

## **3. Edge Cases (边界情况)**

* **订阅失效**: 当订阅链接无法访问时，应保留本地缓存或提示明确错误，不应崩溃。
* **端口冲突**: 当本地端口被占用时，应有检测机制或报错提示。
* **僵尸进程**: 程序异常退出时，需确保 Xray 子进程被正确清理 (已通过 signal handler 实现)。

## **4. Technical Constraints (技术限制)**

* **Single Instance**: 同一时间只能运行一个 Xray 实例（配置文件锁定）。
* **Protocol Support**: 暂不支持 Hysteria2 等最新协议。
