# -*- coding: utf-8 -*-
"""
Xray-Prism 数据模型层

定义代理协议枚举、网络传输类型枚举、统一代理节点模型和测试结果模型。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class Protocol(Enum):
    """代理协议类型枚举"""
    VMESS = "vmess"
    VLESS = "vless"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"
    HYSTERIA2 = "hysteria2"
    SSR = "ssr"


def is_runtime_supported_protocol(protocol: Protocol | str) -> bool:
    """Return whether the current runtime can generate and run this protocol."""
    from .capabilities import is_runtime_supported
    return is_runtime_supported(protocol)


def get_runtime_support_reason(protocol: Protocol | str) -> Optional[str]:
    """Return the runtime support note for a protocol, if any."""
    from .capabilities import get_runtime_support_reason as _get_runtime_support_reason
    return _get_runtime_support_reason(protocol)


class NetworkType(Enum):
    """网络传输类型枚举"""
    TCP = "tcp"
    WS = "ws"
    GRPC = "grpc"
    H2 = "h2"
    KCP = "kcp"
    HYSTERIA = "hysteria"


@dataclass
class ProxyNode:
    """
    统一代理节点模型
    
    屏蔽不同协议（vmess/vless/ss/trojan）的差异，提供标准化的数据对象。
    """
    # 必填字段
    name: str
    protocol: Protocol
    address: str
    port: int
    
    # VMess/VLess 使用 UUID
    uuid: Optional[str] = None
    
    # Shadowsocks/Trojan 使用密码
    password: Optional[str] = None
    
    # 加密方式（默认 auto）
    security: str = "auto"
    
    # 传输方式（默认 TCP）
    network: NetworkType = NetworkType.TCP
    
    # TLS 相关
    tls: bool = False
    sni: Optional[str] = None
    fingerprint: Optional[str] = None
    allow_insecure: bool = False  # 跳过证书验证
    
    # WebSocket/HTTP2 相关
    host: Optional[str] = None
    path: Optional[str] = None
    
    # VMess 专用
    alter_id: int = 0
    
    # VLess 专用
    flow: Optional[str] = None
    
    # gRPC 专用
    service_name: Optional[str] = None
    
    # Reality 专用
    public_key: Optional[str] = None
    short_id: Optional[str] = None

    # Hysteria2 专用
    hy_obfs: Optional[str] = None
    hy_obfs_password: Optional[str] = None
    hy_alpn: Optional[str] = None

    # Shadowsocks 专用
    ss_plugin: Optional[str] = None
    ss_plugin_opts: Optional[str] = None
    ss_uot: Optional[bool] = None
    ss_uot_version: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，便于 JSON 序列化
        
        Returns:
            Dict[str, Any]: 节点配置字典，枚举值转为字符串
        """
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        return result
    
    def __post_init__(self):
        """数据验证"""
        if not self.name:
            raise ValueError("节点名称 (name) 不能为空")
        if not self.address:
            raise ValueError("服务器地址 (address) 不能为空")
        if not isinstance(self.port, int) or self.port <= 0 or self.port > 65535:
            raise ValueError(f"端口号无效: {self.port}")


@dataclass
class TestResult:
    """
    代理测试结果模型
    
    记录每个端口的测试结果，包括成功状态、出口 IP 和延迟。
    """
    # 必填字段
    local_port: int
    node_name: str
    success: bool
    
    # 成功时填充
    exit_ip: Optional[str] = None
    latency_ms: Optional[float] = None
    country: Optional[str] = None
    
    # 失败时填充
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 测试结果字典
        """
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class PortMapping:
    """
    端口映射记录
    
    记录本地端口与代理节点的对应关系。
    """
    local_port: int
    node: ProxyNode
    inbound_tag: str = field(init=False)
    outbound_tag: str = field(init=False)
    
    def __post_init__(self):
        """自动生成 inbound/outbound tag"""
        self.inbound_tag = f"in_{self.local_port}"
        self.outbound_tag = f"out_{self.local_port}"


class HealthStatus(Enum):
    """代理健康状态枚举"""
    HEALTHY = "healthy"      # 正常可用
    DEGRADED = "degraded"    # 降级（曾失败但已恢复，仍需观察）
    DISABLED = "disabled"    # 禁用（冷却中，不参与路由）


@dataclass
class ProxyHealthState:
    """
    代理健康状态模型
    
    跟踪单个代理的健康状态、失败次数和罚时信息。
    """
    proxy_port: int
    status: HealthStatus = HealthStatus.HEALTHY
    failure_count: int = 0          # 连续失败次数
    penalty_level: int = 0          # 当前罚时等级 (0-3)
    penalty_until: Optional[datetime] = None  # 罚时结束时间
    last_check: Optional[datetime] = None     # 最后检测时间
    last_success: Optional[datetime] = None   # 最后成功时间
    last_latency_ms: Optional[float] = None   # 最后成功延迟
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "proxy_port": self.proxy_port,
            "status": self.status.value,
            "failure_count": self.failure_count,
            "penalty_level": self.penalty_level,
        }
        if self.penalty_until:
            result["penalty_until"] = self.penalty_until.isoformat()
        if self.last_check:
            result["last_check"] = self.last_check.isoformat()
        if self.last_success:
            result["last_success"] = self.last_success.isoformat()
        if self.last_latency_ms is not None:
            result["last_latency_ms"] = self.last_latency_ms
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxyHealthState":
        """从字典创建实例"""
        status = HealthStatus(data.get("status", "healthy"))
        penalty_until = None
        if data.get("penalty_until"):
            penalty_until = datetime.fromisoformat(data["penalty_until"])
        last_check = None
        if data.get("last_check"):
            last_check = datetime.fromisoformat(data["last_check"])
        last_success = None
        if data.get("last_success"):
            last_success = datetime.fromisoformat(data["last_success"])
        
        return cls(
            proxy_port=data["proxy_port"],
            status=status,
            failure_count=data.get("failure_count", 0),
            penalty_level=data.get("penalty_level", 0),
            penalty_until=penalty_until,
            last_check=last_check,
            last_success=last_success,
            last_latency_ms=data.get("last_latency_ms"),
        )
