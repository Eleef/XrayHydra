# -*- coding: utf-8 -*-
"""
Xray-Prism 验证测试层

使用并发方式测试所有代理端口的连通性。
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable

import requests

from api.services.geo_service import GeoLookupError, get_geo_service
from .models import TestResult, PortMapping
from .proxy_runtime import get_proxy_access_host

logger = logging.getLogger(__name__)

# 默认 IP 检测接口
DEFAULT_IP_API = "http://ip-api.com/json"
BACKUP_IP_APIs = [
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
]


class ProxyTester:
    """代理连通性测试器"""
    
    def __init__(
        self,
        timeout: int = 5,
        ip_api: str = DEFAULT_IP_API,
        max_workers: int = 20,
        listen_address: Optional[str] = None
    ):
        """
        初始化测试器
        
        Args:
            timeout: 请求超时时间（秒）
            ip_api: IP 检测接口 URL
            max_workers: 最大并发线程数
            listen_address: 代理监听地址
        """
        self.timeout = timeout
        self.ip_api = ip_api
        self.max_workers = max_workers
        self.listen_address = listen_address or get_proxy_access_host()
    
    def test_port(
        self,
        port: int,
        node_name: str,
        proxy_type: str = "http"
    ) -> TestResult:
        """
        测试单个端口
        
        Args:
            port: 本地代理端口
            node_name: 节点名称
            proxy_type: 代理类型（http 或 socks5）
            
        Returns:
            TestResult 测试结果
        """
        proxy_url = f"{proxy_type}://{self.listen_address}:{port}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        start_time = time.time()
        
        try:
            response = requests.get(
                self.ip_api,
                proxies=proxies,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 解析响应
            data = response.json()
            
            # 兼容不同 API 的响应格式
            exit_ip = data.get("query") or data.get("origin") or data.get("ip")
            country = data.get("country") or data.get("country_name")
            country_code = data.get("countryCode") or data.get("country_code")

            if exit_ip and (not country or not country_code):
                try:
                    geo_info = get_geo_service().lookup_ip(str(exit_ip))
                    country = country or geo_info.get("country")
                    country_code = country_code or geo_info.get("country_code")
                except (GeoLookupError, ValueError):
                    pass
            elif exit_ip and country_code:
                try:
                    get_geo_service().remember_region(str(exit_ip), country, country_code)
                except ValueError:
                    pass
            
            logger.debug(f"[{port}] {node_name}: {exit_ip} ({latency_ms:.0f}ms)")
            
            return TestResult(
                local_port=port,
                node_name=node_name,
                success=True,
                exit_ip=exit_ip,
                latency_ms=round(latency_ms, 2),
                country=country,
                country_code=country_code,
            )
            
        except requests.exceptions.Timeout:
            return TestResult(
                local_port=port,
                node_name=node_name,
                success=False,
                error="请求超时"
            )
        except requests.exceptions.ProxyError as e:
            return TestResult(
                local_port=port,
                node_name=node_name,
                success=False,
                error=f"代理错误: {str(e)[:50]}"
            )
        except requests.exceptions.ConnectionError as e:
            return TestResult(
                local_port=port,
                node_name=node_name,
                success=False,
                error=f"连接错误: {str(e)[:50]}"
            )
        except Exception as e:
            return TestResult(
                local_port=port,
                node_name=node_name,
                success=False,
                error=f"未知错误: {str(e)[:50]}"
            )
    
    def test_all(
        self,
        mappings: List[PortMapping],
        proxy_type: str = "http",
        progress_callback: Optional[Callable[[int, int], None]] = None,
        result_callback: Optional[Callable[[TestResult, int, int], None]] = None,
    ) -> List[TestResult]:
        """
        并发测试所有端口
        
        Args:
            mappings: 端口映射列表
            proxy_type: 代理类型
            progress_callback: 进度回调函数 (completed, total)
            result_callback: 每个结果返回后的回调 (result, completed, total)
            
        Returns:
            TestResult 列表
        """
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
                    proxy_type
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
                
                # 日志输出
                status = "✓" if result.success else "✗"
                if result.success:
                    logger.info(
                        f"[{completed}/{total}] {status} :{result.local_port} "
                        f"{result.node_name} -> {result.exit_ip} ({result.latency_ms}ms)"
                    )
                else:
                    logger.warning(
                        f"[{completed}/{total}] {status} :{result.local_port} "
                        f"{result.node_name} - {result.error}"
                    )
        
        # 按端口号排序
        results.sort(key=lambda r: r.local_port)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        logger.info(f"测试完成: {success_count}/{total} 成功")
        
        return results
    
    def format_results(self, results: List[TestResult]) -> str:
        """
        格式化测试结果为表格
        
        Args:
            results: 测试结果列表
            
        Returns:
            格式化的表格字符串
        """
        lines = []
        
        # 表头
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
        
        # 统计
        success_count = sum(1 for r in results if r.success)
        lines.append(f"总计: {len(results)} 个节点, {success_count} 个可用")
        
        return "\n".join(lines)
