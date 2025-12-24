# -*- coding: utf-8 -*-
"""
Xray-Prism 数据模型层

定义代理协议枚举、网络传输类型枚举、统一代理节点模型和测试结果模型。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any


class Protocol(Enum):
    """代理协议类型枚举"""
    VMESS = "vmess"
    VLESS = "vless"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"


class NetworkType(Enum):
    """网络传输类型枚举"""
    TCP = "tcp"
    WS = "ws"
    GRPC = "grpc"
    H2 = "h2"
    KCP = "kcp"


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
