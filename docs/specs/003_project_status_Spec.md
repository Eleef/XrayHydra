# Xray-Prism 项目状态文档

> 最后更新：2025-12-24
> 版本：v0.1.0 (CLI 版本完成)

## 1. 项目概述

**Xray-Prism** 是一个 Python 自动化工具，将 VPN 订阅中的每个节点映射为本地独立端口，实现并发使用不同 IP 出口。

### 核心功能
- 从 URL 或本地文件获取订阅内容
- 自动检测并解析多种订阅格式（Clash YAML / 标准 URI）
- 支持 VMess / VLess / Shadowsocks / Trojan 协议
- 生成 Xray-core 配置（每节点一端口，路由 1:1 硬绑定）
- 自动下载和管理 Xray 内核
- 并发测试所有代理端口的连通性
- 输出代理列表文件

---

## 2. 当前目录结构

```
d:\project\XrayHydra\
├── main.py                    # 主程序入口 (CLI)
├── config.json                # 生成的 Xray 配置
├── proxies.txt                # 生成的代理列表
├── subscription_sample.txt    # 订阅样本（调试用）
├── requirements.txt           # Python 依赖
├── README.md                  # 使用说明
├── CHANGELOG.md               # 变更日志
├── bin/                       # 自动下载的 Xray 内核
│   └── xray.exe
├── docs/
│   ├── PROJECT_STATUS.md      # 本文档
│   └── specs/                 # 模块规格文档
│       ├── 001_models_Spec.md
│       └── 002_fetcher_Spec.md
├── src/xray_prism/            # 核心模块
│   ├── __init__.py
│   ├── models.py              # 数据模型层
│   ├── fetcher.py             # 网络获取层
│   ├── parser.py              # 协议解析层
│   ├── generator.py           # 配置生成层
│   ├── runner.py              # 进程管理层
│   └── tester.py              # 连通性测试层
└── tests/                     # 单元测试
    ├── __init__.py
    ├── test_models.py
    └── test_fetcher.py
```

---

## 3. 模块详解

### 3.1 models.py - 数据模型层

**文件路径**: `src/xray_prism/models.py`

定义核心数据结构：

| 类名 | 描述 |
|:---|:---|
| `Protocol` | 协议枚举：VMESS, VLESS, SHADOWSOCKS, TROJAN |
| `NetworkType` | 网络类型枚举：TCP, WS, GRPC, H2, KCP |
| `ProxyNode` | 统一代理节点模型，包含所有协议的字段 |
| `TestResult` | 测试结果模型 |
| `PortMapping` | 端口映射记录（本地端口 ↔ 节点） |

**关键字段** (`ProxyNode`):
```python
name: str               # 节点名称
protocol: Protocol      # 协议类型
address: str            # 服务器地址
port: int               # 服务器端口
uuid: Optional[str]     # UUID (vmess/vless)
password: Optional[str] # 密码 (ss/trojan)
security: str           # 加密方式
network: NetworkType    # 传输方式
tls: bool               # 是否启用 TLS
sni: Optional[str]      # TLS SNI
allow_insecure: bool    # 跳过证书验证
# ... 更多字段见源码
```

---

### 3.2 fetcher.py - 网络获取层

**文件路径**: `src/xray_prism/fetcher.py`

| 函数 | 描述 |
|:---|:---|
| `fetch_from_url(url)` | 从 URL 获取订阅内容 |
| `read_from_file(path)` | 从本地文件读取 |
| `decode_base64(content)` | Base64 解码（含 padding 修复） |
| `is_base64_encoded(content)` | 检测是否 Base64 编码 |
| `fetch_subscription(url, file)` | 统一入口 |

**特性**:
- 自动检测并解码 Base64
- 支持 URL-safe Base64
- 模拟 Clash 客户端请求头

---

### 3.3 parser.py - 协议解析层

**文件路径**: `src/xray_prism/parser.py`

| 函数 | 描述 |
|:---|:---|
| `parse_vmess(uri)` | 解析 vmess:// 链接 |
| `parse_vless(uri)` | 解析 vless:// 链接 |
| `parse_shadowsocks(uri)` | 解析 ss:// 链接 |
| `parse_trojan(uri)` | 解析 trojan:// 链接 |
| `parse_subscription(content)` | 统一解析入口 |
| `_parse_clash_yaml(content)` | 解析 Clash YAML 格式 |

**关键特性**:
- **自动格式检测**: 区分 Clash YAML 和标准 URI 列表
- **Clash YAML 解析**: 使用 PyYAML，回退到正则
- **节点过滤**: 自动过滤元数据节点（流量信息、到期时间等）

**过滤关键词** (`FILTER_KEYWORDS`):
```python
['剩余流量', '套餐到期', '过期时间', 'TG群', '官网',
 '到期', '流量', '订阅', '更新', '官方', 'Telegram',
 '客服', '网址', 'http', 'https', 'www.']
```

---

### 3.4 generator.py - 配置生成层

**文件路径**: `src/xray_prism/generator.py`

**类**: `ConfigGenerator`

| 方法 | 描述 |
|:---|:---|
| `generate(nodes)` | 生成完整 Xray 配置字典 |
| `generate_and_save(nodes, path)` | 生成并保存到文件 |

**配置结构**:
```json
{
  "log": {"loglevel": "warning"},
  "inbounds": [...],      // 每节点一个 HTTP 入站
  "outbounds": [...],     // 每节点一个协议出站 + freedom + blackhole
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [...]        // 1:1 inboundTag -> outboundTag 绑定
  }
}
```

**路由规则** (关键):
```json
{
  "type": "field",
  "inboundTag": ["in_10000"],
  "outboundTag": "out_10000"
}
```

---

### 3.5 runner.py - 进程管理层

**文件路径**: `src/xray_prism/runner.py`

**类**: `XrayRunner`

| 方法 | 描述 |
|:---|:---|
| `find_xray()` | 自动查找 Xray 可执行文件 |
| `download_xray()` | 下载 Xray 到项目目录 |
| `start(config_path)` | 启动 Xray 进程 |
| `stop()` | 停止 Xray 进程 |
| `is_running()` | 检查运行状态 |

**下载配置**:
- 版本: `v24.12.18`
- 存放目录: `bin/`
- 自动检测平台 (Windows/Linux/macOS)

---

### 3.6 tester.py - 连通性测试层

**文件路径**: `src/xray_prism/tester.py`

**类**: `ProxyTester`

| 方法 | 描述 |
|:---|:---|
| `test_port(port, name)` | 测试单个端口 |
| `test_all(mappings)` | 并发测试所有端口 |
| `format_results(results)` | 格式化输出表格 |

**测试逻辑**:
- 使用 `ThreadPoolExecutor` 并发
- 请求 `http://ip-api.com/json` 获取出口 IP
- 返回延迟、地区等信息

---

### 3.7 main.py - 主程序入口

**命令行参数**:

| 参数 | 说明 | 默认值 |
|:---|:---|:---|
| `--url`, `-u` | 订阅链接 URL | - |
| `--file`, `-f` | 本地订阅文件 | - |
| `--port`, `-p` | 起始端口号 | 10000 |
| `--xray-path` | 手动指定 Xray 路径 | 自动查找 |
| `--download-xray` | 自动下载 Xray | - |
| `--test`, `-t` | 运行连通性测试 | - |
| `--timeout` | 测试超时时间 | 5 |
| `--workers` | 并发线程数 | 20 |
| `--inbound-type` | 入站协议 (http/socks) | http |
| `--keep-running` | 测试后保持运行 | - |
| `--verbose`, `-v` | 详细日志 | - |

**执行流程**:
1. 获取订阅内容 (`fetcher`)
2. 解析代理节点 (`parser`)
3. 生成 Xray 配置 (`generator`)
4. 保存代理列表 (`proxies.txt`)
5. 启动 Xray 内核 (`runner`)
6. 运行连通性测试 (`tester`)

---

## 4. 依赖

**requirements.txt**:
```
requests>=2.28.0
pyyaml>=6.0
```

---

## 5. 使用示例

```bash
# 安装依赖
pip install -r requirements.txt

# 从订阅 URL 获取节点并测试
python main.py --url "YOUR_SUBSCRIPTION_URL" --test

# 从本地文件读取
python main.py --file subscription.txt --test

# 保持运行作为代理服务
python main.py --file subscription.txt --keep-running

# 使用特定端口的代理
curl -x http://127.0.0.1:10000 https://httpbin.org/ip
```

---

## 6. 已知问题和限制

1. **节点测试失败**可能原因:
   - 节点本身不可用
   - 网络阻断
   - 证书问题（确保 `allow_insecure` 已正确解析）

2. **暂不支持的协议**: Hysteria2, TUIC 等较新协议

3. **单实例限制**: 同一时间只能运行一个 Xray 进程

---

## 7. 后续开发计划

### Phase 2: Web 前端 (待开发)

- 前后端分离架构
- 订阅管理（添加/删除/刷新）
- 节点列表可视化
- 代理端口管理
- 实时测试和状态监控

详见下一节的实施计划。
