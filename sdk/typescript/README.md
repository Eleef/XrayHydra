# xray-prism-typescript-sdk

本目录包含基于服务端 OpenAPI 契约生成的 TypeScript SDK，适合浏览器端、Node.js 脚本或其他 TypeScript 客户端接入 Xray-Prism API。

## 生成

```bash
# Windows
.venv\Scripts\python.exe scripts\generate_typescript_sdk.py

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
import { XrayPrismClient, models } from 'xray-prism-typescript-sdk';

const client = new XrayPrismClient({
  baseUrl: 'http://127.0.0.1:8000',
  token: process.env.LEASE_API_TOKEN ?? null,
});

const payload: models.LeaseAcquireRequest = { workspace_id: 'crawler_a', ttl: 60 };
const lease = await client.acquire_lease(payload);
console.log(lease.http_proxy_url);

await client.set_manual_lease_cooldown({ workspace_id: 'crawler_a', proxy_port: 10022 });
await client.recall_lease_cooldown({ workspace_id: 'crawler_a', proxy_port: 10022 });
```

## 说明

- SDK 基于运行中服务的 `/openapi.json` 结构生成，请在接口变更后重新生成。
- 仓库默认不保留巨大的 OpenAPI JSON 副本，避免影响上下文和代码审查。
- 当前产物是 source-first TypeScript SDK；如需分发给外部 npm 使用，可在本目录执行 `npm install` 和 `npm run build`。

## 已生成方法

- `acquire_lease()`
- `add_proxies()`
- `clear_all_proxies()`
- `create_subscription()`
- `delete_subscription()`
- `get_health_config()`
- `get_health_status()`
- `get_lease_stats()`
- `get_lease_status()`
- `get_node()`
- `get_proxy_health_status()`
- `get_subscription()`
- `get_system_status()`
- `list_proxies()`
- `list_subscription_nodes()`
- `list_subscriptions()`
- `recall_lease_cooldown()`
- `refresh_subscription()`
- `release_lease()`
- `remove_proxy()`
- `reset_all_health()`
- `reset_proxy_health()`
- `restart_xray()`
- `run_health_check()`
- `set_manual_lease_cooldown()`
- `start_health_monitoring()`
- `start_xray()`
- `stop_health_monitoring()`
- `stop_xray()`
- `test_all_proxies()`
- `test_single_proxy()`
- `update_health_config()`
