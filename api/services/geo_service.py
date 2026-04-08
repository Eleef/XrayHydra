"""
Geo lookup service with a small JSON cache.
"""
from __future__ import annotations

import ipaddress
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class GeoLookupError(RuntimeError):
    """Raised when geo lookup fails for a valid IP."""


class GeoService:
    """Resolve exit IP country names/codes with a local JSON cache."""

    DATA_DIR = PROJECT_ROOT / "data"
    CACHE_FILE = DATA_DIR / "geo_cache.json"
    LOOKUP_URL = "http://ip-api.com/json/{ip}"
    TIMEOUT_SECONDS = 5

    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: Dict[str, Dict[str, str]] = {}
        self._ensure_data_dir()
        self._load_cache()

    def _ensure_data_dir(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> None:
        if not self.CACHE_FILE.exists():
            self._cache = {}
            return
        try:
            payload = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load geo cache from %s: %s", self.CACHE_FILE, exc)
            self._cache = {}
            return
        if isinstance(payload, dict):
            self._cache = {
                str(ip): {
                    "country": str(item.get("country") or "").strip(),
                    "country_code": str(item.get("country_code") or "").strip().upper(),
                }
                for ip, item in payload.items()
                if isinstance(item, dict)
            }
        else:
            self._cache = {}

    def _save_cache(self) -> None:
        self.CACHE_FILE.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def normalize_ip(ip: str) -> str:
        try:
            return str(ipaddress.ip_address(str(ip).strip()))
        except ValueError as exc:
            raise ValueError("Invalid IP address") from exc

    @staticmethod
    def _normalize_result(country: Optional[str], country_code: Optional[str]) -> Optional[Dict[str, str]]:
        normalized_country = str(country or "").strip()
        normalized_code = str(country_code or "").strip().upper()
        if not normalized_country and not normalized_code:
            return None
        return {
            "country": normalized_country or normalized_code,
            "country_code": normalized_code or "",
        }

    def get_cached_region(self, ip: str) -> Optional[Dict[str, str]]:
        normalized_ip = self.normalize_ip(ip)
        with self._lock:
            item = self._cache.get(normalized_ip)
            return dict(item) if item else None

    def _get_known_region(self, ip: str) -> Optional[Dict[str, str]]:
        normalized_ip = self.normalize_ip(ip)
        candidate_files = (
            self.DATA_DIR / "active_proxies.json",
            self.DATA_DIR / "subscriptions.json",
            self.DATA_DIR / "custom_groups.json",
        )
        for path in candidate_files:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            stack = [payload]
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    exit_ip = str(current.get("exit_ip") or "").strip()
                    if exit_ip == normalized_ip:
                        normalized = self._normalize_result(
                            current.get("exit_country"),
                            current.get("exit_country_code"),
                        )
                        if normalized:
                            return normalized
                    stack.extend(current.values())
                elif isinstance(current, list):
                    stack.extend(current)
        return None

    def remember_region(
        self,
        ip: Optional[str],
        country: Optional[str],
        country_code: Optional[str],
    ) -> Optional[Dict[str, str]]:
        if not ip:
            return None
        normalized_ip = self.normalize_ip(ip)
        normalized = self._normalize_result(country, country_code)
        if normalized is None:
            return None
        with self._lock:
            self._cache[normalized_ip] = normalized
            self._save_cache()
            return dict(normalized)

    def lookup_ip(self, ip: str) -> Dict[str, str]:
        normalized_ip = self.normalize_ip(ip)

        cached = self.get_cached_region(normalized_ip)
        if cached:
            return {
                "ip": normalized_ip,
                "country": cached.get("country", ""),
                "country_code": cached.get("country_code", ""),
            }

        known = self._get_known_region(normalized_ip)
        if known:
            self.remember_region(normalized_ip, known["country"], known["country_code"])
            return {
                "ip": normalized_ip,
                "country": known["country"],
                "country_code": known["country_code"],
            }

        try:
            response = requests.get(
                self.LOOKUP_URL.format(ip=normalized_ip),
                timeout=self.TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:  # pragma: no cover - network defensive
            raise GeoLookupError(f"Geo lookup failed for {normalized_ip}: {exc}") from exc
        except ValueError as exc:  # pragma: no cover - defensive
            raise GeoLookupError(f"Geo lookup returned invalid JSON for {normalized_ip}") from exc

        country = data.get("country") or data.get("country_name")
        country_code = data.get("countryCode") or data.get("country_code")
        normalized = self._normalize_result(country, country_code)
        if normalized is None:
            raise GeoLookupError(f"No geo information found for {normalized_ip}")
        self.remember_region(normalized_ip, normalized["country"], normalized["country_code"])
        return {
            "ip": normalized_ip,
            "country": normalized["country"],
            "country_code": normalized["country_code"],
        }


_geo_service: Optional[GeoService] = None


def get_geo_service() -> GeoService:
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoService()
    return _geo_service
