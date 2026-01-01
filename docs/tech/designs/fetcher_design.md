# **Fetcher Module Technical Design**

> **Moved from**: `docs/specs/002_fetcher_Spec.md`
> **Last Updated**: 2026-01-02

## **1. Overview (概述)**
该模块负责从网络或本地文件获取订阅内容，并进行 Base64 解码处理。它是数据获取的入口层，为后续解析器提供原始文本数据。

## **2. Interface Design (接口设计)**

### **2.1 fetch_from_url**
*   **Function**: `fetch_from_url(url: str, timeout: int = 30) -> str`
*   **Description**: 从 URL 获取订阅内容，支持模拟 User-Agent。
*   **Error Handling**: 抛出 `FetchError` 以屏蔽底层网络异常。

### **2.2 read_from_file**
*   **Function**: `read_from_file(path: str) -> str`
*   **Description**: 从本地文件读取订阅内容。

### **2.3 decode_base64**
*   **Function**: `decode_base64(content: str) -> str`
*   **Description**: 
    1. 自动检测内容是否为 Base64 编码。
    2. 修复非标准 Padding (`=`)。
    3. 支持 URL-safe Base64 (`-_`) 和标准 Base64 (`+/`)。

## **3. Core Logic (核心逻辑)**
1.  **Detection**: 优先尝试 UTF-8 解码，失败或检测到 Base64 特征后进行解码。
2.  **Normalization**: 统一替换 URL-safe 字符，补全 padding。
3.  **Resilience**: 捕获所有解码异常，确保尽可能返回可读文本。
