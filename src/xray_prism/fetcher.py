# -*- coding: utf-8 -*-
"""
Xray-Prism 网络层

负责从 URL 或本地文件获取订阅内容，并进行 Base64 解码处理。
"""

import base64
import logging
from typing import Optional
from pathlib import Path

import requests

# 配置日志
logger = logging.getLogger(__name__)


class FetchError(Exception):
    """网络获取错误"""
    pass


# 默认 User-Agent，模拟常见订阅客户端
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def decode_base64(content: str) -> str:
    """
    Base64 解码工具函数
    
    支持标准 Base64 和 URL-safe Base64，自动处理 padding 问题。
    
    Args:
        content: 待解码的 Base64 字符串
        
    Returns:
        解码后的 UTF-8 字符串
        
    Raises:
        ValueError: 解码失败时抛出
    """
    # 移除空白字符
    content = content.strip()
    
    if not content:
        return ""
    
    # 将 URL-safe 字符替换为标准 Base64 字符
    content = content.replace('-', '+').replace('_', '/')
    
    # 修复 padding（Base64 字符串长度必须是 4 的倍数）
    padding_needed = 4 - (len(content) % 4)
    if padding_needed != 4:
        content += '=' * padding_needed
    
    try:
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Base64 解码失败: {e}")


def is_base64_encoded(content: str) -> bool:
    """
    检测内容是否为 Base64 编码
    
    Args:
        content: 待检测的字符串
        
    Returns:
        True 如果内容是 Base64 编码
    """
    # 如果已经包含协议前缀，则不是 Base64
    protocol_prefixes = ('vmess://', 'vless://', 'ss://', 'trojan://', 'ssr://')
    content_lower = content.strip().lower()
    
    for prefix in protocol_prefixes:
        if content_lower.startswith(prefix):
            return False
    
    # 尝试解码来判断
    try:
        decoded = decode_base64(content)
        # 检查解码结果是否包含有效协议
        for prefix in protocol_prefixes:
            if prefix in decoded.lower():
                return True
        return False
    except (ValueError, UnicodeDecodeError):
        return False


def fetch_from_url(
    url: str,
    timeout: int = 30,
    user_agent: Optional[str] = None
) -> str:
    """
    从 URL 获取订阅内容
    
    自动检测并解码 Base64 编码的内容。
    
    Args:
        url: 订阅链接 URL
        timeout: 请求超时时间（秒），默认 30
        user_agent: 自定义 User-Agent，默认使用浏览器 UA
        
    Returns:
        解码后的订阅内容（多行文本，每行一个节点链接）
        
    Raises:
        FetchError: 网络请求失败时抛出
    """
    # 模拟常见订阅客户端的请求头
    headers = {
        'User-Agent': user_agent or 'ClashforWindows/0.20.39',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
    }
    
    try:
        logger.info(f"正在从 URL 获取订阅: {url}")
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        content = response.text.strip()
        
        if not content:
            raise FetchError("订阅内容为空")
        
        # 自动检测并解码 Base64
        if is_base64_encoded(content):
            logger.debug("检测到 Base64 编码，正在解码...")
            content = decode_base64(content)
        
        logger.info(f"成功获取订阅，共 {len(content)} 字节")
        return content
        
    except requests.exceptions.Timeout:
        raise FetchError(f"请求超时 ({timeout}s): {url}")
    except requests.exceptions.ConnectionError as e:
        raise FetchError(f"连接错误: {e}")
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"HTTP 错误 {e.response.status_code}: {e}")
    except requests.exceptions.RequestException as e:
        raise FetchError(f"请求失败: {e}")


def read_from_file(path: str) -> str:
    """
    从本地文件读取订阅内容
    
    自动检测并解码 Base64 编码的内容。
    
    Args:
        path: 本地文件路径
        
    Returns:
        解码后的订阅内容
        
    Raises:
        FileNotFoundError: 文件不存在时抛出
        FetchError: 读取或解码失败时抛出
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    
    if not file_path.is_file():
        raise FetchError(f"路径不是文件: {path}")
    
    try:
        logger.info(f"正在从文件读取订阅: {path}")
        content = file_path.read_text(encoding='utf-8').strip()
        
        if not content:
            raise FetchError("文件内容为空")
        
        # 自动检测并解码 Base64
        if is_base64_encoded(content):
            logger.debug("检测到 Base64 编码，正在解码...")
            content = decode_base64(content)
        
        logger.info(f"成功读取文件，共 {len(content)} 字节")
        return content
        
    except UnicodeDecodeError as e:
        raise FetchError(f"文件编码错误: {e}")
    except IOError as e:
        raise FetchError(f"文件读取错误: {e}")


def fetch_subscription(url: Optional[str] = None, file: Optional[str] = None) -> str:
    """
    统一获取订阅内容的入口函数
    
    优先使用 URL，如果未提供则使用文件路径。
    
    Args:
        url: 订阅链接 URL（可选）
        file: 本地文件路径（可选）
        
    Returns:
        解码后的订阅内容
        
    Raises:
        ValueError: 未提供任何数据源
        FetchError: 获取失败
    """
    if url:
        return fetch_from_url(url)
    elif file:
        return read_from_file(file)
    else:
        raise ValueError("必须提供 url 或 file 参数之一")
