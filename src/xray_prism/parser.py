# -*- coding: utf-8 -*-
"""
Xray-Prism 核心解析层

负责解析 vmess/vless/ss/trojan 协议链接，转换为统一的 ProxyNode 对象。
"""

import base64
import json
import logging
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, unquote

# 尝试导入 PyYAML 用于解析 Clash 格式
try:
    import yaml
except ImportError:
    yaml = None

from .models import ProxyNode, Protocol, NetworkType

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """解析错误"""
    pass


def _decode_base64(content: str) -> str:
    """Base64 解码辅助函数"""
    content = content.strip()
    content = content.replace('-', '+').replace('_', '/')
    padding_needed = 4 - (len(content) % 4)
    if padding_needed != 4:
        content += '=' * padding_needed
    return base64.b64decode(content).decode('utf-8')


def _parse_network_type(net: str) -> NetworkType:
    """解析网络类型"""
    net = net.lower() if net else "tcp"
    mapping = {
        "tcp": NetworkType.TCP,
        "ws": NetworkType.WS,
        "websocket": NetworkType.WS,
        "grpc": NetworkType.GRPC,
        "gun": NetworkType.GRPC,
        "h2": NetworkType.H2,
        "http": NetworkType.H2,
        "kcp": NetworkType.KCP,
    }
    return mapping.get(net, NetworkType.TCP)


def parse_vmess(uri: str) -> ProxyNode:
    """
    解析 VMess 链接
    
    格式: vmess://base64(json)
    
    Args:
        uri: VMess 链接
        
    Returns:
        ProxyNode 对象
        
    Raises:
        ParseError: 解析失败
    """
    try:
        # 移除协议前缀
        encoded = uri.replace("vmess://", "").strip()
        
        # Base64 解码
        json_str = _decode_base64(encoded)
        config = json.loads(json_str)
        
        # 提取必要字段
        name = config.get("ps", config.get("remarks", "Unknown"))
        address = config.get("add", config.get("address", ""))
        port = int(config.get("port", 0))
        uuid = config.get("id", "")
        
        # 提取可选字段
        alter_id = int(config.get("aid", config.get("alterId", 0)))
        security = config.get("scy", config.get("security", "auto"))
        network = _parse_network_type(config.get("net", config.get("network", "tcp")))
        
        # TLS 相关
        tls = config.get("tls", "") == "tls"
        sni = config.get("sni", config.get("host", ""))
        
        # WebSocket 相关
        host = config.get("host", "")
        path = config.get("path", "")
        
        # gRPC 相关
        service_name = config.get("type", "") if network == NetworkType.GRPC else None
        
        return ProxyNode(
            name=name,
            protocol=Protocol.VMESS,
            address=address,
            port=port,
            uuid=uuid,
            alter_id=alter_id,
            security=security,
            network=network,
            tls=tls,
            sni=sni if sni else None,
            host=host if host else None,
            path=path if path else None,
            service_name=service_name,
        )
        
    except Exception as e:
        raise ParseError(f"VMess 解析失败: {e}")


def parse_vless(uri: str) -> ProxyNode:
    """
    解析 VLess 链接
    
    格式: vless://uuid@host:port?params#name
    
    Args:
        uri: VLess 链接
        
    Returns:
        ProxyNode 对象
        
    Raises:
        ParseError: 解析失败
    """
    try:
        # 解析 URL
        parsed = urlparse(uri)
        
        # 提取基本信息
        uuid = parsed.username or ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"
        
        # 解析查询参数
        params = parse_qs(parsed.query)
        
        # 提取参数（每个参数是列表，取第一个值）
        security = params.get("encryption", ["none"])[0]
        network = _parse_network_type(params.get("type", ["tcp"])[0])
        
        # TLS 相关
        tls_type = params.get("security", ["none"])[0]
        tls = tls_type in ("tls", "reality")
        sni = params.get("sni", [None])[0]
        fingerprint = params.get("fp", [None])[0]
        
        # WebSocket 相关
        host = params.get("host", [None])[0]
        path = params.get("path", [None])[0]
        if path:
            path = unquote(path)
        
        # gRPC 相关
        service_name = params.get("serviceName", [None])[0]
        
        # VLess flow
        flow = params.get("flow", [None])[0]
        
        # Reality 相关
        public_key = params.get("pbk", [None])[0]
        short_id = params.get("sid", [None])[0]
        
        return ProxyNode(
            name=name,
            protocol=Protocol.VLESS,
            address=address,
            port=port,
            uuid=uuid,
            security=security,
            network=network,
            tls=tls,
            sni=sni,
            fingerprint=fingerprint,
            host=host,
            path=path,
            service_name=service_name,
            flow=flow,
            public_key=public_key,
            short_id=short_id,
        )
        
    except Exception as e:
        raise ParseError(f"VLess 解析失败: {e}")


def parse_shadowsocks(uri: str) -> ProxyNode:
    """
    解析 Shadowsocks 链接
    
    支持两种格式:
    1. ss://base64(method:password)@host:port#name
    2. ss://base64(method:password@host:port)#name
    
    Args:
        uri: Shadowsocks 链接
        
    Returns:
        ProxyNode 对象
        
    Raises:
        ParseError: 解析失败
    """
    try:
        # 移除协议前缀
        content = uri.replace("ss://", "").strip()
        
        # 分离名称
        name = "Unknown"
        if "#" in content:
            content, name = content.rsplit("#", 1)
            name = unquote(name)
        
        # 尝试解析格式 1: base64(method:password)@host:port
        if "@" in content:
            parts = content.rsplit("@", 1)
            if len(parts) == 2:
                try:
                    user_info = _decode_base64(parts[0])
                    host_port = parts[1]
                except:
                    # 可能是格式 2
                    user_info = None
                    host_port = None
                
                if user_info and ":" in user_info:
                    method, password = user_info.split(":", 1)
                    
                    # 解析 host:port
                    if ":" in host_port:
                        address, port_str = host_port.rsplit(":", 1)
                        port = int(port_str)
                    else:
                        raise ParseError("缺少端口号")
                    
                    return ProxyNode(
                        name=name,
                        protocol=Protocol.SHADOWSOCKS,
                        address=address,
                        port=port,
                        password=password,
                        security=method,
                    )
        
        # 尝试解析格式 2: base64(完整内容)
        try:
            decoded = _decode_base64(content)
            # 格式: method:password@host:port
            match = re.match(r'([^:]+):([^@]+)@([^:]+):(\d+)', decoded)
            if match:
                method, password, address, port = match.groups()
                return ProxyNode(
                    name=name,
                    protocol=Protocol.SHADOWSOCKS,
                    address=address,
                    port=int(port),
                    password=password,
                    security=method,
                )
        except:
            pass
        
        raise ParseError("无法识别的 Shadowsocks 格式")
        
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Shadowsocks 解析失败: {e}")


def parse_trojan(uri: str) -> ProxyNode:
    """
    解析 Trojan 链接
    
    格式: trojan://password@host:port?params#name
    
    Args:
        uri: Trojan 链接
        
    Returns:
        ProxyNode 对象
        
    Raises:
        ParseError: 解析失败
    """
    try:
        # 解析 URL
        parsed = urlparse(uri)
        
        # 提取基本信息
        password = unquote(parsed.username) if parsed.username else ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"
        
        # 解析查询参数
        params = parse_qs(parsed.query)
        
        # 提取参数
        network = _parse_network_type(params.get("type", ["tcp"])[0])
        
        # TLS 相关（Trojan 默认开启 TLS）
        tls_type = params.get("security", ["tls"])[0]
        tls = tls_type != "none"
        sni = params.get("sni", [None])[0]
        fingerprint = params.get("fp", [None])[0]
        
        # allowInsecure 参数 - 跳过证书验证
        allow_insecure_str = params.get("allowInsecure", params.get("allowinsecure", ["0"]))[0]
        allow_insecure = allow_insecure_str in ("1", "true", "True")
        
        # WebSocket 相关
        host = params.get("host", [None])[0]
        path = params.get("path", [None])[0]
        if path:
            path = unquote(path)
        
        # gRPC 相关
        service_name = params.get("serviceName", [None])[0]
        
        return ProxyNode(
            name=name,
            protocol=Protocol.TROJAN,
            address=address,
            port=port,
            password=password,
            network=network,
            tls=tls,
            sni=sni,
            fingerprint=fingerprint,
            allow_insecure=allow_insecure,
            host=host,
            path=path,
            service_name=service_name,
        )
        
    except Exception as e:
        raise ParseError(f"Trojan 解析失败: {e}")


def parse_line(line: str) -> Optional[ProxyNode]:
    """
    解析单行链接
    
    自动识别协议类型并调用对应的解析函数。
    
    Args:
        line: 单行链接字符串
        
    Returns:
        ProxyNode 对象，解析失败返回 None
    """
    line = line.strip()
    
    if not line:
        return None
    
    try:
        if line.startswith("vmess://"):
            return parse_vmess(line)
        elif line.startswith("vless://"):
            return parse_vless(line)
        elif line.startswith("ss://"):
            return parse_shadowsocks(line)
        elif line.startswith("trojan://"):
            return parse_trojan(line)
        else:
            logger.debug(f"不支持的协议: {line[:20]}...")
            return None
    except ParseError as e:
        logger.warning(f"解析失败: {e}")
        return None
    except Exception as e:
        logger.warning(f"解析异常: {e}")
        return None


# 需要过滤掉的节点名称关键词（订阅元数据，非真正节点）
FILTER_KEYWORDS = [
    '剩余流量', '套餐到期', '过期时间', 'TG群', '官网',
    '到期', '流量', '订阅', '更新', '官方', 'Telegram',
    '客服', '网址', 'http', 'https', 'www.'
]


def _should_filter_node(name: str) -> bool:
    """
    检查节点是否应该被过滤
    
    Args:
        name: 节点名称
        
    Returns:
        True 如果应该过滤掉该节点
    """
    name_lower = name.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in name_lower:
            return True
    return False


def parse_subscription(content: str, filter_nodes: bool = True) -> List[ProxyNode]:
    """
    解析订阅内容
    
    自动检测订阅格式（URI 列表或 Clash YAML），并解析为 ProxyNode 列表。
    解析失败的项会被跳过并记录日志。
    
    Args:
        content: 订阅内容
        filter_nodes: 是否过滤掉元数据节点（如流量信息、到期时间等）
        
    Returns:
        ProxyNode 列表
    """
    content = content.strip()
    
    # 检测是否为 Clash YAML 格式
    if _is_clash_format(content):
        logger.info("检测到 Clash YAML 格式")
        nodes = _parse_clash_yaml(content)
    else:
        # 标准 URI 列表格式
        logger.info("使用标准 URI 格式解析")
        nodes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            node = parse_line(line)
            if node:
                nodes.append(node)
                logger.debug(f"[{i}] 解析成功: {node.name}")
            else:
                logger.debug(f"[{i}] 跳过无效行")
        
        logger.info(f"共解析 {len(nodes)} 个节点（总行数: {len(lines)}）")
    
    # 过滤元数据节点
    if filter_nodes:
        original_count = len(nodes)
        nodes = [n for n in nodes if not _should_filter_node(n.name)]
        filtered_count = original_count - len(nodes)
        if filtered_count > 0:
            logger.info(f"过滤掉 {filtered_count} 个元数据节点，剩余 {len(nodes)} 个有效节点")
    
    return nodes


def _is_clash_format(content: str) -> bool:
    """检测是否为 Clash YAML 格式"""
    # 检查是否包含 Clash 配置的关键字段
    clash_keywords = ['proxies:', 'proxy-groups:', 'mixed-port:', 'port:']
    content_lower = content.lower()
    
    for keyword in clash_keywords:
        if keyword in content_lower:
            return True
    
    return False


def _parse_clash_yaml(content: str) -> List[ProxyNode]:
    """
    解析 Clash YAML 格式配置
    
    Args:
        content: Clash YAML 配置内容
        
    Returns:
        ProxyNode 列表
    """
    nodes = []
    
    # 尝试使用 PyYAML 解析
    if yaml is not None:
        try:
            config = yaml.safe_load(content)
            if config and 'proxies' in config:
                proxies = config['proxies']
                for i, proxy in enumerate(proxies, 1):
                    node = _parse_clash_proxy(proxy)
                    if node:
                        nodes.append(node)
                        logger.debug(f"[{i}] Clash 解析成功: {node.name}")
                    else:
                        logger.debug(f"[{i}] Clash 解析跳过")
                
                logger.info(f"共解析 {len(nodes)} 个有效节点（Clash 格式）")
                return nodes
        except Exception as e:
            logger.warning(f"YAML 解析失败，尝试正则解析: {e}")
    
    # 回退到正则解析（无需 PyYAML）
    return _parse_clash_regex(content)


def _parse_clash_regex(content: str) -> List[ProxyNode]:
    """使用正则表达式解析 Clash 配置（不依赖 PyYAML）"""
    nodes = []
    
    # 匹配 proxies 区块中的每一行
    # 格式: - { name: 'xxx', type: trojan, server: xxx, port: 123, ... }
    pattern = r"-\s*\{\s*name:\s*['\"]?([^'\"}\,]+)['\"]?\s*,\s*type:\s*(\w+)\s*,\s*server:\s*([^,\s]+)\s*,\s*port:\s*(\d+)\s*,\s*password:\s*([^,\s}]+)"
    
    matches = re.findall(pattern, content)
    
    for i, match in enumerate(matches, 1):
        name, proxy_type, server, port, password = match
        name = name.strip().strip("'\"")
        
        try:
            # 提取更多参数
            # 找到这个 proxy 的完整行
            line_pattern = rf"-\s*\{{[^}}]*name:\s*['\"]?{re.escape(name)}['\"]?[^}}]*\}}"
            line_match = re.search(line_pattern, content)
            
            sni = None
            skip_cert_verify = False
            
            if line_match:
                line_content = line_match.group()
                
                # 提取 sni
                sni_match = re.search(r'sni:\s*([^,\s}]+)', line_content)
                if sni_match:
                    sni = sni_match.group(1).strip().strip("'\"")
                
                # 提取 skip-cert-verify
                if 'skip-cert-verify: true' in line_content.lower():
                    skip_cert_verify = True
            
            # 确定协议类型
            protocol_map = {
                'trojan': Protocol.TROJAN,
                'vmess': Protocol.VMESS,
                'vless': Protocol.VLESS,
                'ss': Protocol.SHADOWSOCKS,
                'shadowsocks': Protocol.SHADOWSOCKS,
            }
            
            protocol = protocol_map.get(proxy_type.lower())
            if not protocol:
                logger.debug(f"[{i}] 不支持的协议类型: {proxy_type}")
                continue
            
            node = ProxyNode(
                name=name,
                protocol=protocol,
                address=server.strip(),
                port=int(port),
                password=password.strip().strip("'\""),
                tls=True,  # Clash Trojan 默认启用 TLS
                sni=sni,
                allow_insecure=skip_cert_verify,
            )
            
            nodes.append(node)
            logger.debug(f"[{i}] 正则解析成功: {name}")
            
        except Exception as e:
            logger.warning(f"[{i}] 正则解析失败: {e}")
            continue
    
    logger.info(f"共解析 {len(nodes)} 个有效节点（正则模式）")
    return nodes


def _parse_clash_proxy(proxy: Dict[str, Any]) -> Optional[ProxyNode]:
    """
    解析单个 Clash proxy 配置
    
    Args:
        proxy: Clash proxy 字典
        
    Returns:
        ProxyNode 对象，解析失败返回 None
    """
    try:
        name = proxy.get('name', 'Unknown')
        proxy_type = proxy.get('type', '').lower()
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        
        if not server or not port:
            return None
        
        # 确定协议类型
        protocol_map = {
            'trojan': Protocol.TROJAN,
            'vmess': Protocol.VMESS,
            'vless': Protocol.VLESS,
            'ss': Protocol.SHADOWSOCKS,
            'shadowsocks': Protocol.SHADOWSOCKS,
        }
        
        protocol = protocol_map.get(proxy_type)
        if not protocol:
            logger.debug(f"不支持的协议类型: {proxy_type}")
            return None
        
        # 提取通用字段
        password = proxy.get('password', '')
        uuid = proxy.get('uuid', '')
        
        # TLS 相关
        tls = proxy.get('tls', False)
        sni = proxy.get('sni', proxy.get('servername', ''))
        skip_cert_verify = proxy.get('skip-cert-verify', False)
        
        # 网络类型
        network_str = proxy.get('network', 'tcp')
        network = _parse_network_type(network_str)
        
        # WebSocket 相关
        ws_opts = proxy.get('ws-opts', {})
        path = ws_opts.get('path', proxy.get('ws-path', ''))
        host = ''
        if ws_opts.get('headers'):
            host = ws_opts['headers'].get('Host', '')
        
        # 加密方式
        cipher = proxy.get('cipher', 'auto')
        
        # Trojan 默认启用 TLS
        if protocol == Protocol.TROJAN:
            tls = True
        
        return ProxyNode(
            name=name,
            protocol=protocol,
            address=server,
            port=int(port),
            uuid=uuid if uuid else None,
            password=password if password else None,
            security=cipher,
            network=network,
            tls=tls,
            sni=sni if sni else None,
            allow_insecure=skip_cert_verify,
            path=path if path else None,
            host=host if host else None,
        )
        
    except Exception as e:
        logger.warning(f"Clash proxy 解析失败: {e}")
        return None

