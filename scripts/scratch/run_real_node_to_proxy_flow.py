from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Any

import requests


def _log(message: str) -> None:
    print(f"[flow] {message}")


def _request(
    session: requests.Session,
    method: str,
    base_url: str,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> Any:
    url = f"{base_url}{endpoint}"
    response = session.request(method, url, params=params, json=payload, timeout=timeout)
    try:
        body = response.json()
    except Exception:
        body = {"detail": response.text}

    if response.status_code >= 400:
        detail = body.get("detail") if isinstance(body, dict) else body
        raise RuntimeError(f"{method} {endpoint} failed ({response.status_code}): {detail}")
    return body


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Real validation flow: subscription nodes -> node tests -> auto-select success "
            "-> add proxies -> proxy re-test."
        )
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL.")
    parser.add_argument("--subscription-url", required=True, help="Real subscription URL to validate.")
    parser.add_argument(
        "--subscription-name",
        default=f"real-flow-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        help="Name used when creating subscription.",
    )
    parser.add_argument("--max-nodes", type=int, default=20, help="Max nodes to test from subscription.")
    parser.add_argument("--node-timeout", type=int, default=6, help="Timeout seconds for node tests.")
    parser.add_argument("--proxy-timeout", type=int, default=6, help="Timeout seconds for proxy re-test.")
    parser.add_argument("--proxy-workers", type=int, default=20, help="Workers for proxy re-test.")
    parser.add_argument("--proxy-attempts", type=int, default=1, help="Attempts for proxy re-test.")
    parser.add_argument("--start-port", type=int, default=10000, help="Start port when adding proxies.")
    parser.add_argument(
        "--auto-start-xray",
        dest="auto_start_xray",
        action="store_true",
        default=True,
        help="Start Xray automatically before proxy re-test if needed (default: enabled).",
    )
    parser.add_argument(
        "--no-auto-start-xray",
        dest="auto_start_xray",
        action="store_false",
        help="Do not auto-start Xray before proxy re-test.",
    )
    parser.add_argument(
        "--cleanup-subscription",
        action="store_true",
        help="Delete created subscription at the end.",
    )
    parser.add_argument(
        "--cleanup-added-proxies",
        action="store_true",
        help="Remove proxies added by this run at the end.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    base_url = args.base_url.rstrip("/")
    session = requests.Session()

    created_subscription_id: str | None = None
    added_ports: list[int] = []

    try:
        _log(f"Checking server at {base_url}")
        _request(session, "GET", base_url, "/health", timeout=8.0)

        _log("Creating subscription")
        created_subscription = _request(
            session,
            "POST",
            base_url,
            "/api/subscriptions",
            payload={"name": args.subscription_name, "url": args.subscription_url},
        )
        created_subscription_id = created_subscription.get("id")
        if not created_subscription_id:
            raise RuntimeError("Create subscription succeeded but missing subscription id")
        _log(f"Subscription created: {created_subscription_id}")

        _log("Loading subscription nodes")
        nodes_payload = _request(
            session,
            "GET",
            base_url,
            f"/api/subscriptions/{created_subscription_id}/nodes",
        )
        nodes = nodes_payload.get("nodes", []) if isinstance(nodes_payload, dict) else []
        if not nodes:
            raise RuntimeError("Subscription has no nodes")

        selected_nodes = nodes[: max(1, args.max_nodes)]
        selected_node_ids = [node["id"] for node in selected_nodes if node.get("id")]
        node_by_id = {node["id"]: node for node in selected_nodes if node.get("id")}
        _log(f"Selected nodes for testing: {len(selected_node_ids)}")

        _log("Running node tests (multi_target)")
        node_test_payload = _request(
            session,
            "POST",
            base_url,
            "/api/nodes/test",
            payload={
                "node_ids": selected_node_ids,
                "timeout": args.node_timeout,
                "test_profile": "multi_target",
            },
            timeout=max(30.0, args.node_timeout * max(1, len(selected_node_ids))),
        )

        node_results = node_test_payload.get("results", [])
        node_success = int(node_test_payload.get("success_count", 0))
        node_failed = int(node_test_payload.get("failed_count", 0))
        _log(f"Node test summary: success={node_success}, failed={node_failed}")

        success_addable_ids: list[str] = []
        for item in node_results:
            node_id = item.get("node_id")
            if not node_id:
                continue
            node_meta = node_by_id.get(node_id, {})
            if item.get("status") == "success" and not bool(node_meta.get("in_proxy_pool")):
                success_addable_ids.append(node_id)

        success_addable_ids = list(dict.fromkeys(success_addable_ids))
        _log(f"Auto-selected successful nodes not in pool: {len(success_addable_ids)}")
        if not success_addable_ids:
            raise RuntimeError("No successful addable nodes after node tests")

        _log("Adding selected successful nodes to proxy pool")
        added_proxies = _request(
            session,
            "POST",
            base_url,
            "/api/proxies",
            payload={"node_ids": success_addable_ids, "start_port": args.start_port},
        )
        if not isinstance(added_proxies, list) or not added_proxies:
            raise RuntimeError("No proxies were added")
        added_ports = [int(item["port"]) for item in added_proxies if item.get("port") is not None]
        _log(f"Added proxies: {len(added_ports)} ports")

        status_payload = _request(session, "GET", base_url, "/api/system/status")
        xray_status = status_payload.get("xray_status", "unknown") if isinstance(status_payload, dict) else "unknown"
        if xray_status != "running":
            if args.auto_start_xray:
                _log("Xray not running, starting automatically")
                _request(session, "POST", base_url, "/api/system/start")
            else:
                raise RuntimeError("Xray is not running, cannot run proxy re-test")

        _log("Running proxy re-test")
        proxy_test_payload = _request(
            session,
            "POST",
            base_url,
            "/api/proxies/test-all",
            params={
                "timeout": args.proxy_timeout,
                "workers": args.proxy_workers,
                "attempts": args.proxy_attempts,
            },
            timeout=max(30.0, args.proxy_timeout * max(1, len(added_ports))),
        )
        proxy_success = int(proxy_test_payload.get("success_count", 0))
        proxy_failed = int(proxy_test_payload.get("failed_count", 0))
        _log(f"Proxy re-test summary: success={proxy_success}, failed={proxy_failed}")

        _log("Flow completed")
        print(
            f"RESULT subscription_id={created_subscription_id} "
            f"nodes_tested={len(selected_node_ids)} "
            f"node_success={node_success} node_failed={node_failed} "
            f"added_proxies={len(added_ports)} proxy_success={proxy_success} proxy_failed={proxy_failed}"
        )
        return 0

    except Exception as exc:
        _log(f"FAILED: {exc}")
        return 1

    finally:
        if args.cleanup_added_proxies and added_ports:
            _log(f"Cleanup proxies: {len(added_ports)}")
            for port in added_ports:
                try:
                    _request(session, "DELETE", base_url, f"/api/proxies/{port}")
                except Exception as exc:
                    _log(f"Cleanup proxy failed port={port}: {exc}")

        if args.cleanup_subscription and created_subscription_id:
            _log(f"Cleanup subscription: {created_subscription_id}")
            try:
                _request(session, "DELETE", base_url, f"/api/subscriptions/{created_subscription_id}")
            except Exception as exc:
                _log(f"Cleanup subscription failed: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
