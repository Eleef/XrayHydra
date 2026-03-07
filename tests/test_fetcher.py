# -*- coding: utf-8 -*-
"""
Unit 2: fetcher.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import patch, MagicMock
import base64
import tempfile
from pathlib import Path

from xray_prism.fetcher import (
    build_accept_encoding,
    decode_base64,
    is_base64_encoded,
    fetch_from_url,
    read_from_file,
    fetch_subscription,
    FetchError
)


class TestDecodeBase64:
    """Base64 解码测试"""
    
    def test_decode_standard_base64(self):
        """测试标准 Base64 解码"""
        original = "vmess://test123"
        encoded = base64.b64encode(original.encode()).decode()
        
        result = decode_base64(encoded)
        assert result == original
    
    def test_decode_urlsafe_base64(self):
        """测试 URL-safe Base64 解码"""
        original = "vmess://test+data/path"
        # URL-safe 编码会将 + 替换为 -，/ 替换为 _
        encoded = base64.urlsafe_b64encode(original.encode()).decode()
        
        result = decode_base64(encoded)
        assert result == original
    
    def test_decode_with_missing_padding(self):
        """测试缺少 padding 的 Base64"""
        original = "test"
        encoded = base64.b64encode(original.encode()).decode().rstrip('=')
        
        result = decode_base64(encoded)
        assert result == original
    
    def test_decode_empty_string(self):
        """测试空字符串"""
        assert decode_base64("") == ""
        assert decode_base64("   ") == ""
    
    def test_decode_invalid_base64(self):
        """测试无效 Base64"""
        with pytest.raises(ValueError, match="Base64 解码失败"):
            decode_base64("这不是Base64!!!")


class TestIsBase64Encoded:
    """Base64 编码检测测试"""
    
    def test_detect_base64_content(self):
        """测试检测 Base64 编码内容"""
        original = "vmess://eyJ2IjoiMiJ9"
        encoded = base64.b64encode(original.encode()).decode()
        
        assert is_base64_encoded(encoded) is True
    
    def test_detect_plain_protocol_link(self):
        """测试检测明文协议链接"""
        assert is_base64_encoded("vmess://eyJ2IjoiMiJ9") is False
        assert is_base64_encoded("vless://user@host:443") is False
        assert is_base64_encoded("ss://YWVz") is False
        assert is_base64_encoded("trojan://pass@host:443") is False


class TestFetchFromUrl:
    """URL 获取测试"""

    @patch('xray_prism.fetcher.HAS_BROTLI', False)
    def test_build_accept_encoding_default(self):
        """测试默认仅声明环境支持的压缩编码"""
        encoding = build_accept_encoding()
        assert encoding == "gzip, deflate"

    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_plain_content(self, mock_get):
        """测试获取明文内容"""
        mock_response = MagicMock()
        mock_response.text = "vmess://test1\nvless://test2"
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_from_url("https://example.com/sub")

        assert "vmess://test1" in result
        assert "vless://test2" in result
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Accept-Encoding"] == build_accept_encoding()

    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_base64_content(self, mock_get):
        """测试获取并解码 Base64 内容"""
        original = "vmess://test1\nvless://test2"
        encoded = base64.b64encode(original.encode()).decode()

        mock_response = MagicMock()
        mock_response.text = encoded
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = fetch_from_url("https://example.com/sub")
        
        assert result == original
    
    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_timeout(self, mock_get):
        """测试请求超时"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(FetchError, match="请求超时"):
            fetch_from_url("https://example.com/sub", timeout=5)
    
    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_connection_error(self, mock_get):
        """测试连接错误"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        with pytest.raises(FetchError, match="连接错误"):
            fetch_from_url("https://example.com/sub")
    
    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_empty_content(self, mock_get):
        """测试空内容"""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(FetchError, match="订阅内容为空"):
            fetch_from_url("https://example.com/sub")

    @patch('xray_prism.fetcher.HAS_BROTLI', False)
    @patch('xray_prism.fetcher.requests.get')
    def test_fetch_brotli_without_support(self, mock_get):
        """测试未启用 Brotli 支持时返回明确错误"""
        mock_response = MagicMock()
        mock_response.text = "binary-data"
        mock_response.headers = {"Content-Encoding": "br"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(FetchError, match="Brotli"):
            fetch_from_url("https://example.com/sub")


class TestReadFromFile:
    """文件读取测试"""
    
    def test_read_plain_file(self):
        """测试读取明文文件"""
        content = "vmess://test1\nvless://test2"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = read_from_file(temp_path)
            assert result == content
        finally:
            os.unlink(temp_path)
    
    def test_read_base64_file(self):
        """测试读取并解码 Base64 文件"""
        original = "vmess://test1\nvless://test2"
        encoded = base64.b64encode(original.encode()).decode()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(encoded)
            temp_path = f.name
        
        try:
            result = read_from_file(temp_path)
            assert result == original
        finally:
            os.unlink(temp_path)
    
    def test_read_nonexistent_file(self):
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError):
            read_from_file("/nonexistent/path/file.txt")
    
    def test_read_empty_file(self):
        """测试读取空文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(FetchError, match="文件内容为空"):
                read_from_file(temp_path)
        finally:
            os.unlink(temp_path)


class TestFetchSubscription:
    """统一获取入口测试"""
    
    @patch('xray_prism.fetcher.fetch_from_url')
    def test_fetch_with_url(self, mock_fetch):
        """测试使用 URL 获取"""
        mock_fetch.return_value = "vmess://test"
        
        result = fetch_subscription(url="https://example.com/sub")
        
        mock_fetch.assert_called_once_with("https://example.com/sub")
        assert result == "vmess://test"
    
    @patch('xray_prism.fetcher.read_from_file')
    def test_fetch_with_file(self, mock_read):
        """测试使用文件获取"""
        mock_read.return_value = "vless://test"
        
        result = fetch_subscription(file="/path/to/file.txt")
        
        mock_read.assert_called_once_with("/path/to/file.txt")
        assert result == "vless://test"
    
    @patch('xray_prism.fetcher.fetch_from_url')
    def test_url_takes_priority(self, mock_fetch):
        """测试 URL 优先于文件"""
        mock_fetch.return_value = "vmess://url"
        
        result = fetch_subscription(url="https://example.com", file="/path/file.txt")
        
        mock_fetch.assert_called_once()
        assert result == "vmess://url"
    
    def test_no_source_provided(self):
        """测试未提供数据源"""
        with pytest.raises(ValueError, match="必须提供"):
            fetch_subscription()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
