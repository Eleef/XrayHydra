# -*- coding: utf-8 -*-
"""
Xray-Prism 核心解析层

负责解析 vmess/vless/ss/trojan/hysteria2/ssr 协议链接，转换为统一的 ProxyNode 对象。
"""

import logging
import re
from typing import List, Optional, Dict, Any

# 尝试导入 PyYAML 用于解析 Clash 格式
try:
    import yaml
except ImportError:
    yaml = None

from .models import ProxyNode, Protocol, NetworkType
from .protocol_parsers.base import (
    ParseError,
    resolve_network_type,
)
from .protocol_parsers.hysteria2 import parse_hysteria2 as _parse_hysteria2_impl
from .protocol_parsers.registry import create_default_registry
from .protocol_parsers.shadowsocks import parse_shadowsocks as _parse_shadowsocks_impl
from .protocol_parsers.ssr import parse_ssr as _parse_ssr_impl
from .protocol_parsers.trojan import parse_trojan as _parse_trojan_impl
from .protocol_parsers.vless import parse_vless as _parse_vless_impl
from .protocol_parsers.vmess import parse_vmess as _parse_vmess_impl
from .subscription_decoders import create_default_decoder_registry

logger = logging.getLogger(__name__)

_PROTOCOL_REGISTRY = create_default_registry()
_SUBSCRIPTION_DECODER_REGISTRY = create_default_decoder_registry()


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
    return _parse_vmess_impl(uri)


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
    return _parse_vless_impl(uri)


def parse_shadowsocks(uri: str) -> ProxyNode:
    """
    解析 Shadowsocks 链接
    """
    return _parse_shadowsocks_impl(uri)


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
    return _parse_trojan_impl(uri)


def parse_hysteria2(uri: str) -> ProxyNode:
    """
    解析 Hysteria2 链接

    常见格式:
    hysteria2://password@host:port/?insecure=1&sni=example.com#name
    hy2://password@host:port/?insecure=1&sni=example.com#name
    """
    return _parse_hysteria2_impl(uri)


def parse_ssr(uri: str) -> ProxyNode:
    """
    解析 SSR 链接

    格式: ssr://base64(server:port:protocol:method:obfs:base64(password)/?params)
    """
    return _parse_ssr_impl(uri)


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
        node = _PROTOCOL_REGISTRY.parse(line)
        if node is not None:
            return node
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
    
    decoded = _SUBSCRIPTION_DECODER_REGISTRY.decode(content)

    if decoded.mode == "clash_yaml":
        logger.info("检测到 Clash YAML 格式")
        nodes = _parse_clash_yaml(decoded.content)
    else:
        # 标准 URI 列表格式
        logger.info("使用标准 URI 格式解析")
        nodes = []
        lines = decoded.content.split('\n')
        
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
            proxies = _extract_clash_proxies(config)
            if proxies:
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


def _extract_clash_proxies(config: Any) -> List[Dict[str, Any]]:
    """Extract proxy list from mainstream Clash/provider payload shapes."""
    if not config:
        return []

    if isinstance(config, list):
        return [item for item in config if isinstance(item, dict)]

    if not isinstance(config, dict):
        return []

    for key in ("proxies", "Proxy", "proxy", "payload"):
        raw = config.get(key)
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            values = [item for item in raw.values() if isinstance(item, dict)]
            if values:
                return values
    return []


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
                'hysteria2': Protocol.HYSTERIA2,
                'hy2': Protocol.HYSTERIA2,
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
                network=NetworkType.HYSTERIA if protocol == Protocol.HYSTERIA2 else NetworkType.TCP,
                tls=True,  # Clash Trojan/Hysteria2 默认启用 TLS
                sni=sni,
                allow_insecure=skip_cert_verify,
                parse_degraded=True,
                parse_degraded_reason="Clash 回退解析未提取完整字段，仅展示不可运行",
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
        server = proxy.get('server', proxy.get('address', ''))
        port = proxy.get('port', proxy.get('server_port', 0))
        
        if not server or not port:
            return None
        
        # 确定协议类型
        protocol_map = {
            'trojan': Protocol.TROJAN,
            'vmess': Protocol.VMESS,
            'vless': Protocol.VLESS,
            'ss': Protocol.SHADOWSOCKS,
            'ss2022': Protocol.SHADOWSOCKS,
            'shadowsocks': Protocol.SHADOWSOCKS,
            'hysteria2': Protocol.HYSTERIA2,
            'hy2': Protocol.HYSTERIA2,
        }
        
        protocol = protocol_map.get(proxy_type)
        if not protocol:
            logger.debug(f"不支持的协议类型: {proxy_type}")
            return None
        
        # 提取通用字段
        password = proxy.get('password', '') or proxy.get('auth-str', '') or proxy.get('auth_str', '')
        uuid = proxy.get('uuid', '')
        alter_id = proxy.get('alterId', proxy.get('alter-id', proxy.get('alter_id', 0)))
        try:
            alter_id = int(alter_id or 0)
        except (TypeError, ValueError):
            alter_id = 0

        # TLS 相关
        tls = proxy.get('tls', False)
        sni = proxy.get('sni', proxy.get('servername', ''))
        fingerprint = proxy.get('client-fingerprint', proxy.get('fingerprint'))
        skip_cert_verify = proxy.get('skip-cert-verify', False)
        if protocol == Protocol.HYSTERIA2:
            tls = True
            sni = sni or server

        # 网络类型
        network_str = proxy.get('network', 'tcp')
        parsed_network = resolve_network_type(network_str)
        network = parsed_network.network
        if protocol == Protocol.HYSTERIA2:
            network = NetworkType.HYSTERIA
        
        # WebSocket 相关
        ws_opts = proxy.get('ws-opts', proxy.get('ws_opts', {}))
        path = ws_opts.get('path', proxy.get('ws-path', ''))
        host = ''
        if ws_opts.get('headers'):
            headers = ws_opts['headers']
            host = headers.get('Host', headers.get('host', ''))

        # gRPC 相关
        grpc_opts = proxy.get('grpc-opts', proxy.get('grpc_opts', {}))
        service_name = (
            grpc_opts.get('grpc-service-name')
            or grpc_opts.get('serviceName')
            or proxy.get('grpc-service-name')
            or proxy.get('serviceName')
            or proxy.get('service_name')
            or ''
        )

        # Reality 相关
        reality_opts = proxy.get('reality-opts', proxy.get('reality_opts', {}))
        public_key = (
            proxy.get('public-key')
            or proxy.get('public_key')
            or reality_opts.get('public-key')
            or reality_opts.get('public_key')
        )
        short_id = (
            proxy.get('short-id')
            or proxy.get('short_id')
            or reality_opts.get('short-id')
            or reality_opts.get('short_id')
        )
        
        # 加密方式
        cipher = proxy.get('cipher', 'auto')
        ss_plugin = proxy.get('plugin')
        ss_plugin_opts_raw = proxy.get('plugin-opts', proxy.get('plugin_opts'))
        if isinstance(ss_plugin_opts_raw, dict):
            ss_plugin_opts = ";".join(
                f"{key}={value}" if value not in (True, False, None, "") else str(key)
                for key, value in ss_plugin_opts_raw.items()
            ) or None
        else:
            ss_plugin_opts = str(ss_plugin_opts_raw).strip() if ss_plugin_opts_raw else None
        ss_uot = proxy.get('udp-over-tcp', proxy.get('uot'))
        if isinstance(ss_uot, str):
            normalized_uot = ss_uot.strip().lower()
            if normalized_uot in ('1', 'true', 'yes', 'on'):
                ss_uot = True
            elif normalized_uot in ('0', 'false', 'no', 'off'):
                ss_uot = False
        ss_uot_version = proxy.get('udp-over-tcp-version', proxy.get('uot-version', proxy.get('uotVersion', proxy.get('UoTVersion'))))
        hy_alpn = proxy.get('alpn')
        if isinstance(hy_alpn, list):
            hy_alpn = ",".join(str(item).strip() for item in hy_alpn if str(item).strip()) or None
        elif hy_alpn is not None:
            hy_alpn = str(hy_alpn).strip() or None
        hy_obfs = proxy.get('obfs')
        hy_obfs_password = proxy.get('obfs-password', proxy.get('obfs_password'))
        
        # Trojan / Hysteria2 默认启用 TLS
        if protocol in (Protocol.TROJAN, Protocol.HYSTERIA2):
            tls = True
        if protocol == Protocol.HYSTERIA2:
            tls = True
            network = NetworkType.HYSTERIA
        
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
            fingerprint=fingerprint if fingerprint else None,
            allow_insecure=skip_cert_verify,
            path=path if path else None,
            host=host if host else None,
            alter_id=alter_id,
            service_name=service_name if service_name else None,
            public_key=public_key if public_key else None,
            short_id=short_id if short_id else None,
            hy_obfs=hy_obfs,
            hy_obfs_password=hy_obfs_password,
            hy_alpn=hy_alpn,
            ss_plugin=ss_plugin,
            ss_plugin_opts=ss_plugin_opts,
            ss_uot=ss_uot if isinstance(ss_uot, bool) else (bool(ss_uot) if ss_uot is not None else None),
            ss_uot_version=int(ss_uot_version) if ss_uot_version not in (None, "") else None,
            raw_network=parsed_network.unsupported_raw_value,
            parse_degraded=parsed_network.unsupported_raw_value is not None,
            parse_degraded_reason=(
                f"当前节点使用了未支持的 network 传输类型: {parsed_network.unsupported_raw_value}"
                if parsed_network.unsupported_raw_value
                else None
            ),
        )
        
    except Exception as e:
        logger.warning(f"Clash proxy 解析失败: {e}")
        return None

