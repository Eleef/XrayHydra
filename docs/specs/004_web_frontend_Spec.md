# Phase 2: Web 前端开发计划

> 文档创建时间：2025-12-24
> 状态：待实施

## 1. 功能需求

### 1.1 订阅管理
- 添加订阅链接（支持多个订阅）
- 删除订阅
- 刷新订阅（重新获取节点）
- 显示每个订阅的节点数量

### 1.2 节点列表
- 显示每个订阅的节点列表
- 节点信息：名称、协议、地址、端口、状态
- 节点搜索/过滤

### 1.3 代理端口管理
- 将节点加入到代理列表（分配本地端口）
- 从代理列表移除节点
- 查看当前活跃的代理端口
- 启动/停止 Xray 服务

### 1.4 测试功能
- 测试单个节点/全部节点
- 显示延迟和出口 IP
- 实时状态更新

---

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────────────────────────────────────────────┐
│                    Web Frontend                          │
│   (HTML + CSS + JavaScript / 可选: React/Vue)           │
└─────────────────────────────────────────────────────────┘
                           │
                           │ HTTP REST API
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend API                           │
│   (Python FastAPI / Flask)                              │
└─────────────────────────────────────────────────────────┘
                           │
                           │ 调用
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Xray-Prism Core Modules                    │
│   (fetcher, parser, generator, runner, tester)          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术选型建议

**后端 API**:
- **推荐**: FastAPI（异步支持、自动生成 OpenAPI 文档）
- **备选**: Flask（更简单，足够满足需求）

**前端**:
- **简单方案**: 原生 HTML + CSS + JavaScript（无需构建）
- **复杂方案**: Vue.js / React（如需更复杂交互）

**数据存储**:
- **简单方案**: JSON 文件（`data/subscriptions.json`）
- **复杂方案**: SQLite（如需更多功能）

---

## 3. 新增目录结构

```
d:\project\XrayHydra\
├── main.py                    # CLI 入口（保留）
├── server.py                  # [新增] Web 服务入口
├── requirements.txt           # 更新依赖
│
├── src/xray_prism/            # 核心模块（已存在）
│   ├── __init__.py
│   ├── models.py
│   ├── fetcher.py
│   ├── parser.py
│   ├── generator.py
│   ├── runner.py
│   └── tester.py
│
├── api/                       # [新增] Backend API 层
│   ├── __init__.py
│   ├── main.py               # FastAPI 应用入口
│   ├── routes/               # API 路由
│   │   ├── __init__.py
│   │   ├── subscriptions.py  # 订阅管理 API
│   │   ├── nodes.py          # 节点管理 API
│   │   ├── proxies.py        # 代理端口 API
│   │   └── system.py         # 系统控制 API (启动/停止 Xray)
│   ├── schemas/              # Pydantic 数据模型
│   │   ├── __init__.py
│   │   └── models.py
│   └── services/             # 业务逻辑层
│       ├── __init__.py
│       ├── subscription_service.py
│       ├── node_service.py
│       └── proxy_service.py
│
├── web/                       # [新增] 前端静态文件
│   ├── index.html            # 主页面
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js            # API 调用封装
│   │   ├── app.js            # 主逻辑
│   │   └── components.js     # UI 组件
│   └── assets/
│       └── logo.svg
│
├── data/                      # [新增] 数据存储
│   ├── subscriptions.json    # 订阅列表
│   └── active_proxies.json   # 当前活跃代理
│
└── docs/
    ├── PROJECT_STATUS.md
    ├── PHASE2_PLAN.md        # 本文档
    └── specs/
        └── API_SPEC.md       # [新增] API 规格文档
```

---

## 4. API 设计

### 4.1 订阅管理

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/api/subscriptions` | 获取所有订阅列表 |
| POST | `/api/subscriptions` | 添加新订阅 |
| DELETE | `/api/subscriptions/{id}` | 删除订阅 |
| POST | `/api/subscriptions/{id}/refresh` | 刷新订阅节点 |

**请求示例** (POST /api/subscriptions):
```json
{
  "name": "我的订阅",
  "url": "https://example.com/subscribe"
}
```

**响应示例**:
```json
{
  "id": "sub_001",
  "name": "我的订阅",
  "url": "https://example.com/subscribe",
  "node_count": 39,
  "last_updated": "2025-12-24T15:00:00"
}
```

### 4.2 节点管理

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/api/subscriptions/{id}/nodes` | 获取订阅的节点列表 |
| GET | `/api/nodes/{node_id}` | 获取单个节点详情 |
| POST | `/api/nodes/{node_id}/test` | 测试单个节点 |

### 4.3 代理端口管理

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/api/proxies` | 获取当前活跃代理列表 |
| POST | `/api/proxies` | 添加节点到代理列表 |
| DELETE | `/api/proxies/{port}` | 移除代理端口 |
| POST | `/api/proxies/test-all` | 测试所有代理端口 |

**请求示例** (POST /api/proxies):
```json
{
  "node_ids": ["node_001", "node_002"],
  "start_port": 10000
}
```

### 4.4 系统控制

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/api/system/status` | 获取 Xray 运行状态 |
| POST | `/api/system/start` | 启动 Xray |
| POST | `/api/system/stop` | 停止 Xray |
| POST | `/api/system/restart` | 重启 Xray |

---

## 5. 实施步骤

### Step 1: 环境准备
1. 安装 FastAPI 和 uvicorn
2. 创建目录结构
3. 配置 CORS

### Step 2: 后端 API 开发
1. 创建 FastAPI 应用
2. 实现订阅管理 API
3. 实现节点管理 API
4. 实现代理端口 API
5. 实现系统控制 API
6. 添加静态文件服务

### Step 3: 前端开发
1. 创建基础 HTML 框架
2. 设计 CSS 样式（现代、美观）
3. 实现订阅管理页面
4. 实现节点列表页面
5. 实现代理管理页面
6. 添加实时状态更新

### Step 4: 集成测试
1. API 端到端测试
2. 前后端联调
3. 错误处理和边界情况

### Step 5: 优化和文档
1. 性能优化
2. 用户体验优化
3. 更新文档

---

## 6. 依赖更新

**新增依赖** (requirements.txt):
```
# 现有
requests>=2.28.0
pyyaml>=6.0

# 新增
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
```

---

## 7. 启动方式

**开发模式**:
```bash
# 启动后端 API（带热重载）
uvicorn api.main:app --reload --port 8000

# 或使用简化脚本
python server.py
```

**访问地址**:
- 前端页面: `http://localhost:8000/`
- API 文档: `http://localhost:8000/docs`

---

## 8. 前端界面草图

```
┌─────────────────────────────────────────────────────────────────┐
│ 🌐 Xray-Prism                            [Xray: 运行中 🟢]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📋 订阅管理                              [+ 添加订阅]          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔗 我的订阅 1        39 节点    2025-12-24   [刷新] [删除]│   │
│  │ 🔗 我的订阅 2        25 节点    2025-12-23   [刷新] [删除]│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📡 节点列表 (我的订阅 1)                 [全选] [测试选中]      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☑ 🇭🇰 香港 01    trojan   xxx.com   12001   ✅ 500ms   │   │
│  │ ☑ 🇭🇰 香港 02    trojan   xxx.com   12002   ✅ 600ms   │   │
│  │ ☐ 🇯🇵 日本 01    trojan   xxx.com   12003   ⏳ 测试中  │   │
│  │ ...                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                     [添加到代理列表 →]          │
│                                                                 │
│  🚀 活跃代理                              [停止全部]            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ :10000 → 🇭🇰 香港 01    156.226.172.223    [复制] [移除]│   │
│  │ :10001 → 🇭🇰 香港 02    141.11.91.159      [复制] [移除]│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 注意事项

1. **状态管理**: 需要妥善管理 Xray 进程状态，避免僵尸进程
2. **并发控制**: 防止同时启动多个 Xray 实例
3. **错误处理**: API 需要返回明确的错误信息
4. **安全性**: 考虑 API 访问控制（本地使用可简化）
5. **前端美观**: 使用现代 CSS 设计，参考 Clash Verge 等

---

## 10. 下一步行动

当准备开始实施时，请执行：

```
请开始实施 Phase 2 Web 前端开发，按照 docs/PHASE2_PLAN.md 的步骤执行。
```
