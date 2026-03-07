"""
Generate the Python SDK package from the current FastAPI OpenAPI schema.
"""
from __future__ import annotations

import argparse
import json
import keyword
import re
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SDK_ROOT = ROOT / "sdk" / "python"
PACKAGE_ROOT = SDK_ROOT / "src" / "xray_prism_sdk"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app


TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "object": "dict[str, Any]",
    "array": "list[Any]",
}


def camel_to_snake(value: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
    return sanitize_name(value)


def sanitize_name(name: str) -> str:
    name = name.replace("-", "_")
    if keyword.iskeyword(name):
        name += "_"
    return name


def schema_ref_name(schema: dict[str, Any] | None) -> str | None:
    if not schema:
        return None
    ref = schema.get("$ref")
    if not ref:
        return None
    return ref.rsplit("/", 1)[-1]


def python_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema_ref_name(schema) or "Any"

    if "anyOf" in schema:
        non_null = [item for item in schema["anyOf"] if item.get("type") != "null"]
        if len(non_null) == 1 and len(non_null) != len(schema["anyOf"]):
            return f"{python_type(non_null[0])} | None"
        return "Any"

    schema_type = schema.get("type")
    if schema_type == "array":
        return f"list[{python_type(schema.get('items', {}))}]"
    if schema_type == "object":
        return "dict[str, Any]"
    return TYPE_MAP.get(schema_type, "Any")


def typed_dict_body(spec: dict[str, Any]) -> str:
    components = spec.get("components", {}).get("schemas", {})
    request_names = sorted(
        name for name in components
        if name.endswith("Request") or name.endswith("Update")
    )
    lines: list[str] = [
        '"""Typed request payloads generated from the OpenAPI schema."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "from typing_extensions import NotRequired, TypedDict",
        "",
    ]

    for name in request_names:
        schema = components[name]
        if schema.get("type") != "object":
            continue

        required = set(schema.get("required", []))
        lines.append(f"class {name}(TypedDict):")
        description = schema.get("description")
        if description:
            lines.append(f'    """{description}"""')

        properties = schema.get("properties", {})
        if not properties:
            lines.append("    pass")
            lines.append("")
            continue

        for prop_name, prop_schema in properties.items():
            py_name = sanitize_name(prop_name)
            py_type = python_type(prop_schema)
            if prop_name in required:
                lines.append(f"    {py_name}: {py_type}")
            else:
                lines.append(f"    {py_name}: NotRequired[{py_type}]")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def client_body(spec: dict[str, Any]) -> str:
    lines: list[str] = [
        '"""Python SDK client generated from the OpenAPI schema."""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Any",
        "",
        "import httpx",
        "",
        "from . import models",
        "",
        "",
        "@dataclass",
        "class ApiError(Exception):",
        '    """Raised when the API returns a non-2xx response."""',
        "",
        "    status_code: int",
        "    payload: Any",
        "",
        "    def __str__(self) -> str:",
        "        if isinstance(self.payload, dict):",
        "            message = self.payload.get('detail') or self.payload.get('message') or self.payload",
        "        else:",
        "            message = self.payload",
        "        return f'API error {self.status_code}: {message}'",
        "",
        "",
        "class XrayPrismClient:",
        '    """Synchronous Python SDK for the Xray-Prism REST API."""',
        "",
        "    def __init__(",
        "        self,",
        "        base_url: str = 'http://127.0.0.1:8000',",
        "        token: str | None = None,",
        "        timeout: float = 10.0,",
        "        client: httpx.Client | None = None,",
        "    ) -> None:",
        "        self.base_url = base_url.rstrip('/')",
        "        self.token = token",
        "        self.timeout = timeout",
        "        self._owns_client = client is None",
        "        self._client = client or httpx.Client(base_url=self.base_url, timeout=self.timeout)",
        "",
        "    def close(self) -> None:",
        "        if self._owns_client:",
        "            self._client.close()",
        "",
        "    def __enter__(self) -> 'XrayPrismClient':",
        "        return self",
        "",
        "    def __exit__(self, exc_type, exc_val, exc_tb) -> None:",
        "        self.close()",
        "",
        "    def _request(",
        "        self,",
        "        method: str,",
        "        path: str,",
        "        *,",
        "        params: dict[str, Any] | None = None,",
        "        json_body: dict[str, Any] | None = None,",
        "        requires_auth: bool = False,",
        "    ) -> Any:",
        "        headers: dict[str, str] = {'Accept': 'application/json'}",
        "        if json_body is not None:",
        "            headers['Content-Type'] = 'application/json'",
        "        if requires_auth and self.token:",
        "            headers['Authorization'] = f'Bearer {self.token}'",
        "        url = path if not self.base_url else f'{self.base_url}{path}'",
        "        response = self._client.request(method, url, params=params, json=json_body, headers=headers, timeout=self.timeout)",
        "        if response.status_code >= 400:",
        "            try:",
        "                payload = response.json()",
        "            except Exception:",
        "                payload = response.text",
        "            raise ApiError(response.status_code, payload)",
        "        if response.headers.get('content-type', '').startswith('application/json'):",
        "            return response.json()",
        "        return response.text",
        "",
    ]

    for path, path_item in spec["paths"].items():
        if not path.startswith("/api/"):
            continue
        for http_method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue

            operation_id = operation["operationId"]
            method_name = camel_to_snake(operation_id)
            summary = operation.get("summary") or operation_id
            description = operation.get("description") or ""
            requires_auth = bool(operation.get("security"))

            parameters = operation.get("parameters", [])
            path_params = [p for p in parameters if p.get("in") == "path"]
            query_params = [p for p in parameters if p.get("in") == "query"]
            request_body = operation.get("requestBody")
            request_schema_name = None
            if request_body:
                content = request_body.get("content", {}).get("application/json", {})
                request_schema_name = schema_ref_name(content.get("schema"))

            signature_parts = ["self"]
            format_args: list[str] = []
            query_entries: list[str] = []

            for param in path_params:
                param_name = sanitize_name(param["name"])
                param_type = python_type(param.get("schema", {}))
                signature_parts.append(f"{param_name}: {param_type}")
                format_args.append(f"{param['name']}={param_name}")

            for param in query_params:
                param_name = sanitize_name(param["name"])
                schema = param.get("schema", {})
                param_type = python_type(schema)
                if param.get("required"):
                    signature_parts.append(f"{param_name}: {param_type}")
                else:
                    default = schema.get("default")
                    if default is None:
                        signature_parts.append(f"{param_name}: {param_type} = None")
                    elif isinstance(default, str):
                        signature_parts.append(f"{param_name}: {param_type} = {default!r}")
                    else:
                        signature_parts.append(f"{param_name}: {param_type} = {default}")
                query_entries.append(f"        if {param_name} is not None:")
                query_entries.append(f"            params[{param['name']!r}] = {param_name}")

            if request_schema_name:
                signature_parts.append(f"payload: models.{request_schema_name}")

            signature = ", ".join(signature_parts)
            lines.append(f"    def {method_name}({signature}) -> Any:")
            lines.append(f'        """{summary}."""')
            if description:
                for raw_line in description.strip().splitlines():
                    cleaned = raw_line.strip()
                    if cleaned:
                        lines.append(f"        # {cleaned}")

            if query_params:
                lines.append("        params: dict[str, Any] = {}")
                lines.extend(query_entries)
            else:
                lines.append("        params = None")

            if request_schema_name:
                lines.append("        json_body = dict(payload)")
            else:
                lines.append("        json_body = None")

            if format_args:
                path_literal = f"f'{path}'"
            else:
                path_literal = repr(path)
            lines.append(
                f"        return self._request('{http_method.upper()}', {path_literal}, params=params, json_body=json_body, requires_auth={requires_auth})"
            )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def init_body() -> str:
    return (
        '"""Python SDK for Xray-Prism generated from the local OpenAPI schema."""\n\n'
        "from . import models\n"
        "from .client import ApiError, XrayPrismClient\n\n"
        "__all__ = ['ApiError', 'XrayPrismClient', 'models']\n"
    )


def readme_body(spec: dict[str, Any]) -> str:
    method_names = []
    for path, path_item in spec["paths"].items():
        if not path.startswith("/api/"):
            continue
        for operation in path_item.values():
            if isinstance(operation, dict):
                method_names.append(camel_to_snake(operation["operationId"]))

    method_names = sorted(set(method_names))
    methods_md = "\n".join(f"- `{name}()`" for name in method_names)
    return f"""# xray-prism-sdk

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
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -m pip install -e .\\sdk\\python

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
    lease = client.acquire_lease({{"workspace_id": "crawler", "ttl": 60}})
    print(lease["http_proxy_url"])
    print(lease["socks5_proxy_url"])
    print(lease["socks5h_proxy_url"])
```

## Mixed-Port 代理语义

当前服务端返回的每个本地代理端口都基于 Xray `socks` inbound，同一端口同时兼容 HTTP 与 SOCKS5：

```python
from xray_prism_sdk import XrayPrismClient

with XrayPrismClient(base_url="http://127.0.0.1:8000", token="YOUR_TOKEN") as client:
    lease = client.acquire_lease({{"workspace_id": "crawler", "ttl": 60}})
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

payload = {{
    "name": "my-subscription",
    "url": "https://example.com/subscription"
}}

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    result = client.create_subscription(payload)
    print(result)
```

### 3. 添加代理

```python
from xray_prism_sdk import XrayPrismClient

payload = {{
    "node_ids": ["node-1", "node-2"],
    "start_port": 10808,
}}

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
    acquired = client.acquire_lease({{"workspace_id": "crawler", "ttl": 120}})
    proxy_address = acquired["proxy_address"]
    http_proxy_url = acquired["http_proxy_url"]
    socks5_proxy_url = acquired["socks5_proxy_url"]
    socks5h_proxy_url = acquired["socks5h_proxy_url"]

    print(http_proxy_url)
    print(socks5_proxy_url)
    print(socks5h_proxy_url)

    released = client.release_lease({{
        "workspace_id": "crawler",
        "proxy_address": proxy_address,
        "cooldown_seconds": 300,
    }})
    print(released)
```

### 5. 更新健康检查配置

```python
from xray_prism_sdk import XrayPrismClient

payload = {{
    "enabled": True,
    "check_interval_seconds": 60,
    "test_target": "http://ip-api.com/json",
    "test_timeout_seconds": 10,
}}

with XrayPrismClient(base_url="http://127.0.0.1:8000") as client:
    config = client.update_health_config(payload)
    print(config)
```

## 请求模型

SDK 在 `xray_prism_sdk.models` 中生成了请求 `TypedDict`，适合在 IDE 和类型检查器中使用：

```python
from xray_prism_sdk import XrayPrismClient, models

payload: models.LeaseAcquireRequest = {{
    "workspace_id": "crawler",
    "ttl": 60,
}}

with XrayPrismClient(base_url="http://127.0.0.1:8000", token="YOUR_TOKEN") as client:
    result = client.acquire_lease(payload)
    print(result)
```

当前已生成的请求模型：

- `models.HealthConfigUpdate`
- `models.LeaseAcquireRequest`
- `models.LeaseReleaseRequest`
- `models.ProxyAddRequest`

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
.venv\\Scripts\\python.exe scripts\\generate_python_sdk.py

# 如需额外导出 OpenAPI JSON
.venv\\Scripts\\python.exe scripts\\generate_python_sdk.py --write-openapi .\\tmp\\openapi.json
```

生成后建议执行：

```bash
.venv\\Scripts\\python.exe -m pytest tests/test_openapi.py tests/test_python_sdk.py -q
```

## 已生成方法

{methods_md}
"""


def pyproject_body() -> str:
    return """[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "xray-prism-sdk"
version = "0.1.0"
description = "Python SDK for the Xray-Prism OpenAPI contract"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "httpx>=0.28.0",
]

[tool.setuptools.packages.find]
where = ["src"]
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Python SDK from the local FastAPI OpenAPI schema."
    )
    parser.add_argument(
        "--write-openapi",
        type=Path,
        help="Optional path to also write the generated OpenAPI JSON.",
    )
    return parser.parse_args()


def generate(write_openapi: Path | None = None) -> None:
    spec = app.openapi()

    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    SDK_ROOT.mkdir(parents=True, exist_ok=True)
    if write_openapi is not None:
        write_openapi.parent.mkdir(parents=True, exist_ok=True)
        write_openapi.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (PACKAGE_ROOT / "__init__.py").write_text(init_body(), encoding="utf-8")
    (PACKAGE_ROOT / "models.py").write_text(typed_dict_body(spec), encoding="utf-8")
    (PACKAGE_ROOT / "client.py").write_text(client_body(spec), encoding="utf-8")
    (PACKAGE_ROOT / "py.typed").write_text("", encoding="utf-8")
    (SDK_ROOT / "README.md").write_text(readme_body(spec), encoding="utf-8")
    (SDK_ROOT / "pyproject.toml").write_text(pyproject_body(), encoding="utf-8")


if __name__ == "__main__":
    args = parse_args()
    generate(write_openapi=args.write_openapi)
