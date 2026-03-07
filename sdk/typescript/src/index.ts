/* eslint-disable */
// TypeScript SDK client generated from the OpenAPI schema.

import * as models from './models';

export class ApiError extends Error {
  constructor(public statusCode: number, public payload: unknown) {
    const message = typeof payload === 'object' && payload !== null
      ? String((payload as Record<string, unknown>).detail ?? (payload as Record<string, unknown>).message ?? JSON.stringify(payload))
      : String(payload);
    super(`API error ${statusCode}: ${message}`);
    this.name = 'ApiError';
  }
}

export interface ClientOptions {
  baseUrl?: string;
  token?: string | null;
  fetchImpl?: typeof fetch;
}

export class XrayPrismClient {
  private readonly baseUrl: string;
  private readonly token: string | null;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ClientOptions = {}) {
    const rawBaseUrl = options.baseUrl ?? 'http://127.0.0.1:8000';
    this.baseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;
    this.token = options.token ?? null;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  private async request(method: string, path: string, params?: Record<string, unknown>, body?: unknown, requiresAuth = false): Promise<any> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined && body !== null) {
      headers['Content-Type'] = 'application/json';
    }
    if (requiresAuth && this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await this.fetchImpl(url.toString(), {
      method,
      headers,
      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
    });

    const contentType = response.headers.get('content-type') ?? '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      throw new ApiError(response.status, payload);
    }
    return payload;
  }

  async list_subscriptions() {
    return this.request('GET', `/api/subscriptions`, undefined, undefined, false);
  }

  async create_subscription(payload: models.SubscriptionCreate) {
    return this.request('POST', `/api/subscriptions`, undefined, payload, false);
  }

  async get_subscription(sub_id: string) {
    return this.request('GET', `/api/subscriptions/${sub_id}`, undefined, undefined, false);
  }

  async delete_subscription(sub_id: string) {
    return this.request('DELETE', `/api/subscriptions/${sub_id}`, undefined, undefined, false);
  }

  async refresh_subscription(sub_id: string) {
    return this.request('POST', `/api/subscriptions/${sub_id}/refresh`, undefined, undefined, false);
  }

  async list_subscription_nodes(sub_id: string) {
    return this.request('GET', `/api/subscriptions/${sub_id}/nodes`, undefined, undefined, false);
  }

  async get_node(node_id: string) {
    return this.request('GET', `/api/nodes/${node_id}`, undefined, undefined, false);
  }

  async list_proxies() {
    return this.request('GET', `/api/proxies`, undefined, undefined, false);
  }

  async add_proxies(payload: models.ProxyAddRequest) {
    return this.request('POST', `/api/proxies`, undefined, payload, false);
  }

  async clear_all_proxies() {
    return this.request('DELETE', `/api/proxies`, undefined, undefined, false);
  }

  async remove_proxy(port: number) {
    return this.request('DELETE', `/api/proxies/${port}`, undefined, undefined, false);
  }

  async test_all_proxies(query: { timeout?: number; workers?: number } = {}) {
    return this.request('POST', `/api/proxies/test-all`, Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined && value !== null)), undefined, false);
  }

  async test_single_proxy(port: number, query: { timeout?: number } = {}) {
    return this.request('POST', `/api/proxies/${port}/test`, Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined && value !== null)), undefined, false);
  }

  async get_system_status() {
    return this.request('GET', `/api/system/status`, undefined, undefined, false);
  }

  async start_xray() {
    return this.request('POST', `/api/system/start`, undefined, undefined, false);
  }

  async stop_xray() {
    return this.request('POST', `/api/system/stop`, undefined, undefined, false);
  }

  async restart_xray() {
    return this.request('POST', `/api/system/restart`, undefined, undefined, false);
  }

  async get_health_status() {
    return this.request('GET', `/api/health/status`, undefined, undefined, false);
  }

  async get_proxy_health_status(port: number) {
    return this.request('GET', `/api/health/status/${port}`, undefined, undefined, false);
  }

  async get_health_config() {
    return this.request('GET', `/api/health/config`, undefined, undefined, false);
  }

  async update_health_config(payload: models.HealthConfigUpdate) {
    return this.request('PUT', `/api/health/config`, undefined, payload, false);
  }

  async reset_proxy_health(port: number) {
    return this.request('POST', `/api/health/reset/${port}`, undefined, undefined, false);
  }

  async reset_all_health() {
    return this.request('POST', `/api/health/reset-all`, undefined, undefined, false);
  }

  async run_health_check() {
    return this.request('POST', `/api/health/check`, undefined, undefined, false);
  }

  async start_health_monitoring() {
    return this.request('POST', `/api/health/monitoring/start`, undefined, undefined, false);
  }

  async stop_health_monitoring() {
    return this.request('POST', `/api/health/monitoring/stop`, undefined, undefined, false);
  }

  async acquire_lease(payload: models.LeaseAcquireRequest) {
    return this.request('POST', `/api/lease/acquire`, undefined, payload, true);
  }

  async release_lease(payload: models.LeaseReleaseRequest) {
    return this.request('POST', `/api/lease/release`, undefined, payload, true);
  }

  async set_manual_lease_cooldown(payload: models.LeaseCooldownRequest) {
    return this.request('POST', `/api/lease/cooldown/manual`, undefined, payload, true);
  }

  async recall_lease_cooldown(payload: models.LeaseCooldownRequest) {
    return this.request('POST', `/api/lease/cooldown/recall`, undefined, payload, true);
  }

  async get_lease_status(query: { workspace_id?: string | unknown } = {}) {
    return this.request('GET', `/api/lease/status`, Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined && value !== null)), undefined, true);
  }

  async get_lease_stats() {
    return this.request('GET', `/api/lease/stats`, undefined, undefined, true);
  }

}

export { models };
