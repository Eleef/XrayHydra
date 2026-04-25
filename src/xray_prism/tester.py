# -*- coding: utf-8 -*-
"""
Xray-Prism 验证测试层

将代理测试拆成两条通道：
1. 连通性/延迟检测：使用轻量 204/小响应端点判断代理是否可用
2. 出口信息检测：在连通性成功后获取出口 IP 和地区信息
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import requests

from api.services.geo_service import GeoLookupError, get_geo_service
from .models import PortMapping, TestResult
from .proxy_runtime import get_proxy_access_host, get_proxy_probe_scheme

logger = logging.getLogger(__name__)

DEFAULT_CONNECTIVITY_TARGETS = [
    "https://www.gstatic.com/generate_204",
    "https://www.google.com/generate_204",
    "http://cp.cloudflare.com/",
]
DEFAULT_EXIT_INFO_TARGETS = [
    "http://ip-api.com/json",
    "https://api.ipify.org?format=json",
    "https://httpbin.org/ip",
]
DEFAULT_IP_API = DEFAULT_EXIT_INFO_TARGETS[0]
BACKUP_IP_APIs = DEFAULT_EXIT_INFO_TARGETS[1:]
MIN_CONNECTIVITY_SUCCESSES = 2


@dataclass
class TargetProbeResult:
    target: str
    success: bool
    latency_ms: Optional[float] = None
    ip: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    error: Optional[str] = None
    category: str = "connectivity"


class ProxyTester:
    """代理连通性测试器"""

    def __init__(
        self,
        timeout: int = 5,
        ip_api: str = DEFAULT_IP_API,
        max_workers: int = 20,
        listen_address: Optional[str] = None,
        connectivity_targets: Optional[List[str]] = None,
        exit_info_targets: Optional[List[str]] = None,
        min_connectivity_successes: int = MIN_CONNECTIVITY_SUCCESSES,
    ):
        self.timeout = timeout
        self.ip_api = ip_api
        self.max_workers = max_workers
        self.listen_address = listen_address or get_proxy_access_host()
        self.connectivity_targets = list(connectivity_targets or DEFAULT_CONNECTIVITY_TARGETS)
        self.exit_info_targets = list(exit_info_targets or [])
        if not self.exit_info_targets:
            self.exit_info_targets = [self.ip_api]
            for target in DEFAULT_EXIT_INFO_TARGETS:
                if target not in self.exit_info_targets:
                    self.exit_info_targets.append(target)
        self.min_connectivity_successes = max(1, min_connectivity_successes)

    @staticmethod
    def _extract_ip_from_body(text: str) -> Optional[str]:
        candidate = (text or "").strip()
        if not candidate:
            return None
        if "," in candidate:
            candidate = candidate.split(",", 1)[0].strip()
        if candidate.count(".") == 3:
            return candidate
        return None

    def _build_proxies(self, port: int, proxy_type: Optional[str]) -> Dict[str, str]:
        normalized_proxy_type = proxy_type or get_proxy_probe_scheme()
        proxy_url = f"{normalized_proxy_type}://{self.listen_address}:{port}"
        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def _run_request(self, target: str, proxies: Dict[str, str]) -> tuple[requests.Response, float]:
        start_time = time.time()
        response = requests.get(
            target,
            proxies=proxies,
            timeout=self.timeout,
            allow_redirects=True,
        )
        latency_ms = (time.time() - start_time) * 1000
        return response, round(latency_ms, 2)

    def _probe_connectivity_target(self, target: str, proxies: Dict[str, str]) -> TargetProbeResult:
        try:
            response, latency_ms = self._run_request(target, proxies)
            body = (response.text or "").strip()
            if response.status_code == 204:
                return TargetProbeResult(target=target, success=True, latency_ms=latency_ms)
            if response.status_code == 200 and len(body) <= 256:
                return TargetProbeResult(target=target, success=True, latency_ms=latency_ms)
            return TargetProbeResult(target=target, success=False, error=f"HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            return TargetProbeResult(target=target, success=False, error="请求超时")
        except requests.exceptions.ProxyError as exc:
            return TargetProbeResult(target=target, success=False, error=f"代理错误: {str(exc)[:50]}")
        except requests.exceptions.ConnectionError as exc:
            return TargetProbeResult(target=target, success=False, error=f"连接错误: {str(exc)[:50]}")
        except Exception as exc:
            return TargetProbeResult(target=target, success=False, error=f"未知错误: {str(exc)[:50]}")

    def _probe_exit_info_target(self, target: str, proxies: Dict[str, str]) -> TargetProbeResult:
        try:
            response, latency_ms = self._run_request(target, proxies)
            response.raise_for_status()
            ip = None
            country = None
            country_code = None
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError):
                data = None

            if isinstance(data, dict):
                ip = data.get("query") or data.get("origin") or data.get("ip")
                if isinstance(ip, str) and "," in ip:
                    ip = ip.split(",", 1)[0].strip()
                country = data.get("country") or data.get("country_name")
                country_code = data.get("countryCode") or data.get("country_code")

            if not ip:
                ip = self._extract_ip_from_body(response.text or "")
            if not ip:
                return TargetProbeResult(target=target, success=False, error="未解析到出口 IP", category="exit_info")

            if ip and (not country or not country_code):
                try:
                    geo_info = get_geo_service().lookup_ip(str(ip))
                    country = country or geo_info.get("country")
                    country_code = country_code or geo_info.get("country_code")
                except (GeoLookupError, ValueError):
                    pass
            elif ip and country_code:
                try:
                    get_geo_service().remember_region(str(ip), country, country_code)
                except ValueError:
                    pass

            return TargetProbeResult(
                target=target,
                success=True,
                latency_ms=latency_ms,
                ip=ip,
                country=country,
                country_code=country_code,
                category="exit_info",
            )
        except requests.exceptions.Timeout:
            return TargetProbeResult(target=target, success=False, error="请求超时", category="exit_info")
        except requests.exceptions.ProxyError as exc:
            return TargetProbeResult(target=target, success=False, error=f"代理错误: {str(exc)[:50]}", category="exit_info")
        except requests.exceptions.ConnectionError as exc:
            return TargetProbeResult(target=target, success=False, error=f"连接错误: {str(exc)[:50]}", category="exit_info")
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "error"
            return TargetProbeResult(target=target, success=False, error=f"HTTP {status_code}", category="exit_info")
        except Exception as exc:
            return TargetProbeResult(target=target, success=False, error=f"未知错误: {str(exc)[:50]}", category="exit_info")

    @staticmethod
    def _summarize_targets(connectivity_results: List[TargetProbeResult], exit_results: List[TargetProbeResult]) -> str:
        connectivity_success = sum(1 for item in connectivity_results if item.success)
        exit_success = sum(1 for item in exit_results if item.success)
        return (
            f"connectivity {connectivity_success}/{len(connectivity_results)}; "
            f"exit-info {exit_success}/{len(exit_results)}"
        )

    def test_port(
        self,
        port: int,
        node_name: str,
        proxy_type: Optional[str] = None,
    ) -> TestResult:
        proxies = self._build_proxies(port, proxy_type)

        connectivity_results = [
            self._probe_connectivity_target(target, proxies)
            for target in self.connectivity_targets
        ]
        successful_connectivity = [item for item in connectivity_results if item.success]
        connectivity_success_count = len(successful_connectivity)
        connectivity_status = "success" if connectivity_success_count >= self.min_connectivity_successes else "failed"

        exit_results: List[TargetProbeResult] = []
        best_exit_info: Optional[TargetProbeResult] = None
        if connectivity_status == "success":
            for target in self.exit_info_targets:
                probe = self._probe_exit_info_target(target, proxies)
                exit_results.append(probe)
                if probe.success and best_exit_info is None:
                    best_exit_info = probe

        tested_targets = [item.target for item in connectivity_results]
        tested_targets.extend(item.target for item in exit_results)
        best_latency = min(
            (item.latency_ms for item in successful_connectivity if item.latency_ms is not None),
            default=None,
        )

        last_error = None
        if connectivity_status != "success":
            failures = [item.error for item in connectivity_results if not item.success and item.error]
            last_error = failures[-1] if failures else "connectivity targets failed"
        elif exit_results and best_exit_info is None:
            failures = [item.error for item in exit_results if not item.success and item.error]
            last_error = failures[-1] if failures else "exit info targets failed"

        result = TestResult(
            local_port=port,
            node_name=node_name,
            success=connectivity_status == "success",
            exit_ip=best_exit_info.ip if best_exit_info else None,
            latency_ms=best_latency,
            country=best_exit_info.country if best_exit_info else None,
            country_code=best_exit_info.country_code if best_exit_info else None,
            connectivity_status=connectivity_status,
            successful_target_count=connectivity_success_count,
            tested_targets=tested_targets,
            successful_target=best_exit_info.target if best_exit_info else (successful_connectivity[0].target if successful_connectivity else None),
            tested_target=tested_targets[-1] if tested_targets else None,
            exit_info_complete=best_exit_info is not None,
            last_probe_summary=self._summarize_targets(connectivity_results, exit_results),
            error=last_error,
        )

        if result.success:
            logger.debug(
                "[%s] %s: connectivity %s/%s, exit=%s (%s)",
                port,
                node_name,
                connectivity_success_count,
                len(connectivity_results),
                result.exit_ip or "--",
                f"{result.latency_ms:.0f}ms" if result.latency_ms is not None else "-",
            )
        return result

    def test_all(
        self,
        mappings: List[PortMapping],
        proxy_type: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        result_callback: Optional[Callable[[TestResult, int, int], None]] = None,
    ) -> List[TestResult]:
        results = []
        total = len(mappings)
        completed = 0

        logger.info(f"开始测试 {total} 个端口，最大并发: {self.max_workers}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_mapping = {
                executor.submit(
                    self.test_port,
                    mapping.local_port,
                    mapping.node.name,
                    proxy_type or get_proxy_probe_scheme(),
                ): mapping
                for mapping in mappings
            }

            for future in as_completed(future_to_mapping):
                result = future.result()
                results.append(result)
                completed += 1

                if progress_callback:
                    progress_callback(completed, total)
                if result_callback:
                    result_callback(result, completed, total)

                status = "✓" if result.success else "✗"
                if result.success:
                    logger.info(
                        f"[{completed}/{total}] {status} :{result.local_port} "
                        f"{result.node_name} -> {result.exit_ip or '--'} "
                        f"({result.latency_ms}ms, targets {result.successful_target_count}/{len(self.connectivity_targets)})"
                    )
                else:
                    logger.warning(
                        f"[{completed}/{total}] {status} :{result.local_port} "
                        f"{result.node_name} - {result.error}"
                    )

        results.sort(key=lambda r: r.local_port)
        success_count = sum(1 for r in results if r.success)
        logger.info(f"测试完成: {success_count}/{total} 成功")
        return results

    def format_results(self, results: List[TestResult]) -> str:
        lines = []
        header = f"{'端口':<8} {'状态':<4} {'节点名称':<25} {'出口 IP':<18} {'延迟':<10} {'地区':<15}"
        separator = "=" * 90

        lines.append(separator)
        lines.append(header)
        lines.append(separator)

        for r in results:
            status = "✓" if r.success else "✗"
            ip = r.exit_ip or "-"
            latency = f"{r.latency_ms}ms" if r.latency_ms else "-"
            country = r.country or (r.error[:12] if r.error else "-")
            name = r.node_name[:23] + ".." if len(r.node_name) > 25 else r.node_name
            line = f"{r.local_port:<8} {status:<4} {name:<25} {ip:<18} {latency:<10} {country:<15}"
            lines.append(line)

        lines.append(separator)
        success_count = sum(1 for r in results if r.success)
        lines.append(f"总计: {len(results)} 个节点, {success_count} 个可用")
        return "\n".join(lines)
