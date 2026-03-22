"""
Node test service.
Runs isolated temporary Xray instances to test subscription nodes before
they are added into the active proxy pool.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import socket
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional
from uuid import uuid4

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.services.proxy_service import get_proxy_service
from api.services.subscription_service import get_subscription_service
from src.xray_prism.generator import ConfigGenerator
from src.xray_prism.models import (
    NetworkType,
    PortMapping,
    Protocol,
    ProxyNode,
)
from src.xray_prism.runner import XrayRunner
from src.xray_prism.tester import BACKUP_IP_APIs, DEFAULT_IP_API, ProxyTester

logger = logging.getLogger(__name__)


@dataclass
class NodeTestJob:
    """In-memory state for an asynchronous node test request."""

    job_id: str
    status: str
    total: int
    timeout: int
    test_profile: str
    completed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    progress_percent: int = 0
    active_target: Optional[str] = None
    target_index: Optional[int] = None
    target_total: Optional[int] = None
    current_target_completed: int = 0
    current_target_total: int = 0
    note: Optional[str] = None
    results: List[Dict[str, object]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class NodeTestService:
    """Service for testing nodes without mutating active proxy state."""

    def __init__(self) -> None:
        self._subscription_service = get_subscription_service()
        self._proxy_service = get_proxy_service()
        self._jobs: Dict[str, NodeTestJob] = {}
        self._jobs_lock = threading.Lock()

    def _snapshot_job(self, job: NodeTestJob) -> Dict[str, object]:
        return {
            "job_id": job.job_id,
            "status": job.status,
            "total": job.total,
            "completed_count": job.completed_count,
            "success_count": job.success_count,
            "failed_count": job.failed_count,
            "progress_percent": job.progress_percent,
            "active_target": job.active_target,
            "target_index": job.target_index,
            "target_total": job.target_total,
            "current_target_completed": job.current_target_completed,
            "current_target_total": job.current_target_total,
            "note": job.note,
            "test_profile": job.test_profile,
            "results": [dict(item) for item in job.results],
            "error": job.error,
        }

    def _update_job(self, job_id: str, **patch: object) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in patch.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def get_test_job(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return self._snapshot_job(job)

    def start_test_job(
        self,
        *,
        node_ids: List[str],
        timeout: int = 5,
        test_profile: str = "multi_target",
    ) -> Dict[str, object]:
        requested_ids = list(dict.fromkeys(node_ids))
        if not requested_ids:
            raise ValueError("node_ids cannot be empty")

        job_id = uuid4().hex
        job = NodeTestJob(
            job_id=job_id,
            status="queued",
            total=len(requested_ids),
            timeout=timeout,
            test_profile=test_profile,
            note="等待开始",
        )
        with self._jobs_lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_test_job,
            args=(job_id, requested_ids, timeout, test_profile),
            daemon=True,
        )
        thread.start()
        return self._snapshot_job(job)

    @staticmethod
    def _calculate_progress_percent(
        *,
        target_index: int,
        target_total: int,
        current_target_completed: int,
        current_target_total: int,
    ) -> int:
        if target_total <= 0:
            return 0
        if current_target_total <= 0:
            completed_targets = min(target_total, max(0, target_index))
            return min(99, round((completed_targets / target_total) * 100))
        progress = ((target_index - 1) + (current_target_completed / current_target_total)) / target_total
        return min(99, max(0, round(progress * 100)))

    @staticmethod
    def _to_proxy_node(node: Dict[str, object]) -> ProxyNode:
        return ProxyNode(
            name=str(node["name"]),
            protocol=Protocol(str(node["protocol"])),
            address=str(node["address"]),
            port=int(node["port"]),
            uuid=node.get("uuid"),
            password=node.get("password"),
            security=str(node.get("security", "auto")),
            network=NetworkType(str(node.get("network", "tcp"))),
            tls=bool(node.get("tls", False)),
            sni=node.get("sni"),
            allow_insecure=bool(node.get("allow_insecure", False)),
            path=node.get("ws_path"),
            host=node.get("ws_host"),
            service_name=node.get("grpc_service_name"),
            fingerprint=node.get("fingerprint"),
            alter_id=int(node.get("alter_id", 0)),
            flow=node.get("flow"),
            public_key=node.get("public_key"),
            short_id=node.get("short_id"),
        )

    @staticmethod
    def _find_available_ports(count: int, excluded: set[int], start: int = 20000) -> List[int]:
        ports: List[int] = []
        candidate = start
        while len(ports) < count:
            if candidate in excluded:
                candidate += 1
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.bind(("127.0.0.1", candidate))
                except OSError:
                    candidate += 1
                    continue
            ports.append(candidate)
            excluded.add(candidate)
            candidate += 1
        return ports

    @staticmethod
    def _build_result(
        *,
        node_id: str,
        node_name: str,
        proxy_port: Optional[int],
        status: str,
        latency_ms: Optional[int] = None,
        exit_ip: Optional[str] = None,
        exit_country: Optional[str] = None,
        error: Optional[str] = None,
        tested_target: Optional[str] = None,
        successful_target: Optional[str] = None,
        test_profile: str = "multi_target",
    ) -> Dict[str, object]:
        return {
            "node_id": node_id,
            "name": node_name,
            "proxy_port": proxy_port,
            "status": status,
            "latency_ms": latency_ms,
            "exit_ip": exit_ip,
            "exit_country": exit_country,
            "error": error,
            "tested_target": tested_target,
            "successful_target": successful_target,
            "test_profile": test_profile,
        }

    @staticmethod
    def _normalize_latency(value: Optional[float]) -> Optional[int]:
        if value is None:
            return None
        return int(round(value))

    def _run_test_job(
        self,
        job_id: str,
        node_ids: List[str],
        timeout: int,
        test_profile: str,
    ) -> None:
        self._update_job(
            job_id,
            status="running",
            note="准备测试环境",
            progress_percent=0,
        )
        try:
            result = self._test_nodes_impl(
                node_ids=node_ids,
                timeout=timeout,
                test_profile=test_profile,
                job_id=job_id,
            )
            self._update_job(
                job_id,
                status="completed",
                total=len(node_ids),
                completed_count=len(result["results"]),
                success_count=result["success_count"],
                failed_count=result["failed_count"],
                progress_percent=100,
                active_target=None,
                target_index=None,
                target_total=None,
                current_target_completed=0,
                current_target_total=0,
                note="测试完成",
                results=result["results"],
                error=None,
            )
        except Exception as exc:
            logger.exception("Node test job failed: %s", job_id)
            snapshot = self.get_test_job(job_id) or {}
            self._update_job(
                job_id,
                status="failed",
                progress_percent=int(snapshot.get("progress_percent", 0)),
                active_target=None,
                target_index=None,
                target_total=None,
                current_target_completed=0,
                current_target_total=0,
                note="测试失败",
                error=str(exc),
            )

    def _run_multi_target_tests(
        self,
        *,
        mappings: List[PortMapping],
        node_id_by_port: Dict[int, str],
        node_name_by_id: Dict[str, str],
        timeout: int,
        job_id: Optional[str] = None,
        total_nodes: Optional[int] = None,
        prefailed_count: int = 0,
    ) -> Dict[str, Dict[str, object]]:
        remaining: Dict[int, PortMapping] = {mapping.local_port: mapping for mapping in mappings}
        results_by_node_id: Dict[str, Dict[str, object]] = {}
        last_errors: Dict[int, Optional[str]] = {mapping.local_port: None for mapping in mappings}
        targets = [DEFAULT_IP_API, *BACKUP_IP_APIs]

        for target_index, target in enumerate(targets, start=1):
            if not remaining:
                break

            round_total = len(remaining)
            completed_before_round = len(results_by_node_id) + prefailed_count
            round_success_count = 0
            round_failure_count = 0
            if job_id:
                self._update_job(
                    job_id,
                    status="running",
                    total=total_nodes or (len(mappings) + prefailed_count),
                    completed_count=completed_before_round,
                    success_count=len(results_by_node_id),
                    failed_count=prefailed_count,
                    progress_percent=self._calculate_progress_percent(
                        target_index=target_index,
                        target_total=len(targets),
                        current_target_completed=0,
                        current_target_total=round_total,
                    ),
                    active_target=target,
                    target_index=target_index,
                    target_total=len(targets),
                    current_target_completed=0,
                    current_target_total=round_total,
                    note=f"正在测试目标 {target_index}/{len(targets)}",
                )

            def _on_round_progress(round_completed: int, total_for_round: int) -> None:
                if not job_id:
                    return
                self._update_job(
                    job_id,
                    total=total_nodes or (len(mappings) + prefailed_count),
                    completed_count=completed_before_round,
                    success_count=len(results_by_node_id),
                    failed_count=prefailed_count,
                    progress_percent=self._calculate_progress_percent(
                        target_index=target_index,
                        target_total=len(targets),
                        current_target_completed=round_completed,
                        current_target_total=total_for_round,
                    ),
                    active_target=target,
                    target_index=target_index,
                    target_total=len(targets),
                    current_target_completed=round_completed,
                    current_target_total=total_for_round,
                    note=f"目标 {target_index}/{len(targets)} 已检测 {round_completed}/{total_for_round}",
                )

            def _on_round_result(item, round_completed: int, total_for_round: int) -> None:
                nonlocal round_success_count, round_failure_count
                if item.success:
                    round_success_count += 1
                else:
                    round_failure_count += 1
                if not job_id:
                    return
                confirmed_success = len(results_by_node_id) + round_success_count
                current_failed = prefailed_count + round_failure_count
                self._update_job(
                    job_id,
                    total=total_nodes or (len(mappings) + prefailed_count),
                    completed_count=completed_before_round + round_success_count,
                    success_count=confirmed_success,
                    failed_count=current_failed,
                    progress_percent=self._calculate_progress_percent(
                        target_index=target_index,
                        target_total=len(targets),
                        current_target_completed=round_completed,
                        current_target_total=total_for_round,
                    ),
                    active_target=target,
                    target_index=target_index,
                    target_total=len(targets),
                    current_target_completed=round_completed,
                    current_target_total=total_for_round,
                    note=f"目标 {target_index}/{len(targets)} 已检测 {round_completed}/{total_for_round}",
                )

            tester = ProxyTester(
                timeout=timeout,
                ip_api=target,
                max_workers=min(20, max(1, len(remaining))),
            )
            round_results = tester.test_all(
                list(remaining.values()),
                progress_callback=_on_round_progress if job_id else None,
                result_callback=_on_round_result if job_id else None,
            )
            for item in round_results:
                if item.success:
                    node_id = node_id_by_port[item.local_port]
                    results_by_node_id[node_id] = self._build_result(
                        node_id=node_id,
                        node_name=node_name_by_id[node_id],
                        proxy_port=item.local_port,
                        status="success",
                        latency_ms=self._normalize_latency(item.latency_ms),
                        exit_ip=item.exit_ip,
                        exit_country=item.country,
                        tested_target=target,
                        successful_target=target,
                    )
                    remaining.pop(item.local_port, None)
                else:
                    last_errors[item.local_port] = item.error

            if job_id:
                self._update_job(
                    job_id,
                    total=total_nodes or (len(mappings) + prefailed_count),
                    completed_count=len(results_by_node_id) + prefailed_count,
                    success_count=len(results_by_node_id),
                    failed_count=prefailed_count,
                    progress_percent=self._calculate_progress_percent(
                        target_index=target_index,
                        target_total=len(targets),
                        current_target_completed=round_total,
                        current_target_total=round_total,
                    ),
                    active_target=target,
                    target_index=target_index,
                    target_total=len(targets),
                    current_target_completed=round_total,
                    current_target_total=round_total,
                    note=f"目标 {target_index}/{len(targets)} 完成，剩余 {len(remaining)} 个节点待重试",
                )

        final_target = targets[-1] if targets else None
        for port, mapping in remaining.items():
            node_id = node_id_by_port[port]
            results_by_node_id[node_id] = self._build_result(
                node_id=node_id,
                node_name=node_name_by_id[node_id],
                proxy_port=port,
                status="failed",
                error=last_errors.get(port) or "all test targets failed",
                tested_target=final_target,
            )

        if job_id:
            failed_total = len(remaining) + prefailed_count
            self._update_job(
                job_id,
                total=total_nodes or (len(mappings) + prefailed_count),
                completed_count=len(results_by_node_id) + prefailed_count,
                success_count=sum(1 for item in results_by_node_id.values() if item["status"] == "success"),
                failed_count=failed_total,
                progress_percent=99,
                active_target=final_target,
                target_index=len(targets),
                target_total=len(targets),
                current_target_completed=len(remaining),
                current_target_total=max(1, len(remaining)),
                note="整理最终测试结果",
            )

        return results_by_node_id

    def _test_nodes_impl(
        self,
        *,
        node_ids: List[str],
        timeout: int = 5,
        test_profile: str = "multi_target",
        job_id: Optional[str] = None,
    ) -> Dict[str, object]:
        if test_profile != "multi_target":
            raise ValueError(f"Unsupported test profile: {test_profile}")
        if not node_ids:
            raise ValueError("node_ids cannot be empty")

        requested_ids = list(dict.fromkeys(node_ids))
        nodes = self._subscription_service.get_nodes_by_ids(requested_ids)
        node_by_id = {node["id"]: node for node in nodes}

        missing_ids = [node_id for node_id in requested_ids if node_id not in node_by_id]
        valid_nodes: List[Dict[str, object]] = []
        conversion_failures: Dict[str, str] = {}
        proxy_nodes: List[ProxyNode] = []
        for node_id in requested_ids:
            node = node_by_id.get(node_id)
            if not node:
                continue
            try:
                proxy_nodes.append(self._to_proxy_node(node))
                valid_nodes.append(node)
            except Exception as exc:
                conversion_failures[node_id] = f"invalid node config: {exc}"

        if not valid_nodes:
            if missing_ids or conversion_failures:
                ordered_results: List[Dict[str, object]] = []
                for node_id in requested_ids:
                    if node_id in missing_ids:
                        ordered_results.append(
                            self._build_result(
                                node_id=node_id,
                                node_name=node_id,
                                proxy_port=None,
                                status="failed",
                                error="node not found",
                                tested_target=None,
                                test_profile=test_profile,
                            )
                        )
                        continue
                    error = conversion_failures.get(node_id)
                    node_name = str(node_by_id.get(node_id, {}).get("name", node_id))
                    ordered_results.append(
                        self._build_result(
                            node_id=node_id,
                            node_name=node_name,
                            proxy_port=None,
                            status="failed",
                            error=error or "node is not testable",
                            tested_target=None,
                            test_profile=test_profile,
                        )
                    )
                    if node_id in node_by_id:
                        self._subscription_service.update_node_test_result(
                            node_id=node_id,
                            status="failed",
                            latency_ms=None,
                            exit_ip=None,
                            exit_country=None,
                        )
                return {
                    "results": ordered_results,
                    "success_count": 0,
                    "failed_count": len(ordered_results),
                    "test_profile": test_profile,
                }
            raise ValueError("No testable nodes found")

        prefailed_count = len(missing_ids) + len(conversion_failures)
        if job_id:
            self._update_job(
                job_id,
                status="running",
                total=len(requested_ids),
                completed_count=prefailed_count,
                success_count=0,
                failed_count=prefailed_count,
                progress_percent=0,
                note="准备临时 Xray 实例",
            )

        in_use_ports = {int(item["port"]) for item in self._proxy_service.get_all_proxies()}
        assigned_ports = self._find_available_ports(len(valid_nodes), excluded=in_use_ports)

        mappings: List[PortMapping] = []
        node_id_by_port: Dict[int, str] = {}
        node_name_by_id: Dict[str, str] = {}
        for node, proxy_node, local_port in zip(valid_nodes, proxy_nodes, assigned_ports):
            mapping = PortMapping(local_port=local_port, node=proxy_node)
            mappings.append(mapping)
            node_id_by_port[local_port] = str(node["id"])
            node_name_by_id[str(node["id"])] = str(node["name"])

        run_results: Dict[str, Dict[str, object]]
        with TemporaryDirectory(prefix="xray_prism_node_test_") as tmpdir:
            tmp_path = Path(tmpdir)
            config_path = tmp_path / "node_test_config.json"
            metadata_path = tmp_path / "xray_runner.test.json"
            generator = ConfigGenerator(inbound_protocol="socks")
            generator.generate_and_save_with_mappings(mappings, str(config_path))

            runner = XrayRunner(
                project_dir=str(PROJECT_ROOT),
                process_info_file=str(metadata_path),
                track_process=False,
            )
            if not runner.find_xray():
                try:
                    runner.download_xray()
                except Exception as exc:
                    raise RuntimeError(f"Unable to prepare xray binary: {exc}") from exc

            try:
                runner.start(str(config_path))
                # Give xray a brief warm-up window before probing ports.
                time.sleep(0.8)
                run_results = self._run_multi_target_tests(
                    mappings=mappings,
                    node_id_by_port=node_id_by_port,
                    node_name_by_id=node_name_by_id,
                    timeout=timeout,
                    job_id=job_id,
                    total_nodes=len(requested_ids),
                    prefailed_count=prefailed_count,
                )
            finally:
                try:
                    runner.stop()
                except Exception:
                    logger.exception("Failed to stop temporary xray runner")

        ordered_results: List[Dict[str, object]] = []
        for node_id in requested_ids:
            if node_id in missing_ids:
                ordered_results.append(
                    self._build_result(
                        node_id=node_id,
                        node_name=node_id,
                        proxy_port=None,
                        status="failed",
                        error="node not found",
                        tested_target=None,
                    )
                )
                continue
            if node_id in conversion_failures:
                ordered_results.append(
                    self._build_result(
                        node_id=node_id,
                        node_name=str(node_by_id[node_id]["name"]),
                        proxy_port=None,
                        status="failed",
                        error=conversion_failures[node_id],
                        tested_target=None,
                    )
                )
                self._subscription_service.update_node_test_result(
                    node_id=node_id,
                    status="failed",
                    latency_ms=None,
                    exit_ip=None,
                    exit_country=None,
                )
                continue

            item = run_results[node_id]
            ordered_results.append(item)
            self._subscription_service.update_node_test_result(
                node_id=node_id,
                status=str(item["status"]),
                latency_ms=item.get("latency_ms"),
                exit_ip=item.get("exit_ip"),
                exit_country=item.get("exit_country"),
            )

        success_count = sum(1 for item in ordered_results if item["status"] == "success")
        failed_count = len(ordered_results) - success_count
        return {
            "results": ordered_results,
            "success_count": success_count,
            "failed_count": failed_count,
            "test_profile": test_profile,
        }

    def test_nodes(
        self,
        *,
        node_ids: List[str],
        timeout: int = 5,
        test_profile: str = "multi_target",
    ) -> Dict[str, object]:
        return self._test_nodes_impl(
            node_ids=node_ids,
            timeout=timeout,
            test_profile=test_profile,
            job_id=None,
        )


_node_test_service: Optional[NodeTestService] = None


def get_node_test_service() -> NodeTestService:
    global _node_test_service
    if _node_test_service is None:
        _node_test_service = NodeTestService()
    return _node_test_service
