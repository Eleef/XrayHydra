# -*- coding: utf-8 -*-
"""
Xray-Prism 健康监测层

实时监测代理健康状态，自动剔除不健康节点，支持递进式罚时机制。
"""

import logging
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple

import requests

from .models import ProxyHealthState, HealthStatus
from .proxy_runtime import get_proxy_access_host

logger = logging.getLogger(__name__)
FAILURE_THRESHOLD = 3


# 默认配置
DEFAULT_CONFIG = {
    "enabled": True,
    "check_interval_seconds": 60,
    "test_target": "http://ip-api.com/json",  # 与 Web UI 测试一致
    "test_timeout_seconds": 5,
    "max_workers": 20,
    "network_check_targets": [
        "http://www.baidu.com",
        "http://www.taobao.com",
    ],
    "test_targets_presets": [
        {"name": "IP-API (推荐)", "url": "http://ip-api.com/json"},
        {"name": "HTTPBin", "url": "https://httpbin.org/ip"},
        {"name": "百度 (国内)", "url": "http://www.baidu.com"},
        {"name": "Google (国外)", "url": "http://www.google.com"},
    ],
    # 罚时等级（分钟）
    "penalty_levels_minutes": [5, 30, 150],
}


class HealthMonitor:
    """代理健康监测器"""
    
    def __init__(
        self,
        test_target: str = DEFAULT_CONFIG["test_target"],
        timeout: int = DEFAULT_CONFIG["test_timeout_seconds"],
        max_workers: int = DEFAULT_CONFIG["max_workers"],
        penalty_levels: List[int] = None,
        listen_address: Optional[str] = None,
    ):
        """
        初始化健康监测器
        
        Args:
            test_target: 测试目标 URL
            timeout: 请求超时时间（秒）
            max_workers: 最大并发线程数
            penalty_levels: 罚时等级列表（分钟），如 [5, 30, 150]
            listen_address: 代理监听地址
        """
        self.test_target = test_target
        self.timeout = timeout
        self.max_workers = max_workers
        self.listen_address = listen_address or get_proxy_access_host()
        
        # 默认罚时等级（分钟）
        if penalty_levels is None:
            penalty_levels = DEFAULT_CONFIG["penalty_levels_minutes"]
        self.penalty_levels = [level * 60 for level in penalty_levels]  # 转换为秒
        
        # 健康状态字典 {port: ProxyHealthState}
        self._health_states: Dict[int, ProxyHealthState] = {}
        
        # 网络检测目标
        self.network_check_targets = DEFAULT_CONFIG["network_check_targets"]
    
    def check_network_connectivity(self) -> bool:
        """
        检测本机网络连通性
        
        通过直接请求（不走代理）检测是否可以访问互联网。
        如果网络不通，则不应该将代理标记为失败。
        
        Returns:
            bool: True 表示网络正常，False 表示网络中断
        """
        for target in self.network_check_targets:
            try:
                response = requests.get(
                    target,
                    timeout=5,
                    proxies={"http": None, "https": None},  # 不使用代理
                )
                if response.status_code < 500:
                    return True
            except Exception as e:
                logger.debug(f"网络检测失败 ({target}): {e}")
                continue
        
        logger.warning("本机网络连接中断，跳过健康检测")
        return False
    
    def probe_proxy(
        self,
        port: int,
        proxy_type: str = "http"
    ) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """
        探测单个代理的连通性
        
        Args:
            port: 本地代理端口
            proxy_type: 代理类型 (http/socks5)
            
        Returns:
            Tuple[bool, Optional[float], Optional[str], Optional[str]]:
                (是否成功, 延迟ms, 错误信息, 错误分类)
        """
        if not self._is_local_proxy_available(port):
            return False, None, "本地代理端口未监听", "runtime_unavailable"

        proxy_url = f"{proxy_type}://{self.listen_address}:{port}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
        
        start_time = time.time()
        
        try:
            response = requests.get(
                self.test_target,
                proxies=proxies,
                timeout=self.timeout,
                allow_redirects=True,
            )
            
            # 只要能建立连接就算成功（HTTP 状态码 < 500）
            if response.status_code < 500:
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), None, None
            else:
                return False, None, f"HTTP {response.status_code}", "probe_failed"
                
        except requests.exceptions.Timeout:
            return False, None, "请求超时", "probe_failed"
        except requests.exceptions.ProxyError:
            return False, None, "代理错误", "runtime_unavailable"
        except requests.exceptions.ConnectionError as e:
            error_text = str(e).lower()
            if any(keyword in error_text for keyword in ("refused", "proxy", "failed to establish a new connection", "actively refused")):
                return False, None, "连接错误", "runtime_unavailable"
            return False, None, "连接错误", "probe_failed"
        except Exception as e:
            return False, None, f"未知错误: {str(e)[:30]}", "probe_failed"

    def _is_local_proxy_available(self, port: int) -> bool:
        """Check whether the local proxy port is actually listening."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                return sock.connect_ex((self.listen_address, port)) == 0
            except OSError:
                return False
    
    def get_or_create_state(self, port: int) -> ProxyHealthState:
        """获取或创建代理的健康状态"""
        if port not in self._health_states:
            self._health_states[port] = ProxyHealthState(proxy_port=port)
        return self._health_states[port]
    
    def calculate_penalty_duration(self, penalty_level: int) -> int:
        """
        计算罚时时长（秒）
        
        Args:
            penalty_level: 罚时等级 (0-based)
            
        Returns:
            int: 罚时时长（秒）
        """
        if penalty_level < 0:
            return 0
        if penalty_level >= len(self.penalty_levels):
            return self.penalty_levels[-1]
        return self.penalty_levels[penalty_level]
    
    def handle_probe_success(self, port: int, latency_ms: float) -> None:
        """
        处理探测成功
        
        成功后重置失败计数，但保留降级状态一段时间以便观察。
        
        Args:
            port: 代理端口
            latency_ms: 延迟毫秒
        """
        state = self.get_or_create_state(port)
        now = datetime.now()
        
        state.last_check = now
        state.last_success = now
        state.last_latency_ms = latency_ms
        state.failure_count = 0
        state.last_error_category = None
        state.last_error_message = None
        
        # 如果之前是禁用状态，恢复为降级状态（需要观察）
        if state.status == HealthStatus.DISABLED:
            state.status = HealthStatus.DEGRADED
            state.penalty_until = None
            logger.info(f"代理 :{port} 从禁用恢复为降级状态")
        elif state.status == HealthStatus.DEGRADED:
            # 降级状态下连续成功3次后恢复为健康
            # 这里简化处理：直接恢复
            state.status = HealthStatus.HEALTHY
            state.penalty_level = 0
            logger.debug(f"代理 :{port} 恢复为健康状态")
        
        logger.debug(f"代理 :{port} 探测成功 ({latency_ms:.0f}ms)")
    
    def handle_probe_failure(self, port: int, error: str, error_category: str = "probe_failed") -> None:
        """
        处理探测失败
        
        累加失败次数，达到阈值后进入罚时禁用状态。
        
        Args:
            port: 代理端口
            error: 错误信息
        """
        state = self.get_or_create_state(port)
        now = datetime.now()
        
        state.last_check = now
        state.failure_count += 1
        state.last_error_category = error_category
        state.last_error_message = error

        # 连续失败达到阈值后才触发罚时禁用
        if state.failure_count >= FAILURE_THRESHOLD and state.status != HealthStatus.DISABLED:
            # 提升罚时等级
            state.penalty_level = min(
                state.penalty_level + 1,
                len(self.penalty_levels)
            )
            
            # 计算罚时结束时间
            penalty_seconds = self.calculate_penalty_duration(
                state.penalty_level - 1
            )
            state.penalty_until = now + timedelta(seconds=penalty_seconds)
            state.status = HealthStatus.DISABLED
            
            logger.warning(
                f"代理 :{port} 进入禁用状态 "
                f"(等级 {state.penalty_level}, 罚时 {penalty_seconds // 60} 分钟, 原因 {error_category}: {error})"
            )
        else:
            logger.debug(
                "代理 :%s 探测失败 (%s/%s): %s",
                port,
                state.failure_count,
                FAILURE_THRESHOLD,
                error,
            )
    
    def check_penalty_expiry(self) -> None:
        """
        检查罚时到期的代理，恢复为降级状态
        """
        now = datetime.now()
        
        for port, state in self._health_states.items():
            if (state.status == HealthStatus.DISABLED and 
                state.penalty_until and 
                now >= state.penalty_until):
                state.status = HealthStatus.DEGRADED
                state.penalty_until = None
                logger.info(f"代理 :{port} 罚时结束，恢复为降级状态")
    
    def run_health_check(
        self,
        ports: List[int],
        proxy_type: str = "http",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[int, ProxyHealthState]:
        """
        执行一轮健康检测
        
        Args:
            ports: 要检测的代理端口列表
            proxy_type: 代理类型
            progress_callback: 进度回调函数 (completed, total)
            
        Returns:
            Dict[int, ProxyHealthState]: 检测结果
        """
        # 1. 检查罚时到期
        self.check_penalty_expiry()
        
        # 2. 过滤出需要检测的端口（非禁用状态或罚时已过）
        ports_to_check = []
        for port in ports:
            state = self.get_or_create_state(port)
            if state.status != HealthStatus.DISABLED:
                ports_to_check.append(port)

        # 当所有端口都被标记为 disabled 时，允许做一轮恢复探测。
        # 否则系统会进入“全部禁用 -> 永不再探测 -> 永不恢复”的死锁。
        if not ports_to_check and ports:
            ports_to_check = list(ports)
            logger.warning("所有代理当前均为 disabled，执行恢复探测")

        if not ports_to_check:
            logger.debug("没有需要检测的代理")
            return self._health_states
        
        # 3. 检查本机网络
        if not self.check_network_connectivity():
            logger.warning("网络中断，跳过本轮健康检测")
            return self._health_states
        
        # 4. 并发探测
        logger.info(f"开始健康检测: {len(ports_to_check)} 个代理")
        completed = 0
        total = len(ports_to_check)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_port = {
                executor.submit(self.probe_proxy, port, proxy_type): port
                for port in ports_to_check
            }
            
            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    result = future.result()
                    if len(result) == 4:
                        success, latency_ms, error, error_category = result
                    else:
                        success, latency_ms, error = result
                        error_category = "probe_failed"
                    
                    if success:
                        self.handle_probe_success(port, latency_ms)
                    else:
                        self.handle_probe_failure(port, error, error_category)
                        
                except Exception as e:
                    self.handle_probe_failure(port, str(e), "probe_failed")
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
        
        # 统计结果
        healthy = sum(1 for s in self._health_states.values() 
                     if s.status == HealthStatus.HEALTHY)
        degraded = sum(1 for s in self._health_states.values() 
                      if s.status == HealthStatus.DEGRADED)
        disabled = sum(1 for s in self._health_states.values() 
                      if s.status == HealthStatus.DISABLED)
        
        logger.info(
            f"健康检测完成: {healthy} 健康, {degraded} 降级, {disabled} 禁用"
        )
        
        return self._health_states
    
    def get_all_states(self) -> Dict[int, ProxyHealthState]:
        """获取所有健康状态"""
        return self._health_states.copy()
    
    def get_state(self, port: int) -> Optional[ProxyHealthState]:
        """获取指定端口的健康状态"""
        return self._health_states.get(port)
    
    def get_healthy_ports(self) -> List[int]:
        """获取所有健康状态的端口列表（不包括禁用）"""
        return [
            port for port, state in self._health_states.items()
            if state.status != HealthStatus.DISABLED
        ]
    
    def reset_state(self, port: int) -> bool:
        """
        重置指定端口的健康状态
        
        Args:
            port: 代理端口
            
        Returns:
            bool: 是否成功重置
        """
        if port in self._health_states:
            self._health_states[port] = ProxyHealthState(proxy_port=port)
            logger.info(f"代理 :{port} 状态已重置")
            return True
        return False
    
    def reset_all_states(self) -> int:
        """
        重置所有健康状态
        
        Returns:
            int: 重置的代理数量
        """
        count = len(self._health_states)
        for port in list(self._health_states.keys()):
            self._health_states[port] = ProxyHealthState(proxy_port=port)
        logger.info(f"已重置 {count} 个代理的状态")
        return count
    
    def remove_state(self, port: int) -> bool:
        """移除指定端口的健康状态"""
        if port in self._health_states:
            del self._health_states[port]
            return True
        return False
    
    def load_states(self, states_data: List[Dict]) -> None:
        """从字典列表加载健康状态"""
        self._health_states.clear()
        for data in states_data:
            try:
                state = ProxyHealthState.from_dict(data)
                self._health_states[state.proxy_port] = state
            except Exception as e:
                logger.warning(f"加载健康状态失败: {e}")
    
    def export_states(self) -> List[Dict]:
        """导出健康状态为字典列表"""
        return [state.to_dict() for state in self._health_states.values()]
