# Xray-Prism

[中文](README.md)

Map each subscription node to its own local port. Includes batch testing, proxy-pool management, and a lease API for multi-workspace automation.

## Features

- Node groups: unified `Subscription Groups` and `Custom Groups` in the sidebar. Custom groups are snapshot-based and support paste import, rename, delete, and removing individual nodes.
- Test before adding: single-node and batch tests; batch tests are executed as backend jobs with real progress. Successful nodes can be added to the proxy pool in one click.
- Copy to group: toolbar `Copy to Group` applies to visible and selectable checked nodes; pooled/disabled nodes can still be copied via the per-row `Copy` action.
- Mixed-port local proxy: each local port supports both HTTP and SOCKS5 (prefer `http_proxy_url` / `socks5_proxy_url` returned by the API).
- Exit-IP dedupe (disable, not delete): preview duplicates by exit IP and then disable duplicates after confirmation to prevent re-adding.
- Lease API: workspace isolation, TTL expiration, optional cooldown, manual recall; set `LEASE_API_TOKEN` to enable Bearer auth.
- Xray core: can auto-download Xray-core into `bin/`, or use an existing installed `xray` executable.

## Protocol Support

- Runtime-supported: `vmess` / `vless` / `shadowsocks` / `trojan` / `hysteria2`.
- `shadowsocks`: supports basic `ss://`, SIP002 variants, and `UoT` / `UoTVersion`; SS nodes that require an unmapped `plugin` are still listed, but stay greyed out and non-runnable.
- `ssr://`: recognized and kept visible in the node list, but never enters the runtime path (Xray does not support SSR outbounds).
- Recognized nodes are not the same as runtime-supported nodes; the frontend relies on `runtime_supported` / `runtime_support_reason` from the API to grey out unsupported entries.

## Quick Start

### Windows

```powershell
start_windows.bat
```

### Linux

```bash
chmod +x start_linux.sh
./start_linux.sh
```

Open: `http://127.0.0.1:8000/`

API Docs: `http://127.0.0.1:8000/docs`

## Configuration

Optional `.env`:

```env
HOST=127.0.0.1
PORT=8000
LEASE_API_TOKEN=your_secret_token
```

If `LEASE_API_TOKEN` is empty, lease auth is disabled by default.

## Development

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

Regenerate SDKs:

```powershell
.venv\Scripts\python.exe scripts\generate_python_sdk.py
.venv\Scripts\python.exe scripts\generate_typescript_sdk.py
```

## Privacy & Public Repos

- Subscription URLs and runtime state live under `data/` and are ignored by default via `.gitignore`.
- `.env` is ignored by default and should not be committed.
- Do not put real subscription URLs, node addresses, or credentials into sample files. Use placeholder domains and passwords.
