"""
Unit tests for multi-attempt proxy testing and cooldown candidate generation.
"""
from types import SimpleNamespace
from unittest.mock import patch

from api.services.proxy_service import ProxyService


def _make_result(port: int, success: bool, latency_ms: int | None = None, exit_ip: str | None = None, error: str | None = None):
    return SimpleNamespace(
        local_port=port,
        success=success,
        latency_ms=latency_ms,
        exit_ip=exit_ip,
        error=error,
    )


def test_test_all_proxies_collects_cooldown_candidates_after_all_attempts_fail():
    service = ProxyService()
    service._data = {
        "proxies": [
            {"port": 10001, "node_id": "node_a", "node_name": "Node A", "protocol": "trojan", "address": "a", "server_port": 443},
            {"port": 10002, "node_id": "node_b", "node_name": "Node B", "protocol": "trojan", "address": "b", "server_port": 443},
        ],
        "start_port": 10000,
    }

    mappings = [SimpleNamespace(local_port=10001), SimpleNamespace(local_port=10002)]
    tester_runs = [
        [
            _make_result(10001, False, error="timeout"),
            _make_result(10002, False, error="timeout"),
        ],
        [
            _make_result(10001, True, latency_ms=320, exit_ip="203.0.113.1"),
            _make_result(10002, False, error="timeout"),
        ],
    ]

    with patch.object(service, "_load_data", return_value=service._data), \
         patch.object(service, "_save_data", return_value=None), \
         patch.object(service, "_is_xray_running", return_value=True), \
         patch.object(service, "_build_proxy_nodes", return_value=mappings), \
         patch("api.services.proxy_service.ProxyTester") as tester_cls:
        tester_cls.return_value.test_all.side_effect = tester_runs
        result = service.test_all_proxies(timeout=5, workers=20, attempts=2)

    assert result["attempts"] == 2
    assert result["success_count"] == 1
    assert result["failed_count"] == 1
    assert result["cooldown_candidates"] == [
        {
            "node_id": "node_b",
            "name": "Node B",
            "proxy_port": 10002,
            "failed_attempts": 2,
            "error": "timeout",
        }
    ]

    proxy_a = next(item for item in service._data["proxies"] if item["port"] == 10001)
    proxy_b = next(item for item in service._data["proxies"] if item["port"] == 10002)
    assert proxy_a["test_status"] == "success"
    assert proxy_a["exit_ip"] == "203.0.113.1"
    assert proxy_b["test_status"] == "failed"
    assert proxy_b["exit_ip"] is None
