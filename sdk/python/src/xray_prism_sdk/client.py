"""Python SDK client generated from the OpenAPI schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from . import models


@dataclass
class ApiError(Exception):
    """Raised when the API returns a non-2xx response."""

    status_code: int
    payload: Any

    def __str__(self) -> str:
        if isinstance(self.payload, dict):
            message = self.payload.get('detail') or self.payload.get('message') or self.payload
        else:
            message = self.payload
        return f'API error {self.status_code}: {message}'


class XrayPrismClient:
    """Synchronous Python SDK for the Xray-Prism REST API."""

    def __init__(
        self,
        base_url: str = 'http://127.0.0.1:8000',
        token: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> 'XrayPrismClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        requires_auth: bool = False,
    ) -> Any:
        headers: dict[str, str] = {'Accept': 'application/json'}
        if json_body is not None:
            headers['Content-Type'] = 'application/json'
        if requires_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        url = path if not self.base_url else f'{self.base_url}{path}'
        response = self._client.request(method, url, params=params, json=json_body, headers=headers, timeout=self.timeout)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            raise ApiError(response.status_code, payload)
        if response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        return response.text

    def list_subscriptions(self) -> Any:
        """Get Subscriptions."""
        # Get all subscriptions.
        params = None
        json_body = None
        return self._request('GET', '/api/subscriptions', params=params, json_body=json_body, requires_auth=False)

    def create_subscription(self, payload: models.SubscriptionCreate) -> Any:
        """Create Subscription."""
        # Create a new subscription and fetch its nodes.
        params = None
        json_body = dict(payload)
        return self._request('POST', '/api/subscriptions', params=params, json_body=json_body, requires_auth=False)

    def get_subscription(self, sub_id: str) -> Any:
        """Get Subscription."""
        # Get a subscription by ID.
        params = None
        json_body = None
        return self._request('GET', f'/api/subscriptions/{sub_id}', params=params, json_body=json_body, requires_auth=False)

    def delete_subscription(self, sub_id: str) -> Any:
        """Delete Subscription."""
        # Delete a subscription and all its nodes.
        params = None
        json_body = None
        return self._request('DELETE', f'/api/subscriptions/{sub_id}', params=params, json_body=json_body, requires_auth=False)

    def refresh_subscription(self, sub_id: str) -> Any:
        """Refresh Subscription."""
        # Refresh a subscription's nodes from the source URL.
        params = None
        json_body = None
        return self._request('POST', f'/api/subscriptions/{sub_id}/refresh', params=params, json_body=json_body, requires_auth=False)

    def list_subscription_nodes(self, sub_id: str) -> Any:
        """Get Subscription Nodes."""
        # Get all nodes for a subscription.
        params = None
        json_body = None
        return self._request('GET', f'/api/subscriptions/{sub_id}/nodes', params=params, json_body=json_body, requires_auth=False)

    def get_node(self, node_id: str) -> Any:
        """Get Node."""
        # Get a single node by ID.
        params = None
        json_body = None
        return self._request('GET', f'/api/nodes/{node_id}', params=params, json_body=json_body, requires_auth=False)

    def list_proxies(self) -> Any:
        """Get Proxies."""
        # Get all active proxies.
        params = None
        json_body = None
        return self._request('GET', '/api/proxies', params=params, json_body=json_body, requires_auth=False)

    def add_proxies(self, payload: models.ProxyAddRequest) -> Any:
        """Add Proxies."""
        # Add nodes to the active proxy list.
        params = None
        json_body = dict(payload)
        return self._request('POST', '/api/proxies', params=params, json_body=json_body, requires_auth=False)

    def clear_all_proxies(self) -> Any:
        """Clear All Proxies."""
        # Remove all proxies.
        params = None
        json_body = None
        return self._request('DELETE', '/api/proxies', params=params, json_body=json_body, requires_auth=False)

    def remove_proxy(self, port: int) -> Any:
        """Remove Proxy."""
        # Remove a proxy by port.
        params = None
        json_body = None
        return self._request('DELETE', f'/api/proxies/{port}', params=params, json_body=json_body, requires_auth=False)

    def test_all_proxies(self, timeout: int = 5, workers: int = 20) -> Any:
        """Test All Proxies."""
        # Test all active proxies.
        params: dict[str, Any] = {}
        if timeout is not None:
            params['timeout'] = timeout
        if workers is not None:
            params['workers'] = workers
        json_body = None
        return self._request('POST', '/api/proxies/test-all', params=params, json_body=json_body, requires_auth=False)

    def test_single_proxy(self, port: int, timeout: int = 5) -> Any:
        """Test Single Proxy."""
        # Test a single proxy.
        params: dict[str, Any] = {}
        if timeout is not None:
            params['timeout'] = timeout
        json_body = None
        return self._request('POST', f'/api/proxies/{port}/test', params=params, json_body=json_body, requires_auth=False)

    def get_system_status(self) -> Any:
        """Get System Status."""
        # Get overall system status.
        params = None
        json_body = None
        return self._request('GET', '/api/system/status', params=params, json_body=json_body, requires_auth=False)

    def start_xray(self) -> Any:
        """Start Xray."""
        # Start the Xray process.
        params = None
        json_body = None
        return self._request('POST', '/api/system/start', params=params, json_body=json_body, requires_auth=False)

    def stop_xray(self) -> Any:
        """Stop Xray."""
        # Stop the Xray process.
        params = None
        json_body = None
        return self._request('POST', '/api/system/stop', params=params, json_body=json_body, requires_auth=False)

    def restart_xray(self) -> Any:
        """Restart Xray."""
        # Restart the Xray process.
        params = None
        json_body = None
        return self._request('POST', '/api/system/restart', params=params, json_body=json_body, requires_auth=False)

    def get_health_status(self) -> Any:
        """Get Health Status."""
        # Get health status for all monitored proxies.
        params = None
        json_body = None
        return self._request('GET', '/api/health/status', params=params, json_body=json_body, requires_auth=False)

    def get_proxy_health_status(self, port: int) -> Any:
        """Get Proxy Health Status."""
        # Get health status for a specific proxy.
        params = None
        json_body = None
        return self._request('GET', f'/api/health/status/{port}', params=params, json_body=json_body, requires_auth=False)

    def get_health_config(self) -> Any:
        """Get Health Config."""
        # Get health monitoring configuration.
        params = None
        json_body = None
        return self._request('GET', '/api/health/config', params=params, json_body=json_body, requires_auth=False)

    def update_health_config(self, payload: models.HealthConfigUpdate) -> Any:
        """Update Health Config."""
        # Update health monitoring configuration.
        params = None
        json_body = dict(payload)
        return self._request('PUT', '/api/health/config', params=params, json_body=json_body, requires_auth=False)

    def reset_proxy_health(self, port: int) -> Any:
        """Reset Proxy Health."""
        # Reset health state for a specific proxy.
        params = None
        json_body = None
        return self._request('POST', f'/api/health/reset/{port}', params=params, json_body=json_body, requires_auth=False)

    def reset_all_health(self) -> Any:
        """Reset All Health."""
        # Reset health states for all proxies.
        params = None
        json_body = None
        return self._request('POST', '/api/health/reset-all', params=params, json_body=json_body, requires_auth=False)

    def run_health_check(self) -> Any:
        """Run Health Check."""
        # Manually trigger a health check on all active proxies.
        # This is in addition to automatic background monitoring.
        params = None
        json_body = None
        return self._request('POST', '/api/health/check', params=params, json_body=json_body, requires_auth=False)

    def start_health_monitoring(self) -> Any:
        """Start Monitoring."""
        # Start background health monitoring.
        params = None
        json_body = None
        return self._request('POST', '/api/health/monitoring/start', params=params, json_body=json_body, requires_auth=False)

    def stop_health_monitoring(self) -> Any:
        """Stop Monitoring."""
        # Stop background health monitoring.
        params = None
        json_body = None
        return self._request('POST', '/api/health/monitoring/stop', params=params, json_body=json_body, requires_auth=False)

    def acquire_lease(self, payload: models.LeaseAcquireRequest) -> Any:
        """申请代理租约."""
        # 为指定 workspace 申请一个代理租约。
        # - **workspace_id**: 业务隔离标识（不同 workspace 可使用同一代理）
        # - **ttl**: 租约有效时间（秒），超时自动释放
        # 返回代理地址和租约ID，或 503 表示无可用代理。
        params = None
        json_body = dict(payload)
        return self._request('POST', '/api/lease/acquire', params=params, json_body=json_body, requires_auth=True)

    def release_lease(self, payload: models.LeaseReleaseRequest) -> Any:
        """归还代理租约."""
        # 归还代理租约并可选设置冷却期。
        # - **workspace_id**: 业务隔离标识
        # - **proxy_address**: 要归还的代理地址
        # - **cooldown_seconds**: 冷却时间（秒），期间该 workspace 不会再获取此代理
        # 幂等设计：重复归还不会报错。
        params = None
        json_body = dict(payload)
        return self._request('POST', '/api/lease/release', params=params, json_body=json_body, requires_auth=True)

    def get_lease_status(self, workspace_id: str | None = None) -> Any:
        """查看租约状态."""
        # 查看当前租约和冷却状态。
        # - **workspace_id**: 可选，指定则只返回该 workspace 的信息
        params: dict[str, Any] = {}
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        json_body = None
        return self._request('GET', '/api/lease/status', params=params, json_body=json_body, requires_auth=True)

    def get_lease_stats(self) -> Any:
        """获取租约统计."""
        # 获取租约系统的统计信息，包括可用代理数、活跃租约数、使用频率等。
        params = None
        json_body = None
        return self._request('GET', '/api/lease/stats', params=params, json_body=json_body, requires_auth=True)
