"""
Health monitoring service.
Manages proxy health checking, state persistence, and background monitoring.
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.xray_prism.health_monitor import HealthMonitor, DEFAULT_CONFIG
from src.xray_prism.models import HealthStatus, ProxyHealthState

logger = logging.getLogger(__name__)


class HealthService:
    """Service for managing proxy health monitoring."""
    
    DATA_DIR = PROJECT_ROOT / "data"
    CONFIG_FILE = DATA_DIR / "health_config.json"
    STATE_FILE = DATA_DIR / "health_state.json"
    
    def __init__(self):
        """Initialize the health service."""
        self._ensure_data_dir()
        self._config = self._load_config()
        self._monitor = self._create_monitor()
        self._load_states()
        
        # Background monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # Merge with defaults
                    config = DEFAULT_CONFIG.copy()
                    config.update(saved_config)
                    return config
            except Exception as e:
                logger.warning(f"Failed to load health config: {e}")
        return DEFAULT_CONFIG.copy()
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health config: {e}")
    
    def _create_monitor(self) -> HealthMonitor:
        """Create a HealthMonitor instance with current config."""
        return HealthMonitor(
            test_target=self._config.get("test_target", DEFAULT_CONFIG["test_target"]),
            timeout=self._config.get("test_timeout_seconds", DEFAULT_CONFIG["test_timeout_seconds"]),
            max_workers=self._config.get("max_workers", DEFAULT_CONFIG["max_workers"]),
            penalty_levels=self._config.get("penalty_levels_minutes", DEFAULT_CONFIG["penalty_levels_minutes"]),
        )
    
    def _load_states(self) -> None:
        """Load health states from file."""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    states_data = json.load(f)
                    self._monitor.load_states(states_data)
                    logger.info(f"Loaded {len(states_data)} health states")
            except Exception as e:
                logger.warning(f"Failed to load health states: {e}")
    
    def _save_states(self) -> None:
        """Save health states to file."""
        try:
            states_data = self._monitor.export_states()
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(states_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health states: {e}")
    
    # ==================== Configuration ====================
    
    def get_config(self) -> Dict[str, Any]:
        """Get current health monitoring configuration."""
        return {
            "enabled": self._config.get("enabled", True),
            "check_interval_seconds": self._config.get("check_interval_seconds", 60),
            "test_target": self._config.get("test_target", DEFAULT_CONFIG["test_target"]),
            "test_timeout_seconds": self._config.get("test_timeout_seconds", 5),
            "test_targets_presets": self._config.get("test_targets_presets", DEFAULT_CONFIG["test_targets_presets"]),
            "penalty_levels_minutes": self._config.get("penalty_levels_minutes", DEFAULT_CONFIG["penalty_levels_minutes"]),
            "is_monitoring": self._is_running,
        }
    
    def update_config(
        self,
        enabled: Optional[bool] = None,
        check_interval_seconds: Optional[int] = None,
        test_target: Optional[str] = None,
        test_timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update health monitoring configuration.
        
        Returns:
            Updated configuration
        """
        if enabled is not None:
            self._config["enabled"] = enabled
        if check_interval_seconds is not None:
            self._config["check_interval_seconds"] = max(10, check_interval_seconds)
        if test_target is not None:
            self._config["test_target"] = test_target
            self._monitor.test_target = test_target
        if test_timeout_seconds is not None:
            self._config["test_timeout_seconds"] = max(1, min(30, test_timeout_seconds))
            self._monitor.timeout = self._config["test_timeout_seconds"]
        
        self._save_config()
        
        # Restart monitoring if config changed
        if self._is_running:
            self.stop_monitoring()
            if self._config.get("enabled", True):
                self.start_monitoring()
        
        return self.get_config()
    
    # ==================== Health States ====================
    
    def get_all_health_states(self) -> List[Dict[str, Any]]:
        """Get health states for all monitored proxies."""
        states = self._monitor.get_all_states()
        result = []
        now = datetime.now()
        
        for port, state in states.items():
            state_dict = state.to_dict()
            
            # Calculate remaining penalty time
            if state.penalty_until and state.status == HealthStatus.DISABLED:
                remaining = (state.penalty_until - now).total_seconds()
                state_dict["penalty_remaining_seconds"] = max(0, int(remaining))
            else:
                state_dict["penalty_remaining_seconds"] = None
            
            result.append(state_dict)
        
        return sorted(result, key=lambda x: x["proxy_port"])
    
    def get_health_state(self, port: int) -> Optional[Dict[str, Any]]:
        """Get health state for a specific proxy."""
        state = self._monitor.get_state(port)
        if not state:
            return None
        
        state_dict = state.to_dict()
        
        # Calculate remaining penalty time
        now = datetime.now()
        if state.penalty_until and state.status == HealthStatus.DISABLED:
            remaining = (state.penalty_until - now).total_seconds()
            state_dict["penalty_remaining_seconds"] = max(0, int(remaining))
        else:
            state_dict["penalty_remaining_seconds"] = None
        
        return state_dict
    
    def reset_proxy_health(self, port: int) -> bool:
        """Reset health state for a specific proxy."""
        result = self._monitor.reset_state(port)
        if result:
            self._save_states()
        return result
    
    def reset_all_health(self) -> int:
        """Reset health states for all proxies."""
        count = self._monitor.reset_all_states()
        self._save_states()
        return count
    
    def sync_with_proxies(self, active_ports: List[int]) -> None:
        """
        Synchronize health states with active proxy list.
        
        Removes states for proxies that no longer exist,
        and creates states for new proxies.
        """
        current_ports = set(self._monitor.get_all_states().keys())
        active_ports_set = set(active_ports)
        
        # Remove states for removed proxies
        for port in current_ports - active_ports_set:
            self._monitor.remove_state(port)
        
        # Create states for new proxies
        for port in active_ports_set - current_ports:
            self._monitor.get_or_create_state(port)
        
        self._save_states()
    
    # ==================== Health Check ====================
    
    def run_health_check(
        self,
        ports: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run a health check on specified ports.
        
        Args:
            ports: List of ports to check. If None, checks all known ports.
            
        Returns:
            List of health state dictionaries
        """
        if ports is None:
            ports = list(self._monitor.get_all_states().keys())
        
        if not ports:
            return []
        
        self._monitor.run_health_check(ports)
        self._save_states()
        
        return self.get_all_health_states()
    
    # ==================== Background Monitoring ====================
    
    def _monitoring_loop(self, get_ports_callback) -> None:
        """Background monitoring loop."""
        logger.info("Health monitoring started")
        
        while not self._stop_event.is_set():
            if self._config.get("enabled", True):
                try:
                    # Get current active ports
                    ports = get_ports_callback()
                    if ports:
                        self._monitor.run_health_check(ports)
                        self._save_states()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
            
            # Wait for the configured interval
            interval = self._config.get("check_interval_seconds", 60)
            self._stop_event.wait(interval)
        
        logger.info("Health monitoring stopped")
    
    def start_monitoring(self, get_ports_callback=None) -> bool:
        """
        Start background health monitoring.
        
        Args:
            get_ports_callback: Callback function that returns list of active ports
            
        Returns:
            bool: True if started, False if already running
        """
        if self._is_running:
            return False
        
        if get_ports_callback is None:
            # Default: check all known ports
            get_ports_callback = lambda: list(self._monitor.get_all_states().keys())
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(get_ports_callback,),
            daemon=True,
            name="HealthMonitor"
        )
        self._monitor_thread.start()
        self._is_running = True
        
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Stop background health monitoring.
        
        Returns:
            bool: True if stopped, False if not running
        """
        if not self._is_running:
            return False
        
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self._is_running = False
        
        return True
    
    def is_monitoring(self) -> bool:
        """Check if background monitoring is running."""
        return self._is_running


# Singleton instance
_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """Get the singleton health service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
