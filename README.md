# Xray-Prism

将 VPN 订阅中的每个节点映射为本地独立端口，实现并发使用不同 IP。

## 功能特性

- ✅ 支持 VMess / VLess / Shadowsocks / Trojan 协议解析
- ✅ 自动 Base64 解码（含 URL-safe 和 padding 修复）
- ✅ 每个节点一个独立端口，路由 1 对 1 硬绑定
- ✅ 自动下载 Xray 内核（支持 Windows/Linux/macOS）
- ✅ 并发连通性测试，获取出口 IP 和延迟
- ✅ 优雅的进程管理，支持信号中断

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

```bash
# 从订阅 URL 获取节点并测试
python main.py --url "YOUR_SUBSCRIPTION_URL" --test

# 从本地文件读取
python main.py --file subscription.txt --port 10000 --test

# 保持运行（作为代理服务器）
python main.py --url "..." --keep-running
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|:---|:---|:---|
| `--url`, `-u` | 订阅链接 URL | - |
| `--file`, `-f` | 本地订阅文件路径 | - |
| `--port`, `-p` | 起始端口号 | 10000 |
| `--xray-path` | 手动指定 Xray 路径 | 自动查找 |
| `--download-xray` | 自动下载 Xray 内核 | - |
| `--test`, `-t` | 运行连通性测试 | - |
| `--timeout` | 测试超时时间（秒） | 5 |
| `--workers` | 最大并发测试线程数 | 20 |
| `--inbound-type` | 入站协议 (http/socks) | http |
| `--keep-running` | 测试后保持运行 | - |
| `--verbose`, `-v` | 显示详细日志 | - |

## 使用示例

启动后，每个节点会映射到一个本地端口：

```bash
# 使用第一个节点（端口 10000）
curl -x http://127.0.0.1:10000 https://httpbin.org/ip

# 使用第二个节点（端口 10001）
curl -x http://127.0.0.1:10001 https://httpbin.org/ip

# Python 中使用
import requests
proxies = {"http": "http://127.0.0.1:10000", "https": "http://127.0.0.1:10000"}
response = requests.get("https://httpbin.org/ip", proxies=proxies)
```

## 项目结构

```
XrayHydra/
├── main.py              # 主程序入口
├── config.json          # 生成的 Xray 配置
├── bin/                 # 自动下载的 Xray 内核
├── src/xray_prism/
│   ├── models.py        # 数据模型
│   ├── fetcher.py       # 订阅获取
│   ├── parser.py        # 协议解析
│   ├── generator.py     # 配置生成
│   ├── runner.py        # 进程管理
│   └── tester.py        # 连通性测试
└── tests/               # 单元测试
```

## 依赖

- Python 3.10+
- requests
- Xray-core（自动下载或手动指定）

