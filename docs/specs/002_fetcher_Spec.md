# Spec 002: Fetcher - 网络层

## 1. 概述 (Overview)

该模块负责从网络或本地文件获取订阅内容，并进行 Base64 解码处理。是数据获取的入口层，为后续解析器提供原始文本数据。

## 2. 接口设计 (API Design)

### 2.1 fetch_from_url

从 URL 获取订阅内容。

| 参数名 | 类型 | 必选 | 描述 |
| :--- | :--- | :--- | :--- |
| `url` | `str` | 是 | 订阅链接 URL |
| `timeout` | `int` | 否 | 请求超时时间（秒），默认 30 |
| `user_agent` | `str` | 否 | 自定义 User-Agent |

**Return**: `str` - 解码后的订阅内容（多行文本）

**Raises**: `FetchError` - 网络请求失败时抛出

### 2.2 read_from_file

从本地文件读取订阅内容。

| 参数名 | 类型 | 必选 | 描述 |
| :--- | :--- | :--- | :--- |
| `path` | `str` | 是 | 本地文件路径 |

**Return**: `str` - 解码后的订阅内容

**Raises**: `FileNotFoundError` - 文件不存在时抛出

### 2.3 decode_base64

Base64 解码工具函数。

| 参数名 | 类型 | 必选 | 描述 |
| :--- | :--- | :--- | :--- |
| `content` | `str` | 是 | 待解码的 Base64 字符串 |

**Return**: `str` - 解码后的 UTF-8 字符串

### 2.4 FetchError

自定义异常类，用于封装网络获取错误。

## 3. 核心逻辑 (Core Logic)

1. **URL 获取**：使用 `requests.get()` 发送 HTTP GET 请求。
2. **Base64 检测**：自动检测内容是否为 Base64 编码（通过尝试解码）。
3. **Padding 修复**：处理非标准 Base64 字符串的 padding 问题（`=` 填充）。
4. **URL-safe 支持**：同时支持标准 Base64 和 URL-safe Base64（`-_` vs `+/`）。
5. **错误处理**：所有网络异常包装为 `FetchError`，不让原始异常暴露。

## 4. 示例 (Usage Example)

```python
from fetcher import fetch_from_url, read_from_file

# 从 URL 获取
content = fetch_from_url("https://example.com/subscribe")
print(content)  # vmess://...\nvless://...\n...

# 从本地文件读取
content = read_from_file("subscription.txt")
```
