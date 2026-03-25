"""
Lease management service.
Manages proxy lease acquisition, release, cooldown, and workspace-scoped metrics.
"""
from __future__ import annotations

import atexit
import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from api.services.health_service import get_health_service

# Configurable logging - disabled by default
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Default: only warnings and errors

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LEASE_METRICS_PATH = ROOT_DIR / "data" / "lease_metrics.json"
DEFAULT_METRICS_FLUSH_DELAY_SECONDS = 2.0
DEFAULT_METRICS_MAX_FLUSH_INTERVAL_SECONDS = 10.0

GLOBAL_WORKSPACE_ID = "__global__"
INITIAL_PORT_ORDER_RANDOM = "random"
INITIAL_PORT_ORDER_ASC = "port_asc"
LEASE_RESULT_SUCCESS = "success"
LEASE_RESULT_FAILURE = "failure"

def enable_lease_debug_logging():
    """Enable debug logging for lease operations."""
    logger.setLevel(logging.DEBUG)

def disable_lease_debug_logging():
    """Disable debug logging for lease operations."""
    logger.setLevel(logging.WARNING)


@dataclass
class LeaseRecord:
    """Represents an active lease."""
    lease_id: str
    workspace_id: str
    proxy_port: int
    acquired_at: datetime
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "lease_id": self.lease_id,
            "workspace_id": self.workspace_id,
            "proxy_port": self.proxy_port,
            "proxy_address": f"127.0.0.1:{self.proxy_port}",
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }


@dataclass
class CooldownRecord:
    """Represents a cooldown period."""
    workspace_id: str
    proxy_port: int
    until: Optional[datetime]
    set_at: datetime
    source: str = "timed"
    
    def is_expired(self) -> bool:
        if self.until is None:
            return False
        return datetime.now() > self.until
    
    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "proxy_port": self.proxy_port,
            "until": self.until.isoformat() if self.until else None,
            "set_at": self.set_at.isoformat(),
            "source": self.source,
        }


@dataclass
class UsageRecord:
    """Tracks usage and outcome statistics for a workspace-scoped proxy port."""

    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @classmethod
    def from_dict(cls, payload: dict) -> "UsageRecord":
        last_used_at = None
        last_used_raw = payload.get("last_used_at")
        if isinstance(last_used_raw, str) and last_used_raw:
            try:
                last_used_at = datetime.fromisoformat(last_used_raw)
            except ValueError:
                logger.warning("Ignoring invalid lease metric timestamp: %s", last_used_raw)
        return cls(
            last_used_at=last_used_at,
            usage_count=int(payload.get("usage_count", 0) or 0),
            success_count=int(payload.get("success_count", 0) or 0),
            failure_count=int(payload.get("failure_count", 0) or 0),
        )

    def to_dict(self) -> dict:
        return {
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

    def snapshot(self) -> dict:
        return self.to_dict()


@dataclass
class LeaseResult:
    """Result of a lease acquisition attempt."""
    success: bool
    lease_id: Optional[str] = None
    proxy_port: Optional[int] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
    message: Optional[str] = None
    metrics: Optional[dict] = None


class LeaseManager:
    """
    Manages proxy leases with workspace isolation.
    
    Features:
    - Workspace isolation: different workspaces can use the same proxy
    - TTL-based leases: automatic expiration to prevent deadlocks
    - Client-specified cooldown: caller controls rest period after release
    - LRU selection: least recently used proxy is selected first within a workspace
    - Optional lazy JSON persistence for workspace+port metrics
    - Thread-safe: uses threading.Lock for concurrent access
    """

    def __init__(
        self,
        metrics_path: Optional[Path | str] = None,
        flush_delay_seconds: float = DEFAULT_METRICS_FLUSH_DELAY_SECONDS,
        max_flush_interval_seconds: float = DEFAULT_METRICS_MAX_FLUSH_INTERVAL_SECONDS,
    ):
        # workspace_id:port -> LeaseRecord
        self._active_leases: Dict[str, LeaseRecord] = {}
        # workspace_id:port -> CooldownRecord
        self._cooldowns: Dict[str, CooldownRecord] = {}
        # workspace_id -> port -> UsageRecord
        self._usage_stats: Dict[str, Dict[int, UsageRecord]] = {}
        self._lock = threading.Lock()

        self._metrics_path = Path(metrics_path) if metrics_path else None
        self._flush_delay_seconds = max(0.0, float(flush_delay_seconds))
        self._max_flush_interval_seconds = max(
            self._flush_delay_seconds,
            float(max_flush_interval_seconds),
        )
        self._persist_dirty = False
        self._first_dirty_at_monotonic: Optional[float] = None
        self._flush_timer: Optional[threading.Timer] = None

        self._load_metrics()
        logger.debug("LeaseManager initialized")

    def _make_key(self, workspace_id: str, port: int) -> str:
        """Create a composite key for workspace:port."""
        return f"{workspace_id}:{port}"

    def _cancel_flush_timer_locked(self) -> None:
        timer = self._flush_timer
        self._flush_timer = None
        if timer and timer is not threading.current_thread():
            timer.cancel()

    def _serialize_usage_stats(self) -> dict:
        workspaces = {}
        for workspace_id, ports in self._usage_stats.items():
            if not ports:
                continue
            workspaces[workspace_id] = {
                str(port): usage.to_dict()
                for port, usage in sorted(ports.items())
            }
        return {"workspaces": workspaces}

    def _load_metrics(self) -> None:
        if self._metrics_path is None or not self._metrics_path.exists():
            return

        try:
            payload = json.loads(self._metrics_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("Failed to load lease metrics from %s: %s", self._metrics_path, exc)
            return

        workspaces = payload.get("workspaces", {})
        if not isinstance(workspaces, dict):
            logger.warning("Ignoring malformed lease metrics payload from %s", self._metrics_path)
            return

        usage_stats: Dict[str, Dict[int, UsageRecord]] = {}
        for workspace_id, ports in workspaces.items():
            if not isinstance(workspace_id, str) or not isinstance(ports, dict):
                continue
            workspace_metrics: Dict[int, UsageRecord] = {}
            for port_raw, usage_payload in ports.items():
                try:
                    port = int(port_raw)
                except (TypeError, ValueError):
                    continue
                if not isinstance(usage_payload, dict):
                    continue
                workspace_metrics[port] = UsageRecord.from_dict(usage_payload)
            if workspace_metrics:
                usage_stats[workspace_id] = workspace_metrics

        self._usage_stats = usage_stats

    def _flush_metrics_locked(self) -> None:
        if self._metrics_path is None or not self._persist_dirty:
            return

        self._cancel_flush_timer_locked()
        payload = self._serialize_usage_stats()
        self._metrics_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._metrics_path.with_suffix(f"{self._metrics_path.suffix}.tmp")

        try:
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp_path.replace(self._metrics_path)
            self._persist_dirty = False
            self._first_dirty_at_monotonic = None
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("Failed to persist lease metrics to %s: %s", self._metrics_path, exc)

    def _flush_metrics_from_timer(self) -> None:
        with self._lock:
            self._flush_timer = None
            self._flush_metrics_locked()

    def _schedule_flush_locked(self) -> None:
        if self._metrics_path is None or not self._persist_dirty:
            return

        if self._first_dirty_at_monotonic is None:
            self._first_dirty_at_monotonic = time.monotonic()

        elapsed = time.monotonic() - self._first_dirty_at_monotonic
        if elapsed >= self._max_flush_interval_seconds:
            self._flush_metrics_locked()
            return

        self._cancel_flush_timer_locked()
        delay = min(self._flush_delay_seconds, self._max_flush_interval_seconds - elapsed)
        if delay <= 0:
            self._flush_metrics_locked()
            return

        timer = threading.Timer(delay, self._flush_metrics_from_timer)
        timer.daemon = True
        self._flush_timer = timer
        timer.start()

    def _mark_metrics_dirty_locked(self, immediate: bool = False) -> None:
        if self._metrics_path is None:
            return

        self._persist_dirty = True
        if self._first_dirty_at_monotonic is None:
            self._first_dirty_at_monotonic = time.monotonic()

        if immediate:
            self._flush_metrics_locked()
            return

        self._schedule_flush_locked()

    def flush_metrics(self) -> None:
        """Flush in-memory metrics to disk immediately if persistence is enabled."""
        with self._lock:
            self._flush_metrics_locked()

    def close(self) -> None:
        """Best-effort shutdown flush for metrics persistence."""
        self.flush_metrics()

    def _get_usage_record(
        self,
        workspace_id: str,
        port: int,
        create: bool = False,
    ) -> Optional[UsageRecord]:
        workspace_usage = self._usage_stats.get(workspace_id)
        if workspace_usage is None:
            if not create:
                return None
            workspace_usage = {}
            self._usage_stats[workspace_id] = workspace_usage

        usage = workspace_usage.get(port)
        if usage is None and create:
            usage = UsageRecord()
            workspace_usage[port] = usage
        return usage

    def _get_metrics_snapshot(self, workspace_id: str, port: int) -> dict:
        usage = self._get_usage_record(workspace_id, port, create=False)
        if usage is None:
            return UsageRecord().snapshot()
        return usage.snapshot()

    def _update_usage(self, workspace_id: str, port: int) -> dict:
        usage = self._get_usage_record(workspace_id, port, create=True)
        assert usage is not None
        usage.last_used_at = datetime.now()
        usage.usage_count += 1
        self._mark_metrics_dirty_locked()
        return usage.snapshot()

    def _mark_result(self, workspace_id: str, port: int, result: Optional[str]) -> None:
        if result not in {LEASE_RESULT_SUCCESS, LEASE_RESULT_FAILURE}:
            return
        usage = self._get_usage_record(workspace_id, port, create=True)
        assert usage is not None
        if result == LEASE_RESULT_SUCCESS:
            usage.success_count += 1
        elif result == LEASE_RESULT_FAILURE:
            usage.failure_count += 1
        self._mark_metrics_dirty_locked()

    def _has_active_lease_for_port(self, proxy_port: int) -> bool:
        """Return whether any non-expired lease currently holds the port."""
        return any(
            lease.proxy_port == proxy_port and not lease.is_expired()
            for lease in self._active_leases.values()
        )
    
    def _cleanup_expired_leases(self) -> int:
        """Remove expired leases. Returns count of removed leases."""
        expired_keys = [
            key for key, lease in self._active_leases.items()
            if lease.is_expired()
        ]
        for key in expired_keys:
            del self._active_leases[key]
            logger.debug(f"Cleaned up expired lease: {key}")
        return len(expired_keys)
    
    def _cleanup_expired_cooldowns(self) -> int:
        """Remove expired cooldowns. Returns count of removed cooldowns."""
        expired_keys = [
            key for key, cooldown in self._cooldowns.items()
            if cooldown.is_expired()
        ]
        for key in expired_keys:
            del self._cooldowns[key]
            logger.debug(f"Cleaned up expired cooldown: {key}")
        return len(expired_keys)
    
    def _get_healthy_ports(self) -> List[int]:
        """Get list of healthy proxy ports from HealthService."""
        health_service = get_health_service()
        states = health_service.get_all_health_states()
        
        # Return HEALTHY and DEGRADED ports (not disabled)
        # Degraded ports are recovering from failure, still usable
        available_ports = [
            state["proxy_port"] 
            for state in states 
            if state.get("status") in ("healthy", "degraded")
        ]
        
        logger.debug(f"Found {len(available_ports)} available ports (healthy/degraded)")
        return available_ports

    def _build_no_available_message(self) -> str:
        """Return a more precise lease exhaustion message."""
        health_service = get_health_service()
        states = health_service.get_all_health_states()
        if states and all(state.get("status") == "disabled" for state in states):
            return "当前没有可分配代理：所有代理均处于健康禁用状态"
        return "所有代理均被占用或冷却中"
    
    def _get_available_ports(self, workspace_id: str) -> List[int]:
        """
        Get ports available for the given workspace.
        
        A port is available if:
        1. It is healthy (from HealthService)
        2. It is NOT currently leased by this workspace
        3. It is NOT in cooldown for this workspace
        """
        healthy_ports = self._get_healthy_ports()
        available = []
        
        for port in healthy_ports:
            key = self._make_key(workspace_id, port)
            global_key = self._make_key(GLOBAL_WORKSPACE_ID, port)
            
            # Check if leased by this workspace
            if key in self._active_leases:
                lease = self._active_leases[key]
                if not lease.is_expired():
                    continue  # Skip, still leased
            
            # Check if in cooldown for this workspace
            if key in self._cooldowns:
                cooldown = self._cooldowns[key]
                if not cooldown.is_expired():
                    continue  # Skip, still in cooldown

            if global_key in self._cooldowns:
                cooldown = self._cooldowns[global_key]
                if not cooldown.is_expired():
                    continue  # Skip, globally cooled down
            
            available.append(port)
        
        logger.debug(f"Available ports for {workspace_id}: {len(available)}")
        return available
    
    def _select_lru_port(
        self,
        workspace_id: str,
        ports: List[int],
        initial_port_ordering: str = INITIAL_PORT_ORDER_RANDOM,
    ) -> Optional[int]:
        """
        Select the least recently used port from the list for this workspace.

        Ports that have never been used in the workspace are prioritized.
        """
        if not ports:
            return None

        def sort_key(port: int) -> datetime:
            usage = self._get_usage_record(workspace_id, port, create=False)
            if usage is None or usage.last_used_at is None:
                return datetime.min
            return usage.last_used_at

        usage_by_port = {port: sort_key(port) for port in ports}
        oldest_usage = min(usage_by_port.values())
        candidate_ports = [port for port in ports if usage_by_port[port] == oldest_usage]

        if oldest_usage == datetime.min:
            if initial_port_ordering == INITIAL_PORT_ORDER_ASC:
                selected = min(candidate_ports)
            else:
                selected = random.choice(candidate_ports)
            logger.debug("Initial ordering selected port: %s (%s)", selected, initial_port_ordering)
            return selected

        selected = min(candidate_ports)
        logger.debug(f"LRU selected port: {selected}")
        return selected
    
    def acquire(
        self,
        workspace_id: str,
        ttl: int = 30,
        initial_port_ordering: str = INITIAL_PORT_ORDER_RANDOM,
    ) -> LeaseResult:
        """
        Acquire a proxy lease for the given workspace.
        
        Args:
            workspace_id: Workspace identifier for isolation
            ttl: Time-to-live in seconds (default: 30)
        
        Returns:
            LeaseResult with lease details or error
        """
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            available_ports = self._get_available_ports(workspace_id)
            if not available_ports:
                logger.warning("No available proxy for workspace: %s", workspace_id)
                return LeaseResult(
                    success=False,
                    error="no_available_proxy",
                    message=self._build_no_available_message(),
                )

            port = self._select_lru_port(
                workspace_id,
                available_ports,
                initial_port_ordering=initial_port_ordering,
            )
            if port is None:
                return LeaseResult(
                    success=False,
                    error="no_available_proxy",
                    message="无法选择代理端口",
                )

            now = datetime.now()
            lease_id = str(uuid.uuid4())
            expires_at = now + timedelta(seconds=ttl)
            lease = LeaseRecord(
                lease_id=lease_id,
                workspace_id=workspace_id,
                proxy_port=port,
                acquired_at=now,
                expires_at=expires_at,
            )
            key = self._make_key(workspace_id, port)
            self._active_leases[key] = lease
            metrics = self._update_usage(workspace_id, port)

            logger.info("Lease acquired: %s -> port %s, ttl=%ss", workspace_id, port, ttl)
            return LeaseResult(
                success=True,
                lease_id=lease_id,
                proxy_port=port,
                expires_at=expires_at,
                metrics=metrics,
            )

    def release(
        self,
        workspace_id: str,
        proxy_address: str,
        cooldown_seconds: int = 0,
        result: Optional[str] = None,
    ) -> tuple[bool, Optional[datetime]]:
        """
        Release a proxy lease and optionally set cooldown.
        
        Args:
            workspace_id: Workspace identifier
            proxy_address: Proxy address (e.g., "127.0.0.1:10001")
            cooldown_seconds: Cooldown period in seconds (0 = no cooldown)
        
        Returns:
            Tuple of (success, cooldown_until)
            
        Note: This is idempotent - releasing a non-existent lease returns success.
        """
        try:
            port = int(proxy_address.split(":")[-1])
        except (ValueError, IndexError):
            logger.error("Invalid proxy_address format: %s", proxy_address)
            return False, None

        with self._lock:
            key = self._make_key(workspace_id, port)
            had_active_lease = key in self._active_leases and not self._active_leases[key].is_expired()

            if key in self._active_leases:
                del self._active_leases[key]
                logger.debug("Lease released: %s", key)
            else:
                logger.debug("Lease not found (idempotent release): %s", key)

            cooldown_until = None
            if cooldown_seconds > 0:
                now = datetime.now()
                cooldown_until = now + timedelta(seconds=cooldown_seconds)
                self._cooldowns[key] = CooldownRecord(
                    workspace_id=workspace_id,
                    proxy_port=port,
                    until=cooldown_until,
                    set_at=now,
                    source="timed",
                )
                logger.debug("Cooldown set: %s until %s", key, cooldown_until)

            if had_active_lease:
                self._mark_result(workspace_id, port, result)

            logger.info(
                "Lease released: %s -> port %s, cooldown=%ss, result=%s",
                workspace_id,
                port,
                cooldown_seconds,
                result,
            )
            return True, cooldown_until

    def set_manual_cooldown(
        self,
        workspace_id: str,
        proxy_port: int,
        result: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Create or replace a manual cooldown for the given workspace and port."""
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            key = self._make_key(workspace_id, proxy_port)
            if workspace_id == GLOBAL_WORKSPACE_ID:
                if self._has_active_lease_for_port(proxy_port):
                    return False, "an active lease currently holds this proxy"
            elif key in self._active_leases and not self._active_leases[key].is_expired():
                return False, "workspace currently holds an active lease for this proxy"

            self._cooldowns[key] = CooldownRecord(
                workspace_id=workspace_id,
                proxy_port=proxy_port,
                until=None,
                set_at=datetime.now(),
                source="manual",
            )
            self._mark_result(workspace_id, proxy_port, result)
            logger.info("Manual cooldown set: %s -> port %s, result=%s", workspace_id, proxy_port, result)
            return True, None

    def set_timed_cooldown(
        self,
        workspace_id: str,
        proxy_port: int,
        cooldown_seconds: int,
        result: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Create or replace a timed cooldown for the given workspace and port."""
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            key = self._make_key(workspace_id, proxy_port)
            if workspace_id == GLOBAL_WORKSPACE_ID:
                if self._has_active_lease_for_port(proxy_port):
                    return False, "an active lease currently holds this proxy"
            elif key in self._active_leases and not self._active_leases[key].is_expired():
                return False, "workspace currently holds an active lease for this proxy"

            now = datetime.now()
            self._cooldowns[key] = CooldownRecord(
                workspace_id=workspace_id,
                proxy_port=proxy_port,
                until=now + timedelta(seconds=cooldown_seconds),
                set_at=now,
                source="timed",
            )
            self._mark_result(workspace_id, proxy_port, result)
            logger.info(
                "Timed cooldown set: %s -> port %s, cooldown=%ss, result=%s",
                workspace_id,
                proxy_port,
                cooldown_seconds,
                result,
            )
            return True, None

    def set_timed_cooldowns(
        self,
        workspace_id: str,
        proxy_ports: List[int],
        cooldown_seconds: int,
        result: Optional[str] = None,
    ) -> dict:
        """Apply timed cooldowns for multiple ports in one workspace-scoped action."""
        applied_ports: List[int] = []
        skipped_ports: List[int] = []
        for proxy_port in proxy_ports:
            success, _ = self.set_timed_cooldown(
                workspace_id,
                proxy_port,
                cooldown_seconds,
                result=result,
            )
            if success:
                applied_ports.append(proxy_port)
            else:
                skipped_ports.append(proxy_port)

        return {
            "workspace_id": workspace_id,
            "cooldown_seconds": cooldown_seconds,
            "applied_ports": applied_ports,
            "skipped_ports": skipped_ports,
        }

    def recall_cooldown(self, workspace_id: str, proxy_port: int) -> tuple[bool, Optional[str]]:
        """Remove an existing cooldown for the given workspace and port."""
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            key = self._make_key(workspace_id, proxy_port)
            cooldown = self._cooldowns.pop(key, None)
            source = cooldown.source if cooldown else None
            logger.info(f"Cooldown recalled: {workspace_id} -> port {proxy_port}, source={source}")
            return True, source

    def reset_workspace(self, workspace_id: str, clear_metrics: bool = False) -> dict:
        """Clear all active leases/cooldowns for the given workspace and optionally clear metrics."""
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            lease_keys = [
                key for key, lease in self._active_leases.items()
                if lease.workspace_id == workspace_id
            ]
            cooldown_keys = [
                key for key, cooldown in self._cooldowns.items()
                if cooldown.workspace_id == workspace_id
            ]

            for key in lease_keys:
                del self._active_leases[key]

            for key in cooldown_keys:
                del self._cooldowns[key]

            cleared_metric_entries = 0
            if clear_metrics:
                workspace_usage = self._usage_stats.pop(workspace_id, {})
                cleared_metric_entries = len(workspace_usage)
                if cleared_metric_entries > 0:
                    self._mark_metrics_dirty_locked(immediate=True)

            logger.info(
                "Workspace reset: %s, released=%s, recalled=%s, cleared_metrics=%s",
                workspace_id,
                len(lease_keys),
                len(cooldown_keys),
                cleared_metric_entries,
            )
            return {
                "workspace_id": workspace_id,
                "released_count": len(lease_keys),
                "recalled_count": len(cooldown_keys),
                "cleared_metric_entries": cleared_metric_entries,
            }

    def _build_workspace_summaries(self) -> List[dict]:
        """Summarize active and cooldown state per workspace."""
        workspace_map: Dict[str, dict] = {}

        for lease in self._active_leases.values():
            summary = workspace_map.setdefault(
                lease.workspace_id,
                {
                    "workspace_id": lease.workspace_id,
                    "active_count": 0,
                    "cooldown_count": 0,
                    "last_activity_at": lease.acquired_at,
                },
            )
            summary["active_count"] += 1
            if lease.acquired_at > summary["last_activity_at"]:
                summary["last_activity_at"] = lease.acquired_at

        for cooldown in self._cooldowns.values():
            if cooldown.workspace_id == GLOBAL_WORKSPACE_ID:
                continue
            summary = workspace_map.setdefault(
                cooldown.workspace_id,
                {
                    "workspace_id": cooldown.workspace_id,
                    "active_count": 0,
                    "cooldown_count": 0,
                    "last_activity_at": cooldown.set_at,
                },
            )
            summary["cooldown_count"] += 1
            if cooldown.set_at > summary["last_activity_at"]:
                summary["last_activity_at"] = cooldown.set_at

        summaries = list(workspace_map.values())
        summaries.sort(key=lambda item: (item["last_activity_at"], item["workspace_id"]), reverse=True)
        return [
            {
                **summary,
                "last_activity_at": summary["last_activity_at"].isoformat(),
            }
            for summary in summaries
        ]
    
    def get_status(self, workspace_id: Optional[str] = None) -> dict:
        """
        Get lease and cooldown status.
        
        Args:
            workspace_id: If specified, filter by workspace. Otherwise, return all.
        
        """
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            if workspace_id:
                lease_records = [
                    lease
                    for lease in self._active_leases.values()
                    if lease.workspace_id == workspace_id
                ]
                cooldown_records = [
                    cd
                    for cd in self._cooldowns.values()
                    if cd.workspace_id in {workspace_id, GLOBAL_WORKSPACE_ID}
                ]
            else:
                lease_records = list(self._active_leases.values())
                cooldown_records = list(self._cooldowns.values())

            leases = [
                {
                    **lease.to_dict(),
                    "metrics": self._get_metrics_snapshot(lease.workspace_id, lease.proxy_port),
                }
                for lease in lease_records
            ]
            cooldowns = [
                {
                    **cd.to_dict(),
                    "metrics": self._get_metrics_snapshot(cd.workspace_id, cd.proxy_port),
                }
                for cd in cooldown_records
            ]

            return {
                "workspace_id": workspace_id,
                "active_leases": leases,
                "cooldowns": cooldowns,
                "total_active": len(leases),
                "total_cooldowns": len(cooldowns),
                "workspaces": self._build_workspace_summaries(),
            }
    
    def get_stats(self) -> dict:
        """Get lease statistics."""
        with self._lock:
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()

            workspaces: Set[str] = set(self._usage_stats.keys())
            for lease in self._active_leases.values():
                workspaces.add(lease.workspace_id)
            for cd in self._cooldowns.values():
                workspaces.add(cd.workspace_id)

            healthy_ports = self._get_healthy_ports()

            proxies_by_usage = []
            for workspace_id, usage_by_port in self._usage_stats.items():
                for port, usage in usage_by_port.items():
                    proxies_by_usage.append(
                        {
                            "workspace_id": workspace_id,
                            "port": port,
                            "last_used_at": usage.last_used_at.isoformat() if usage.last_used_at else None,
                            "usage_count": usage.usage_count,
                            "success_count": usage.success_count,
                            "failure_count": usage.failure_count,
                        }
                    )

            proxies_by_usage.sort(
                key=lambda item: (
                    item["usage_count"],
                    item["success_count"],
                    item["failure_count"],
                    item["workspace_id"],
                    -item["port"],
                ),
                reverse=True,
            )

            return {
                "total_available_proxies": len(healthy_ports),
                "total_active_leases": len(self._active_leases),
                "total_cooldowns": len(self._cooldowns),
                "workspaces": sorted(workspaces),
                "proxies_by_usage": proxies_by_usage[:20],
            }


_lease_manager: Optional[LeaseManager] = None


def _flush_lease_manager_at_exit() -> None:
    global _lease_manager
    if _lease_manager is not None:
        _lease_manager.close()


atexit.register(_flush_lease_manager_at_exit)


def get_lease_manager() -> LeaseManager:
    """Get the singleton lease manager instance."""
    global _lease_manager
    if _lease_manager is None:
        _lease_manager = LeaseManager(metrics_path=DEFAULT_LEASE_METRICS_PATH)
    return _lease_manager
