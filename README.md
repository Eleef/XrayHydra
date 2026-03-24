# Xray-Prism

[English](README.en.md)

把订阅里的“每个节点”映射为本地独立端口，支持批量测试、代理池管理与租约分配，面向多任务并发与自动化采集场景。

## 功能概览

- 节点组：左侧统一展示 `订阅组` 与 `自定义组`（自定义组为连接快照，支持粘贴批量导入、重命名、删除与组内单节点移除）。
- 先测后加：单节点测试 + 批量测试；批量测试走后端任务并返回真实进度，测试成功节点可一键加入代理池。
- 复制到分组：工具栏 `加入到分组` 作用于当前可见且可操作的勾选节点；已入池或勾选禁用节点可用行内 `复制到分组` 单独复制。
- Mixed-Port 本地代理：每个本地端口同时支持 HTTP 与 SOCKS5（以 API 返回的 `http_proxy_url` / `socks5_proxy_url` 为准）。
- 出口 IP 去重（禁用不删除）：手动预览重复项并确认后，将重复代理标记为去重禁用，避免节点侧再次被重复加入。
- 租约 API：按 workspace 隔离、TTL 过期、可选冷却与手动召回；可配置 `LEASE_API_TOKEN` 启用 Bearer 鉴权。
- Xray 内核：支持自动下载 Xray-core 到 `bin/`，也可手动指定已安装的 `xray` 可执行文件。

## 协议支持

- 订阅输入兼容（主流）：多行 URI、Base64 文本订阅、Clash YAML / provider、SIP008 / SIP002 主流 Shadowsocks 分享形态，以及 v2rayN/v2rayNG 常见订阅导入形态（覆盖 `vmess` / `vless` / `shadowsocks` / `trojan` / `hysteria2` 主流子集）。
- 运行后端边界：仅使用 Xray 作为运行内核（Xray-only）；“可识别”与“可运行”分层处理。
- 可运行协议：`vmess` / `vless` / `shadowsocks` / `trojan` / `hysteria2`。
- `shadowsocks`：支持基础 `ss://`、SIP002 / SIP008 主流变体以及 `UoT` / `UoTVersion`；带当前未映射 `plugin` 的 SS 节点会保留显示，但灰色不可选。
- `ssr://`：会被识别并显示在节点列表中，但不会进入运行链路（Xray 不支持 SSR 出站）。
- 识别到的节点不等于可运行节点；前端会依据 API 返回的 `runtime_supported` / `runtime_support_reason` 做灰显与拦截。

## 快速开始

### Windows

直接运行一键脚本：

```powershell
start_windows.bat
```

### Linux

```bash
chmod +x start_linux.sh
./start_linux.sh
```

打开：`http://127.0.0.1:8000/`

API Docs：`http://127.0.0.1:8000/docs`

## 配置

可选使用 `.env`：

```env
HOST=127.0.0.1
PORT=8000
LEASE_API_TOKEN=your_secret_token
```

`LEASE_API_TOKEN` 为空时，租约 API 默认不启用认证。

## 开发与测试

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

重新生成 SDK：

```powershell
.venv\Scripts\python.exe scripts\generate_python_sdk.py
.venv\Scripts\python.exe scripts\generate_typescript_sdk.py
```

## 隐私与公开仓库

- 订阅链接与运行态数据会落在 `data/` 下，默认被 `.gitignore` 忽略，不应提交到仓库。
- `.env` 默认被忽略，不应提交到仓库。
- 不要把任何真实订阅 URL、节点地址或凭据写进示例文件；样例请使用占位符域名与占位符密码。
