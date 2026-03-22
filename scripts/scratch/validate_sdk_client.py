from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SDK_SRC = ROOT / "sdk" / "python" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from xray_prism_sdk import ApiError, XrayPrismClient


def _extract_items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "subscriptions", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def main() -> int:
    base_url = "http://127.0.0.1:8000"

    try:
        with XrayPrismClient(base_url=base_url, timeout=10.0) as client:
            status = client.get_system_status()
            subscriptions = client.list_subscriptions()
            subscription_items = _extract_items(subscriptions)

            xray_status = status.get("xray_status", "unknown") if isinstance(status, dict) else "unknown"
            subscription_count = len(subscription_items)

            print(f"OK base_url={base_url}")
            print(f"system_status xray_status={xray_status}")
            print(f"subscriptions count={subscription_count}")

            if subscription_items:
                first = subscription_items[0]
                print(
                    "subscriptions first="
                    f"{first.get('id', 'n/a')}:{first.get('name', 'n/a')}"
                )

            try:
                lease_stats = client.get_lease_stats()
            except ApiError as exc:
                print(f"lease_stats skipped api_error={exc.status_code}")
            else:
                if isinstance(lease_stats, dict):
                    active = lease_stats.get(
                        "total_active_leases",
                        lease_stats.get("active_leases", lease_stats.get("active", "n/a")),
                    )
                    print(f"lease_stats active={active}")
                else:
                    print("lease_stats ok")

    except ApiError as exc:
        print(f"API_ERROR status={exc.status_code} payload={exc.payload}")
        return 1
    except Exception as exc:
        print(f"ERROR {exc.__class__.__name__}: {exc}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
