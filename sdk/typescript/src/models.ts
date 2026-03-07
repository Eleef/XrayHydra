/* eslint-disable */
// Typed request payloads generated from the OpenAPI schema.

export interface HealthConfigUpdate {
  enabled?: boolean | unknown;
  check_interval_seconds?: number | unknown;
  test_target?: string | unknown;
  test_timeout_seconds?: number | unknown;
}

export interface LeaseAcquireRequest {
  workspace_id: string;
  ttl?: number;
}

export interface LeaseCooldownRequest {
  workspace_id: string;
  proxy_port: number;
}

export interface LeaseReleaseRequest {
  workspace_id: string;
  proxy_address: string;
  cooldown_seconds?: number;
}

export interface ProxyAddRequest {
  node_ids: Array<string>;
  start_port?: number;
}

export interface SubscriptionCreate {
  name: string;
  url: string;
}
