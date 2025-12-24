# Changelog

本文件记录 Xray-Prism 项目的所有重要变更。

## [0.1.0] - 2025-12-23

### Added
- **models.py**: 数据模型层，定义 Protocol/NetworkType 枚举、ProxyNode/TestResult/PortMapping 数据类
- **fetcher.py**: 网络层，支持 URL 获取和文件读取，自动 Base64 解码（含 URL-safe 和 padding 修复）
- **parser.py**: 核心解析层，支持 VMess/VLess/Shadowsocks/Trojan 协议解析，具备容错机制
- **generator.py**: 配置生成层，生成 Xray config.json，每节点一端口，路由 1 对 1 硬绑定
- **runner.py**: 进程管理层，自动查找/下载 Xray 内核，优雅管理子进程生命周期
- **tester.py**: 验证测试层，ThreadPoolExecutor 并发测试，获取出口 IP 和延迟
- **main.py**: 主程序入口，argparse CLI，完整执行流程，信号处理和优雅退出

