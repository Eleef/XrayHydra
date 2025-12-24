# Spec 001: Models - 数据模型层

## 1. 概述 (Overview)

该模块定义 Xray-Prism 的核心数据结构，包括代理协议枚举、网络传输类型枚举、统一代理节点模型和测试结果模型。

目标是屏蔽不同协议（vmess/vless/ss/trojan）的差异，提供标准化的数据对象供其他模块使用。

## 2. 接口设计 (API Design)

### 2.1 Protocol 枚举

| 枚举值 | 描述 |
| :--- | :--- |
| `VMESS` | VMess 协议 |
| `VLESS` | VLess 协议 |
| `SHADOWSOCKS` | Shadowsocks 协议 |
| `TROJAN` | Trojan 协议 |

### 2.2 NetworkType 枚举

| 枚举值 | 描述 |
| :--- | :--- |
| `TCP` | TCP 直连 |
| `WS` | WebSocket 传输 |
| `GRPC` | gRPC 传输 |
| `H2` | HTTP/2 传输 |
| `KCP` | mKCP 传输 |

### 2.3 ProxyNode 数据类

| 参数名 | 类型 | 必选 | 描述 |
| :--- | :--- | :--- | :--- |
| `name` | `str` | 是 | 节点名称 |
| `protocol` | `Protocol` | 是 | 代理协议类型 |
| `address` | `str` | 是 | 服务器地址 |
| `port` | `int` | 是 | 服务器端口 |
| `uuid` | `Optional[str]` | 否 | UUID (vmess/vless) |
| `password` | `Optional[str]` | 否 | 密码 (ss/trojan) |
| `security` | `str` | 否 | 加密方式，默认 `"auto"` |
| `network` | `NetworkType` | 否 | 传输方式，默认 `TCP` |
| `tls` | `bool` | 否 | 是否启用 TLS，默认 `False` |
| `sni` | `Optional[str]` | 否 | TLS SNI 主机名 |
| `host` | `Optional[str]` | 否 | WS/H2 Host 头 |
| `path` | `Optional[str]` | 否 | WS/H2/gRPC 路径 |
| `alter_id` | `int` | 否 | VMess alterId，默认 `0` |
| `flow` | `Optional[str]` | 否 | VLess flow 控制 |
| `service_name` | `Optional[str]` | 否 | gRPC serviceName |
| `fingerprint` | `Optional[str]` | 否 | TLS 指纹 |
| `public_key` | `Optional[str]` | 否 | Reality 公钥 |
| `short_id` | `Optional[str]` | 否 | Reality shortId |

### 2.4 TestResult 数据类

| 参数名 | 类型 | 必选 | 描述 |
| :--- | :--- | :--- | :--- |
| `local_port` | `int` | 是 | 本地监听端口 |
| `node_name` | `str` | 是 | 节点名称 |
| `success` | `bool` | 是 | 测试是否成功 |
| `exit_ip` | `Optional[str]` | 否 | 出口 IP 地址 |
| `latency_ms` | `Optional[float]` | 否 | 延迟（毫秒） |
| `error` | `Optional[str]` | 否 | 错误信息 |

## 3. 核心逻辑 (Core Logic)

1. 使用 `@dataclass` 装饰器定义数据类，自动生成 `__init__`、`__repr__` 等方法。
2. 使用 `Enum` 定义协议和网络类型枚举，确保类型安全。
3. `ProxyNode` 提供 `to_dict()` 方法，便于 JSON 序列化。
4. 所有可选字段使用 `Optional[T]` 类型注解，默认值为 `None`。

## 4. 示例 (Usage Example)

```python
from models import ProxyNode, Protocol, NetworkType

# 创建 VMess 节点
node = ProxyNode(
    name="香港-01",
    protocol=Protocol.VMESS,
    address="hk.example.com",
    port=443,
    uuid="a3482e88-686a-4a58-8126-99c9df64b7bf",
    network=NetworkType.WS,
    tls=True,
    path="/ws"
)

print(node.to_dict())
```
