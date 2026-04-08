# xray-prism-sdk

本目录包含基于服务端 OpenAPI 契约生成的 Python SDK，用于从 Python 程序直接调用 Xray-Prism API。

默认不会在仓库中保留 `openapi.json` 副本，避免大文件影响 AI 上下文和代码审查噪音。
如需导出 OpenAPI 文件，可在生成时额外传入 `--write-openapi <path>`。

## 适用场景

- 爬虫、调度器、自动化任务通过 Lease API 申请和释放代理。
- 外部业务系统统一调用订阅、代理、健康检查和系统状态接口。
- 测试脚本复用服务端契约，减少手写 URL、Header 和请求体结构。

## 安装

### 在仓库内开发使用

```bash
# 在项目根目录
python -m venv .venv

# Windows
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .\sdk\python

# Linux / macOS
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e ./sdk/python
```

### 单独安装 SDK

```bash
cd sdk/python
python -m pip install -e .
```

## 快速开始

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    status = client.get_system_status()
    print(status)
```

## 鉴权

Lease API 在服务端配置 `LEASE_API_TOKEN` 后会启用 Bearer Token 校验。使用 SDK 时传入 `token` 即可：

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
) as client:
    lease = client.acquire_lease({"workspace_id": "crawler", "ttl": 60})
    print(lease["http_proxy_url"])
    print(lease["socks5_proxy_url"])
    print(lease["socks5h_proxy_url"])
```

## Mixed-Port 代理语义

当前服务端返回的每个本地代理端口都基于 Xray `socks` inbound，同一端口同时兼容 HTTP 与 SOCKS5：

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(base_url="http://127.0.0.1:8000", token="YOUR_TOKEN") as client:
    lease = client.acquire_lease({"workspace_id": "crawler", "ttl": 60})
    print(lease["supported_proxy_protocols"])
    print(lease["http_proxy_url"])
    print(lease["socks5_proxy_url"])
    print(lease["socks5h_proxy_url"])
```

建议新客户端优先使用显式 URL 字段，而不是只拿 `proxy_address` 后自行猜测协议。若目标是域名且本机 DNS 可能被污染，优先选择 `socks5h_proxy_url`。

## 常见调用示例

### 1. 获取系统状态

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    data = client.get_system_status()
    print(data["xray_status"])
    print(data["subscription_count"])
```

### 2. 创建订阅

```python
from xray_prism_sdk import XrayPrismClient

payload = {
    "name": "my-subscription",
    "url": "https://example.com/subscription"
}

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    result = client.create_subscription(payload)
    print(result)
```

### 3. 添加代理

```python
from xray_prism_sdk import XrayPrismClient

payload = {
    "node_ids": ["node-1", "node-2"],
    "start_port": 10808,
}

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    result = client.add_proxies(payload)
    print(result)
```

### 4. 申请和释放租约

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
) as client:
    acquired = client.acquire_lease({"workspace_id": "crawler", "ttl": 120})
    proxy_address = acquired["proxy_address"]
    http_proxy_url = acquired["http_proxy_url"]
    socks5_proxy_url = acquired["socks5_proxy_url"]
    socks5h_proxy_url = acquired["socks5h_proxy_url"]

    print(http_proxy_url)
    print(socks5_proxy_url)
    print(socks5h_proxy_url)

    released = client.release_lease({
        "workspace_id": "crawler",
        "proxy_address": proxy_address,
        "cooldown_seconds": 300,
    })
    print(released)
```

### 5. 更新健康检查配置

```python
from xray_prism_sdk import XrayPrismClient

payload = {
    "enabled": True,
    "check_interval_seconds": 60,
    "test_target": "http://ip-api.com/json",
    "test_timeout_seconds": 10,
}

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    config = client.update_health_config(payload)
    print(config)
```

### 6. 手动冷却与召回代理

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
) as client:
    client.set_manual_lease_cooldown({
        "workspace_id": "crawler",
        "proxy_port": 10022,
    })

    status = client.get_lease_status()
    print(status["workspaces"])

    client.recall_lease_cooldown({
        "workspace_id": "crawler",
        "proxy_port": 10022,
    })
```

### 7. 查询 IP 所属国家代码

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    geo = client.lookup_ip_region("8.8.8.8")
    print(geo["country"])
    print(geo["country_code"])  # US
```

### 8. 按国家代码列出当前 workspace 可见出口 IP

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
) as client:
    listing = client.list_exit_ips_by_country_code(
        workspace_id="crawler",
        country_code="US",
        available_only=True,
    )
    print(listing["items"])
```

### 9. 先按国家代码列出出口 IP，再按出口 IP 申请租约

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
) as client:
    listing = client.list_exit_ips_by_country_code(
        workspace_id="crawler",
        country_code="US",
        available_only=True,
    )
    selected_ip = listing["items"][0]["exit_ip"]
    lease = client.acquire_lease_by_exit_ip({
        "workspace_id": "crawler",
        "exit_ip": selected_ip,
        "ttl": 120,
    })
    print(lease["exit_ip"])
    print(lease["exit_country_code"])
```

## 请求模型

SDK 在 `xray_prism_sdk.models` 中生成了请求 `TypedDict`，适合在 IDE 和类型检查器中使用：

```python
from xray_prism_sdk import XrayPrismClient, models

payload: models.LeaseAcquireRequest = {
    "workspace_id": "crawler",
    "ttl": 60,
}

with XrayPrismClient(base_url="http://127.0.0.1:8000", token="YOUR_TOKEN") as client:
    result = client.acquire_lease(payload)
    print(result)
```

当前已生成的请求模型：

- `models.HealthConfigUpdate`
- `models.LeaseCooldownRequest`
- `models.LeaseAcquireRequest`
- `models.LeaseReleaseRequest`
- `models.ProxyAddRequest`
- `models.SubscriptionCreate`

## 返回值与错误处理

- 当前 SDK 的成功响应会直接返回解析后的 JSON `dict` / `list`。
- 当服务端返回 4xx/5xx 时，会抛出 `ApiError`。

```python
from xray_prism_sdk import ApiError, XrayPrismClient

try:
    with XrayPrismClient(base_url="http://127.0.0.1:8000", token="BAD_TOKEN") as client:
        client.get_lease_stats()
except ApiError as exc:
    print(exc.status_code)
    print(exc.payload)
```

## 自定义 httpx Client

如果你已经在项目里统一管理 `httpx.Client`，可以把现有客户端注入 SDK：

```python
import httpx

from xray_prism_sdk import XrayPrismClient

transport = httpx.HTTPTransport(retries=2)
shared_client = httpx.Client(transport=transport)

sdk = XrayPrismClient(
    base_url="http://127.0.0.1:8000",
    token="YOUR_TOKEN",
    client=shared_client,
)

try:
    print(sdk.get_system_status())
finally:
    sdk.close()
    shared_client.close()
```

## 重新生成 SDK

当服务端路由、Schema 或 OpenAPI 元数据发生变化后，重新生成一次 SDK：

```bash
# 在项目根目录
.venv\Scripts\python.exe scripts\generate_python_sdk.py

# 如需额外导出 OpenAPI JSON
.venv\Scripts\python.exe scripts\generate_python_sdk.py --write-openapi .\tmp\openapi.json
```

生成后建议执行：

```bash
.venv\Scripts\python.exe -m pytest tests/test_openapi.py tests/test_python_sdk.py -q
```

## 已生成方法

- `acquire_lease()`
- `acquire_lease_by_exit_ip()`
- `add_proxies()`
- `apply_timed_lease_cooldown_batch()`
- `clear_all_proxies()`
- `copy_nodes_to_custom_group()`
- `create_custom_group()`
- `create_subscription()`
- `dedupe_proxies_by_exit_ip()`
- `delete_custom_group()`
- `delete_custom_group_node()`
- `delete_subscription()`
- `get_health_config()`
- `get_health_status()`
- `get_lease_stats()`
- `get_lease_status()`
- `get_node()`
- `get_node_test_job()`
- `get_proxy_health_status()`
- `get_subscription()`
- `get_system_status()`
- `import_custom_group_nodes()`
- `list_custom_group_nodes()`
- `list_custom_groups()`
- `list_proxies()`
- `list_proxy_exit_ips_by_country_code()`
- `list_subscription_nodes()`
- `list_subscriptions()`
- `lookup_ip_region()`
- `preview_proxy_exit_ip_duplicates()`
- `recall_lease_cooldown()`
- `refresh_subscription()`
- `release_lease()`
- `remove_proxy()`
- `rename_custom_group()`
- `reset_all_health()`
- `reset_proxy_health()`
- `reset_workspace_lease_state()`
- `restart_xray()`
- `run_health_check()`
- `set_manual_lease_cooldown()`
- `start_health_monitoring()`
- `start_node_test_job()`
- `start_xray()`
- `stop_health_monitoring()`
- `stop_xray()`
- `test_all_proxies()`
- `test_nodes()`
- `test_single_proxy()`
- `update_health_config()`
