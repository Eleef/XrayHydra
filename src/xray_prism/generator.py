# -*- coding: utf-8 -*-
"""
Xray-Prism 配置生成层

生成 Xray-core 的 config.json 配置文件。
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import (
    ProxyNode,
    Protocol,
    NetworkType,
    PortMapping,
    get_runtime_support_reason,
    is_runtime_supported_protocol,
)
from .runtime_adapters.xray import XrayAdapterRegistry

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Xray 配置生成器"""
    
    def __init__(
        self,
        start_port: int = 10000,
        listen_address: str = "127.0.0.1",
        inbound_protocol: str = "http"  # 或 "socks"
    ):
        """
        初始化配置生成器
        
        Args:
            start_port: 起始端口号
            listen_address: 监听地址
            inbound_protocol: 入站协议类型（http 或 socks）
        """
        self.start_port = start_port
        self.listen_address = listen_address
        self.inbound_protocol = inbound_protocol
        self._adapter_registry = XrayAdapterRegistry()
    
    def generate(self, nodes: List[ProxyNode]) -> Dict[str, Any]:
        """
        生成完整的 Xray 配置
        
        Args:
            nodes: 代理节点列表
            
        Returns:
            Xray 配置字典
        """
        mappings = self._create_port_mappings(nodes)
        
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": self._generate_inbounds(mappings),
            "outbounds": self._generate_outbounds(mappings),
            "routing": self._generate_routing(mappings)
        }
        
        return config
    
    def generate_and_save(
        self,
        nodes: List[ProxyNode],
        output_path: str
    ) -> List[PortMapping]:
        """
        生成配置并保存到文件
        
        Args:
            nodes: 代理节点列表
            output_path: 输出文件路径
            
        Returns:
            端口映射列表
        """
        mappings = self._create_port_mappings(nodes)
        config = self.generate(nodes)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置已保存到: {output_path}")
        return mappings
    
    def generate_with_mappings(self, mappings: List[PortMapping]) -> Dict[str, Any]:
        """
        使用外部提供的端口映射生成完整的 Xray 配置
        
        Args:
            mappings: 端口映射列表
            
        Returns:
            Xray 配置字典
        """
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": self._generate_inbounds(mappings),
            "outbounds": self._generate_outbounds(mappings),
            "routing": self._generate_routing(mappings)
        }
        
        return config
    
    def generate_and_save_with_mappings(
        self,
        mappings: List[PortMapping],
        output_path: str
    ) -> List[PortMapping]:
        """
        使用外部端口映射生成配置并保存到文件
        
        Args:
            mappings: 端口映射列表
            output_path: 输出文件路径
            
        Returns:
            端口映射列表
        """
        config = self.generate_with_mappings(mappings)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置已保存到: {output_path} (使用自定义端口映射)")
        return mappings
    
    def _create_port_mappings(self, nodes: List[ProxyNode]) -> List[PortMapping]:
        """创建端口映射列表"""
        mappings = []
        for i, node in enumerate(nodes):
            port = self.start_port + i
            mappings.append(PortMapping(local_port=port, node=node))
        return mappings
    
    def _generate_inbounds(self, mappings: List[PortMapping]) -> List[Dict[str, Any]]:
        """生成入站配置"""
        inbounds = []
        
        for mapping in mappings:
            inbound = {
                "tag": mapping.inbound_tag,
                "port": mapping.local_port,
                "listen": self.listen_address,
                "protocol": self.inbound_protocol,
                "settings": {}
            }
            
            if self.inbound_protocol == "socks":
                inbound["settings"] = {
                    "auth": "noauth",
                    "udp": True
                }
            elif self.inbound_protocol == "http":
                inbound["settings"] = {
                    "allowTransparent": False
                }
            
            inbounds.append(inbound)
        
        return inbounds
    
    def _generate_outbounds(self, mappings: List[PortMapping]) -> List[Dict[str, Any]]:
        """生成出站配置"""
        outbounds = []
        
        # 为每个节点生成出站配置
        for mapping in mappings:
            outbound = self._node_to_outbound(mapping.node, mapping.outbound_tag)
            outbounds.append(outbound)
        
        # 添加 freedom 直连出站作为 fallback
        outbounds.append({
            "tag": "direct",
            "protocol": "freedom",
            "settings": {}
        })
        
        # 添加 blackhole 出站用于阻断
        outbounds.append({
            "tag": "block",
            "protocol": "blackhole",
            "settings": {}
        })
        
        return outbounds
    
    def _generate_routing(self, mappings: List[PortMapping]) -> Dict[str, Any]:
        """生成路由配置"""
        rules = []
        
        # 为每个端口创建 1 对 1 的路由规则
        for mapping in mappings:
            rules.append({
                "type": "field",
                "inboundTag": [mapping.inbound_tag],
                "outboundTag": mapping.outbound_tag
            })
        
        return {
            "domainStrategy": "AsIs",
            "rules": rules
        }
    
    def _node_to_outbound(self, node: ProxyNode, tag: str) -> Dict[str, Any]:
        """将 ProxyNode 转换为 Xray 出站配置"""
        if not is_runtime_supported_protocol(node.protocol):
            reason = get_runtime_support_reason(node.protocol) or f"不支持的协议: {node.protocol.value}"
            raise ValueError(reason)
        return self._adapter_registry.build_outbound(node, tag, self._stream_settings)
    
    def _stream_settings(self, node: ProxyNode) -> Dict[str, Any]:
        """生成传输层配置"""
        settings: Dict[str, Any] = {
            "network": node.network.value
        }
        
        # TLS 配置
        if node.tls:
            if node.public_key:  # Reality
                settings["security"] = "reality"
                settings["realitySettings"] = {
                    "serverName": node.sni or node.address,
                    "fingerprint": node.fingerprint or "chrome",
                    "publicKey": node.public_key,
                    "shortId": node.short_id or ""
                }
            else:  # 普通 TLS
                settings["security"] = "tls"
                tls_settings: Dict[str, Any] = {}
                if node.sni:
                    tls_settings["serverName"] = node.sni
                if node.fingerprint:
                    tls_settings["fingerprint"] = node.fingerprint
                # 关键：allowInsecure 参数
                if node.allow_insecure:
                    tls_settings["allowInsecure"] = True
                # 确保 tlsSettings 始终存在
                settings["tlsSettings"] = tls_settings if tls_settings else {}
        else:
            settings["security"] = "none"
        
        # WebSocket 配置
        if node.network == NetworkType.WS:
            ws_settings: Dict[str, Any] = {}
            if node.path:
                ws_settings["path"] = node.path
            if node.host:
                ws_settings["headers"] = {"Host": node.host}
            if ws_settings:
                settings["wsSettings"] = ws_settings
        
        # gRPC 配置
        elif node.network == NetworkType.GRPC:
            grpc_settings: Dict[str, Any] = {}
            if node.service_name:
                grpc_settings["serviceName"] = node.service_name
            if grpc_settings:
                settings["grpcSettings"] = grpc_settings
        
        # HTTP/2 配置
        elif node.network == NetworkType.H2:
            h2_settings: Dict[str, Any] = {}
            if node.path:
                h2_settings["path"] = node.path
            if node.host:
                h2_settings["host"] = [node.host]
            if h2_settings:
                settings["httpSettings"] = h2_settings
        
        return settings
