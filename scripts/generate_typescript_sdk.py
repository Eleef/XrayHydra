"""
Generate the TypeScript SDK package from the current FastAPI OpenAPI schema.
"""
from __future__ import annotations

import json
import keyword
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SDK_ROOT = ROOT / "sdk" / "typescript"
SRC_ROOT = SDK_ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app


TS_TYPE_MAP = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "object": "Record<string, unknown>",
}


def camel_to_snake(value: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
    return sanitize_name(value)


def snake_to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


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


def ts_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema_ref_name(schema) or "unknown"

    if "enum" in schema:
        return " | ".join(json.dumps(item) for item in schema["enum"])

    if "anyOf" in schema:
        return " | ".join(ts_type(item) for item in schema["anyOf"])

    schema_type = schema.get("type")
    if schema_type == "array":
        return f"Array<{ts_type(schema.get('items', {}))}>"

    if schema_type == "object":
        properties = schema.get("properties") or {}
        if properties:
            required = set(schema.get("required", []))
            parts = []
            for prop_name, prop_schema in properties.items():
                optional = "" if prop_name in required else "?"
                parts.append(f"{prop_name}{optional}: {ts_type(prop_schema)}")
            return "{ " + "; ".join(parts) + " }"
        return "Record<string, unknown>"

    return TS_TYPE_MAP.get(schema_type, "unknown")


def request_schema_names(spec: dict[str, Any]) -> list[str]:
    components = spec.get("components", {}).get("schemas", {})
    names = {
        name for name in components
        if name.endswith("Request") or name.endswith("Update")
    }

    for path_item in spec.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody", {})
            schema = request_body.get("content", {}).get("application/json", {}).get("schema")
            schema_name = schema_ref_name(schema)
            if schema_name:
                names.add(schema_name)

    return sorted(names)


def model_body(spec: dict[str, Any]) -> str:
    components = spec.get("components", {}).get("schemas", {})
    names = request_schema_names(spec)
    lines = [
        "/* eslint-disable */",
        "// Typed request payloads generated from the OpenAPI schema.",
        "",
    ]

    for name in names:
        schema = components.get(name, {})
        if schema.get("type") != "object":
            continue
        required = set(schema.get("required", []))
        lines.append(f"export interface {name} {{")
        for prop_name, prop_schema in schema.get("properties", {}).items():
            optional = "" if prop_name in required else "?"
            lines.append(f"  {prop_name}{optional}: {ts_type(prop_schema)};")
        if not schema.get("properties"):
            lines.append("  [key: string]: unknown;")
        lines.append("}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def client_body(spec: dict[str, Any]) -> str:
    lines = [
        "/* eslint-disable */",
        "// TypeScript SDK client generated from the OpenAPI schema.",
        "",
        "import * as models from './models';",
        "",
        "export class ApiError extends Error {",
        "  constructor(public statusCode: number, public payload: unknown) {",
        "    const message = typeof payload === 'object' && payload !== null",
        "      ? String((payload as Record<string, unknown>).detail ?? (payload as Record<string, unknown>).message ?? JSON.stringify(payload))",
        "      : String(payload);",
        "    super(`API error ${statusCode}: ${message}`);",
        "    this.name = 'ApiError';",
        "  }",
        "}",
        "",
        "export interface ClientOptions {",
        "  baseUrl?: string;",
        "  token?: string | null;",
        "  fetchImpl?: typeof fetch;",
        "}",
        "",
        "export class XrayPrismClient {",
        "  private readonly baseUrl: string;",
        "  private readonly token: string | null;",
        "  private readonly fetchImpl: typeof fetch;",
        "",
        "  constructor(options: ClientOptions = {}) {",
        "    const rawBaseUrl = options.baseUrl ?? 'http://127.0.0.1:8000';",
        "    this.baseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;",
        "    this.token = options.token ?? null;",
        "    this.fetchImpl = options.fetchImpl ?? fetch;",
        "  }",
        "",
        "  private async request(method: string, path: string, params?: Record<string, unknown>, body?: unknown, requiresAuth = false): Promise<any> {",
        "    const url = new URL(`${this.baseUrl}${path}`);",
        "    if (params) {",
        "      Object.entries(params).forEach(([key, value]) => {",
        "        if (value !== undefined && value !== null) {",
        "          url.searchParams.set(key, String(value));",
        "        }",
        "      });",
        "    }",
        "",
        "    const headers: Record<string, string> = { Accept: 'application/json' };",
        "    if (body !== undefined && body !== null) {",
        "      headers['Content-Type'] = 'application/json';",
        "    }",
        "    if (requiresAuth && this.token) {",
        "      headers.Authorization = `Bearer ${this.token}`;",
        "    }",
        "",
        "    const response = await this.fetchImpl(url.toString(), {",
        "      method,",
        "      headers,",
        "      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,",
        "    });",
        "",
        "    const contentType = response.headers.get('content-type') ?? '';",
        "    const payload = contentType.includes('application/json') ? await response.json() : await response.text();",
        "    if (!response.ok) {",
        "      throw new ApiError(response.status, payload);",
        "    }",
        "    return payload;",
        "  }",
        "",
    ]

    for path, path_item in spec.get("paths", {}).items():
        if not path.startswith("/api/"):
            continue

        for http_method, operation in path_item.items():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue

            operation_id = operation["operationId"]
            method_name = camel_to_snake(operation_id)
            parameters = operation.get("parameters", [])
            path_params = [item for item in parameters if item.get("in") == "path"]
            query_params = [item for item in parameters if item.get("in") == "query"]
            request_body = operation.get("requestBody", {})
            request_schema = request_body.get("content", {}).get("application/json", {}).get("schema")
            request_schema_name = schema_ref_name(request_schema)
            requires_auth = bool(operation.get("security"))

            signature_parts = []
            for param in path_params:
                param_name = sanitize_name(param["name"])
                signature_parts.append(f"{param_name}: {ts_type(param.get('schema', {}))}")

            if query_params:
                query_bits = []
                for param in query_params:
                    param_name = sanitize_name(param["name"])
                    schema = param.get("schema", {})
                    optional = "" if param.get("required") else "?"
                    query_bits.append(f"{param_name}{optional}: {ts_type(schema)}")
                signature_parts.append(f"query: {{ {'; '.join(query_bits)} }} = {{}}")

            if request_schema_name:
                signature_parts.append(f"payload: models.{request_schema_name}")

            signature = ", ".join(signature_parts)
            lines.append(f"  async {method_name}({signature}) {{")

            path_literal = path
            for param in path_params:
                name = sanitize_name(param["name"])
                path_literal = path_literal.replace("{" + param["name"] + "}", f"${{{name}}}")

            params_expr = "undefined"
            if query_params:
                params_expr = "Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined && value !== null))"

            body_expr = "undefined"
            if request_schema_name:
                body_expr = "payload"

            lines.append(
                f"    return this.request('{http_method.upper()}', `{path_literal}`, {params_expr}, {body_expr}, {str(requires_auth).lower()});"
            )
            lines.append("  }")
            lines.append("")

    lines.extend([
        "}",
        "",
        "export { models };",
    ])

    return "\n".join(lines).rstrip() + "\n"


def package_json_body() -> str:
    return json.dumps(
        {
            "name": "xray-prism-typescript-sdk",
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "main": "./src/index.ts",
            "types": "./src/index.ts",
            "scripts": {
                "build": "tsc -p tsconfig.json"
            },
            "devDependencies": {
                "typescript": "^5.9.0"
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def tsconfig_body() -> str:
    return json.dumps(
        {
            "compilerOptions": {
                "target": "ES2022",
                "module": "ES2022",
                "moduleResolution": "Bundler",
                "declaration": True,
                "outDir": "dist",
                "strict": True,
                "skipLibCheck": True,
            },
            "include": ["src/**/*.ts"],
        },
        indent=2,
    ) + "\n"


def readme_body(spec: dict[str, Any]) -> str:
    methods = []
    for path, path_item in spec.get("paths", {}).items():
        if not path.startswith("/api/"):
            continue
        for operation in path_item.values():
            if isinstance(operation, dict) and operation.get("operationId"):
                methods.append(camel_to_snake(operation["operationId"]))
    methods = "\n".join(f"- `{name}()`" for name in sorted(set(methods)))

    return f"""# xray-prism-typescript-sdk

本目录包含基于服务端 OpenAPI 契约生成的 TypeScript SDK，适合浏览器端、Node.js 脚本或其他 TypeScript 客户端接入 Xray-Prism API。

## 生成

```bash
# Windows
.venv\\Scripts\\python.exe scripts\\generate_typescript_sdk.py

# Linux / macOS
source .venv/bin/activate
python scripts/generate_typescript_sdk.py
```

## 安装

```bash
npm install ./sdk/typescript
```

## 使用示例

```ts
import {{ XrayPrismClient, models }} from 'xray-prism-typescript-sdk';

const client = new XrayPrismClient({{
  baseUrl: 'http://127.0.0.1:8000',
  token: process.env.LEASE_API_TOKEN ?? null,
}});

const payload: models.LeaseAcquireRequest = {{ workspace_id: 'crawler_a', ttl: 60 }};
const lease = await client.acquire_lease(payload);
console.log(lease.http_proxy_url);

await client.set_manual_lease_cooldown({{ workspace_id: 'crawler_a', proxy_port: 10022 }});
await client.recall_lease_cooldown({{ workspace_id: 'crawler_a', proxy_port: 10022 }});
```

## 说明

- SDK 基于运行中服务的 `/openapi.json` 结构生成，请在接口变更后重新生成。
- 仓库默认不保留巨大的 OpenAPI JSON 副本，避免影响上下文和代码审查。
- 当前产物是 source-first TypeScript SDK；如需分发给外部 npm 使用，可在本目录执行 `npm install` 和 `npm run build`。

## 已生成方法

{methods}
"""


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    spec = app.openapi()

    write_file(SDK_ROOT / "package.json", package_json_body())
    write_file(SDK_ROOT / "tsconfig.json", tsconfig_body())
    write_file(SDK_ROOT / "README.md", readme_body(spec))
    write_file(SRC_ROOT / "models.ts", model_body(spec))
    write_file(SRC_ROOT / "index.ts", client_body(spec))


if __name__ == "__main__":
    main()
