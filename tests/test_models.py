# -*- coding: utf-8 -*-
"""
Unit 1: models.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from xray_prism.models import (
    Protocol, 
    NetworkType, 
    ProxyNode, 
    TestResult,
    PortMapping,
    is_runtime_supported_protocol,
    get_runtime_support_reason,
)


class TestProtocolEnum:
    """Protocol 枚举测试"""
    
    def test_protocol_values(self):
        """测试协议枚举值"""
        assert Protocol.VMESS.value == "vmess"
        assert Protocol.VLESS.value == "vless"
        assert Protocol.SHADOWSOCKS.value == "shadowsocks"
        assert Protocol.TROJAN.value == "trojan"
        assert Protocol.HYSTERIA2.value == "hysteria2"
        assert Protocol.SSR.value == "ssr"
    
    def test_protocol_from_string(self):
        """测试从字符串创建枚举"""
        assert Protocol("vmess") == Protocol.VMESS

    def test_runtime_support_matrix(self):
        """测试协议运行支持矩阵。"""
        assert is_runtime_supported_protocol("hysteria2") is True
        assert is_runtime_supported_protocol("ssr") is False
        assert get_runtime_support_reason("ssr") is not None


class TestNetworkTypeEnum:
    """NetworkType 枚举测试"""
    
    def test_network_values(self):
        """测试网络类型枚举值"""
        assert NetworkType.TCP.value == "tcp"
        assert NetworkType.WS.value == "ws"
        assert NetworkType.GRPC.value == "grpc"
        assert NetworkType.H2.value == "h2"
        assert NetworkType.KCP.value == "kcp"
        assert NetworkType.HYSTERIA.value == "hysteria"
        assert NetworkType.HYSTERIA.value == "hysteria"


class TestProxyNode:
    """ProxyNode 数据类测试"""
    
    def test_create_vmess_node(self):
        """测试创建 VMess 节点"""
        node = ProxyNode(
            name="香港-01",
            protocol=Protocol.VMESS,
            address="hk.example.com",
            port=443,
            uuid="a3482e88-686a-4a58-8126-99c9df64b7bf",
            network=NetworkType.WS,
            tls=True,
            path="/ws"
        )
        
        assert node.name == "香港-01"
        assert node.protocol == Protocol.VMESS
        assert node.address == "hk.example.com"
        assert node.port == 443
        assert node.uuid == "a3482e88-686a-4a58-8126-99c9df64b7bf"
        assert node.network == NetworkType.WS
        assert node.tls is True
        assert node.path == "/ws"
    
    def test_create_ss_node(self):
        """测试创建 Shadowsocks 节点"""
        node = ProxyNode(
            name="日本-SS",
            protocol=Protocol.SHADOWSOCKS,
            address="jp.example.com",
            port=8388,
            password="test_password",
            security="aes-256-gcm"
        )
        
        assert node.protocol == Protocol.SHADOWSOCKS
        assert node.password == "test_password"
        assert node.security == "aes-256-gcm"
    
    def test_create_trojan_node(self):
        """测试创建 Trojan 节点"""
        node = ProxyNode(
            name="美国-Trojan",
            protocol=Protocol.TROJAN,
            address="us.example.com",
            port=443,
            password="trojan_password",
            tls=True,
            sni="example.com"
        )
        
        assert node.protocol == Protocol.TROJAN
        assert node.password == "trojan_password"
        assert node.tls is True
        assert node.sni == "example.com"

    def test_create_hysteria2_node(self):
        """测试创建 Hysteria2 节点"""
        node = ProxyNode(
            name="新加坡-HY2",
            protocol=Protocol.HYSTERIA2,
            address="sg.example.com",
            port=8443,
            password="hy2-secret",
            network=NetworkType.HYSTERIA,
            tls=True,
            sni="sg.example.com",
            allow_insecure=True,
            hy_alpn="h3",
        )

        assert node.protocol == Protocol.HYSTERIA2
        assert node.password == "hy2-secret"
        assert node.network == NetworkType.HYSTERIA
        assert node.sni == "sg.example.com"
        assert node.hy_alpn == "h3"
    
    def test_default_values(self):
        """测试默认值"""
        node = ProxyNode(
            name="测试节点",
            protocol=Protocol.VMESS,
            address="test.com",
            port=443
        )
        
        assert node.security == "auto"
        assert node.network == NetworkType.TCP
        assert node.tls is False
        assert node.alter_id == 0
    
    def test_to_dict(self):
        """测试 to_dict 方法"""
        node = ProxyNode(
            name="测试",
            protocol=Protocol.VMESS,
            address="test.com",
            port=443,
            uuid="test-uuid"
        )
        
        result = node.to_dict()
        
        assert result["name"] == "测试"
        assert result["protocol"] == "vmess"
        assert result["address"] == "test.com"
        assert result["port"] == 443
        assert result["uuid"] == "test-uuid"
        assert result["network"] == "tcp"
    
    def test_validation_empty_name(self):
        """测试空名称验证"""
        with pytest.raises(ValueError, match="节点名称.*不能为空"):
            ProxyNode(
                name="",
                protocol=Protocol.VMESS,
                address="test.com",
                port=443
            )
    
    def test_validation_empty_address(self):
        """测试空地址验证"""
        with pytest.raises(ValueError, match="服务器地址.*不能为空"):
            ProxyNode(
                name="测试",
                protocol=Protocol.VMESS,
                address="",
                port=443
            )
    
    def test_validation_invalid_port(self):
        """测试无效端口验证"""
        with pytest.raises(ValueError, match="端口号无效"):
            ProxyNode(
                name="测试",
                protocol=Protocol.VMESS,
                address="test.com",
                port=0
            )
        
        with pytest.raises(ValueError, match="端口号无效"):
            ProxyNode(
                name="测试",
                protocol=Protocol.VMESS,
                address="test.com",
                port=70000
            )


class TestTestResult:
    """TestResult 数据类测试"""
    
    def test_create_success_result(self):
        """测试创建成功的测试结果"""
        result = TestResult(
            local_port=10001,
            node_name="香港-01",
            success=True,
            exit_ip="1.2.3.4",
            latency_ms=150.5,
            country="Hong Kong"
        )
        
        assert result.local_port == 10001
        assert result.node_name == "香港-01"
        assert result.success is True
        assert result.exit_ip == "1.2.3.4"
        assert result.latency_ms == 150.5
    
    def test_create_failed_result(self):
        """测试创建失败的测试结果"""
        result = TestResult(
            local_port=10002,
            node_name="日本-02",
            success=False,
            error="Connection timeout"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.exit_ip is None
    
    def test_to_dict(self):
        """测试 to_dict 方法"""
        result = TestResult(
            local_port=10001,
            node_name="测试",
            success=True,
            exit_ip="1.2.3.4"
        )
        
        data = result.to_dict()
        assert "local_port" in data
        assert "exit_ip" in data
        assert "error" not in data  # None 值不应包含


class TestPortMapping:
    """PortMapping 数据类测试"""
    
    def test_auto_generate_tags(self):
        """测试自动生成 inbound/outbound tag"""
        node = ProxyNode(
            name="测试",
            protocol=Protocol.VMESS,
            address="test.com",
            port=443
        )
        
        mapping = PortMapping(local_port=10001, node=node)
        
        assert mapping.inbound_tag == "in_10001"
        assert mapping.outbound_tag == "out_10001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
