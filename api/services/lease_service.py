"""
Lease management service.
Manages proxy lease acquisition, release, and cooldown with workspace isolation.
"""
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from api.services.health_service import get_health_service

# Configurable logging - disabled by default
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Default: only warnings and errors

GLOBAL_WORKSPACE_ID = "__global__"

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
    """Tracks usage statistics for a proxy port."""
    last_used_at: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class LeaseResult:
    """Result of a lease acquisition attempt."""
    success: bool
    lease_id: Optional[str] = None
    proxy_port: Optional[int] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
    message: Optional[str] = None


class LeaseManager:
    """
    Manages proxy leases with workspace isolation.
    
    Features:
    - Workspace isolation: different workspaces can use the same proxy
    - TTL-based leases: automatic expiration to prevent deadlocks
    - Client-specified cooldown: caller controls rest period after release
    - LRU selection: least recently used proxy is selected first
    - Thread-safe: uses threading.Lock for concurrent access
    """
    
    def __init__(self):
        # workspace_id:port -> LeaseRecord
        self._active_leases: Dict[str, LeaseRecord] = {}
        # workspace_id:port -> CooldownRecord
        self._cooldowns: Dict[str, CooldownRecord] = {}
        # port -> UsageRecord (global, not per-workspace)
        self._usage_stats: Dict[int, UsageRecord] = {}
        # Thread safety
        self._lock = threading.Lock()
        
        logger.debug("LeaseManager initialized")
    
    def _make_key(self, workspace_id: str, port: int) -> str:
        """Create a composite key for workspace:port."""
        return f"{workspace_id}:{port}"

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
    
    def _select_lru_port(self, ports: List[int]) -> Optional[int]:
        """
        Select the least recently used port from the list.
        
        Ports that have never been used are prioritized (treated as oldest).
        """
        if not ports:
            return None
        
        # Sort by last_used_at (None = never used = oldest)
        def sort_key(port):
            usage = self._usage_stats.get(port)
            if usage is None or usage.last_used_at is None:
                return datetime.min  # Never used = highest priority
            return usage.last_used_at
        
        sorted_ports = sorted(ports, key=sort_key)
        selected = sorted_ports[0]
        logger.debug(f"LRU selected port: {selected}")
        return selected
    
    def _update_usage(self, port: int):
        """Update usage statistics for a port."""
        if port not in self._usage_stats:
            self._usage_stats[port] = UsageRecord()
        
        self._usage_stats[port].last_used_at = datetime.now()
        self._usage_stats[port].usage_count += 1
    
    def acquire(self, workspace_id: str, ttl: int = 30) -> LeaseResult:
        """
        Acquire a proxy lease for the given workspace.
        
        Args:
            workspace_id: Workspace identifier for isolation
            ttl: Time-to-live in seconds (default: 30)
        
        Returns:
            LeaseResult with lease details or error
        """
        with self._lock:
            # 1. Cleanup expired leases and cooldowns
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()
            
            # 2. Get available ports for this workspace
            available_ports = self._get_available_ports(workspace_id)
            
            if not available_ports:
                logger.warning(f"No available proxy for workspace: {workspace_id}")
                return LeaseResult(
                    success=False,
                    error="no_available_proxy",
                    message="所有代理均被占用或冷却中"
                )
            
            # 3. Select LRU port
            port = self._select_lru_port(available_ports)
            if port is None:
                return LeaseResult(
                    success=False,
                    error="no_available_proxy",
                    message="无法选择代理端口"
                )
            
            # 4. Create lease
            now = datetime.now()
            lease_id = str(uuid.uuid4())
            expires_at = now + timedelta(seconds=ttl)
            
            lease = LeaseRecord(
                lease_id=lease_id,
                workspace_id=workspace_id,
                proxy_port=port,
                acquired_at=now,
                expires_at=expires_at
            )
            
            key = self._make_key(workspace_id, port)
            self._active_leases[key] = lease
            
            # 5. Update usage stats
            self._update_usage(port)
            
            logger.info(f"Lease acquired: {workspace_id} -> port {port}, ttl={ttl}s")
            
            return LeaseResult(
                success=True,
                lease_id=lease_id,
                proxy_port=port,
                expires_at=expires_at
            )
    
    def release(
        self, 
        workspace_id: str, 
        proxy_address: str, 
        cooldown_seconds: int = 0
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
        # Parse port from address
        try:
            port = int(proxy_address.split(":")[-1])
        except (ValueError, IndexError):
            logger.error(f"Invalid proxy_address format: {proxy_address}")
            return False, None
        
        with self._lock:
            key = self._make_key(workspace_id, port)
            
            # 1. Remove lease (if exists)
            if key in self._active_leases:
                del self._active_leases[key]
                logger.debug(f"Lease released: {key}")
            else:
                logger.debug(f"Lease not found (idempotent release): {key}")
            
            # 2. Set cooldown (if specified)
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
                logger.debug(f"Cooldown set: {key} until {cooldown_until}")
            
            # 3. Update usage timestamp
            self._update_usage(port)
            
            logger.info(
                f"Lease released: {workspace_id} -> port {port}, "
                f"cooldown={cooldown_seconds}s"
            )
            
            return True, cooldown_until

    def set_manual_cooldown(self, workspace_id: str, proxy_port: int) -> tuple[bool, Optional[str]]:
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
            logger.info(f"Manual cooldown set: {workspace_id} -> port {proxy_port}")
            return True, None

    def set_timed_cooldown(
        self,
        workspace_id: str,
        proxy_port: int,
        cooldown_seconds: int,
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
            logger.info(
                "Timed cooldown set: %s -> port %s, cooldown=%ss",
                workspace_id,
                proxy_port,
                cooldown_seconds,
            )
            return True, None

    def set_timed_cooldowns(
        self,
        workspace_id: str,
        proxy_ports: List[int],
        cooldown_seconds: int,
    ) -> dict:
        """Apply timed cooldowns for multiple ports in one workspace-scoped action."""
        applied_ports: List[int] = []
        skipped_ports: List[int] = []
        for proxy_port in proxy_ports:
            success, _ = self.set_timed_cooldown(workspace_id, proxy_port, cooldown_seconds)
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

    def reset_workspace(self, workspace_id: str) -> dict:
        """Clear all active leases and cooldowns for the given workspace."""
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

            released_ports = [self._active_leases[key].proxy_port for key in lease_keys]
            for key in lease_keys:
                del self._active_leases[key]

            for key in cooldown_keys:
                del self._cooldowns[key]

            for port in released_ports:
                self._update_usage(port)

            logger.info(
                "Workspace reset: %s, released=%s, recalled=%s",
                workspace_id,
                len(lease_keys),
                len(cooldown_keys),
            )
            return {
                "workspace_id": workspace_id,
                "released_count": len(lease_keys),
                "recalled_count": len(cooldown_keys),
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
        
        Returns:
            Status dictionary with active leases and cooldowns
        """
        with self._lock:
            # Cleanup first
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()
            
            # Filter leases
            if workspace_id:
                leases = [
                    lease.to_dict() 
                    for lease in self._active_leases.values()
                    if lease.workspace_id == workspace_id
                ]
                cooldowns = [
                    cd.to_dict()
                    for cd in self._cooldowns.values()
                    if cd.workspace_id in {workspace_id, GLOBAL_WORKSPACE_ID}
                ]
            else:
                leases = [lease.to_dict() for lease in self._active_leases.values()]
                cooldowns = [cd.to_dict() for cd in self._cooldowns.values()]
            
            return {
                "workspace_id": workspace_id,
                "active_leases": leases,
                "cooldowns": cooldowns,
                "total_active": len(leases),
                "total_cooldowns": len(cooldowns),
                "workspaces": self._build_workspace_summaries(),
            }
    
    def get_stats(self) -> dict:
        """
        Get lease statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            # Cleanup first
            self._cleanup_expired_leases()
            self._cleanup_expired_cooldowns()
            
            # Get unique workspaces
            workspaces: Set[str] = set()
            for lease in self._active_leases.values():
                workspaces.add(lease.workspace_id)
            for cd in self._cooldowns.values():
                workspaces.add(cd.workspace_id)
            
            # Get healthy ports count
            healthy_ports = self._get_healthy_ports()
            
            # Build usage list
            proxies_by_usage = []
            for port, usage in sorted(
                self._usage_stats.items(), 
                key=lambda x: x[1].usage_count, 
                reverse=True
            ):
                proxies_by_usage.append({
                    "port": port,
                    "last_used_at": usage.last_used_at.isoformat() if usage.last_used_at else None,
                    "usage_count": usage.usage_count
                })
            
            return {
                "total_available_proxies": len(healthy_ports),
                "total_active_leases": len(self._active_leases),
                "total_cooldowns": len(self._cooldowns),
                "workspaces": sorted(workspaces),
                "proxies_by_usage": proxies_by_usage[:20]  # Top 20
            }


# Singleton instance
_lease_manager: Optional[LeaseManager] = None


def get_lease_manager() -> LeaseManager:
    """Get the singleton lease manager instance."""
    global _lease_manager
    if _lease_manager is None:
        _lease_manager = LeaseManager()
    return _lease_manager
