# **Documentation Templates Library**

此文件是项目文档的唯一真理来源 (Single Source of Truth)。
AI Agent 在创建或重构文档时，必须严格遵循以下模板结构。

## **📋 1. Project Index (项目地图)**

文件路径: docs/00_project_index.md
用途: 核心入口，Agent 启动时必读。
```markdown

# **[Project Name] Context Map**

Last Updated: [YYYY-MM-DD]

## **1. Project Overview (项目简介)**

一句话清晰描述项目的核心价值和目标用户。

## **2. Documentation Navigation (文档导航)**

Agent 请注意：在回答问题前，优先通过此索引定位详细文档。

### **📘 Product & Requirements (产品)**

* **[Requirements] (product/requirements.md)**: 当前生效的 PRD 和功能列表。 
* **[Domain Terms] (product/domain_terms.md)**: 业务术语表 (专有名词解释)。

### **🏗️ Technical Architecture (技术)**

* **[Architecture] (tech/architecture.md)**: 系统设计、技术栈与拓扑图。
* **[API Specs] (tech/api_specs.md)**: 关键接口约定。
* **[Database] (tech/database.md)**: 数据库模型与设计。

### **🛠️ Guides & Norms (规范与指南)**

* **[Development] (guide/development.md)**: ⚡ 开发环境搭建与常用命令。
* **[Conventions] (guide/conventions.md)**: 📏 代码风格与命名规范。
* **[Testing] (guide/testing.md)**: 🧪 测试策略与覆盖率要求。

### **🚦 Development Status (状态)**

* **[Active Task] (dev_status/active_task.md)**: 🚧 当前正在进行的上下文 (实时更新)。  
* **[Todo List] (dev_status/todo.md)**: 💡 待办事项与积压的灵感 (Backlog)。  
* **[History Log] (dev_status/history_log.md)**: 📜 已完成任务流水账。

## **3. Key Environment Variables (关键环境)**

* ENV_TYPE: (dev/prod)
* (列出其他关键开关，不要包含真实密钥)
```

## **🚧 2. Active Task Context (当前任务状态)**

文件路径: docs/dev_status/active_task.md
用途: 记录“存档点”，保证对话中断后能无缝恢复。
```markdown

# **Active Task Context (Live State)**

Last Updated: [YYYY-MM-DD HH:MM]

## **🎯 Current Objective (当前目标)**

一句话描述当前正在解决的核心问题。

## **🧩 Context Dump (关键上下文)**

极其重要：列出解决此问题必须关注的文件和变量。

* **相关文件**: src/xxx.py, docs/xxx.md
* **最近修改**: 修改了函数 X 的逻辑...

## **🚧 Progress Checklist (进度)**

* [x] 已完成步骤 A  
* [ ] 正在进行步骤 B <-- **Current Focus**
* [ ] 待执行步骤 C

## **💥 Known Issues / Blockers (遇到的阻碍)**

如果有报错，必须在此粘贴关键 Error Log 和 Stack Trace。

* **Error**: ...
* **Attempted**: 尝试了方案 A，但失败了，原因是...

## **⏭️ Next Actions (下一步计划)**

1. 具体动作 1
2. 具体动作 2
```

## **📄 3. Product Requirement (PRD)**

文件路径: docs/product/requirements.md (或子功能文档)
命名建议: 保持语义化，不带编号。
```markdown

# **[Feature Name] Product Requirements**

Last Updated: [YYYY-MM-DD]

## **1. Background & Value (背景与价值)**

* **User Story**: 作为 [角色]，我想要 [动作]，以便于 [价值]。
* **Priority**: P0 (Critical) / P1 (Important) / P2 (Nice to have)

## **2. Functional Requirements (功能需求)**

| ID | Feature Point | Description | Acceptance Criteria |
| :---- | :---- | :---- | :---- |
| F1 | 登录验证 | 支持 JWT 校验 | Token 过期需返回 401 |
| F2 | ... | ... | ... |

## **3. Edge Cases (边界情况)**

* 网络异常时的表现？
* 数据为空时的 UI 状态？

## **4. UI/UX Reference (交互)**

* (可选) 描述页面跳转逻辑或引用设计图链接。
```

## **⚙️ 4. Technical Design (技术设计)**

文件路径: docs/tech/designs/xxx_design.md 或 docs/tech/architecture.md
命名建议: 保持语义化，不带编号。
```markdown

# **[Module Name] Technical Design**

Last Updated: [YYYY-MM-DD]

## **1. Overview (概述)**

简述该模块的技术职责。

## **2. Data Flow (数据流向)**

graph LR
    A[Client] --> B[Service] --> C[DB]

## **3. Data Structures (数据结构)**

* **Table**: table_name
  * col1: Type (Description)

## **4. Interface Design (接口设计)**

* **Function**: process_data(input: Dict) -> bool
* API: POST /api/v1/submit
```

## **🐛 5. Issue / Bug Report**

文件路径: docs/issues/YYYY-MM-DD-issue-name.md
命名建议: 使用 日期前缀 以便排序。
```markdown

# **Issue: [简短描述错误现象]**

Date: [YYYY-MM-DD]

## **1. Environment (环境)**

* OS: Windows/Linux/Mac
* Version: v1.2.0

## **2. Symptom (现象)**

描述发生了什么，预期应该发生什么。

## **3. Reproduction Steps (复现步骤)**

1. Go to page X
2. Click button Y

## **4. Root Cause Analysis (原因分析)**

(由 Agent 填写) 经过排查，发现是 ... 导致的。

## **5. Resolution (解决方案)**

* [ ] 修复代码 A
* [ ] 增加测试用例 B
```

## **🏛️ 6. ADR (Architecture Decision Record)**

文件路径: docs/adr/001-title.md
命名建议: 必须使用 递增编号 (001, 002...)。
```markdown

# **ADR-[编号]: [简短标题]**

Date: [YYYY-MM-DD]

## **Status**

[Draft / Accepted / Deprecated]

## **Context (背景)**

我们在面临什么问题？有哪些选项？(e.g., 选择 Redis 还是 Memcached)

## **Decision (决策)**

我们决定使用 [方案 X]。

## **Consequences (后果)**

* **Positive**: 性能提升，生态更好。
* Negative: 运维成本增加，内存占用更高。
```

## **🛠️ 7. Development Manual (开发手册)**

**文件路径**: docs/guide/development.md

```markdown

# **Development Guide (开发指南)**

Last Updated: [YYYY-MM-DD]

## **1. Quick Start Commands (常用命令)**

AI 请注意：执行任务时优先使用以下命令。

* **Start Server**: npm run dev
* **Run Tests**: npm test (or pytest)
* **Lint/Format**: npm run lint
* **DB Migration**: npm run migrate

## **2. Environment Variables (环境变量)**

| Variable | Required | Description | Example |
| :---- | :---- | :---- | :---- |
| DB_URL | Yes | Postgres 连接字符串 | postgres://... |
| API_KEY | No | 第三方服务密钥 | sk-123... |

## **3. Deployment Flow (部署流程)**

* main 分支自动部署到 Production 环境。
* Docker 构建命令: docker build -t app .
```

## **📏 8. Coding Conventions (代码规范)**

**文件路径**: docs/guide/conventions.md

```markdown

# **Coding Standards (代码规范)**

## **1. Naming Conventions (命名规范)**

* **Files**: snake_case.py / kebab-case.ts
* **Classes**: PascalCase
* **Variables/Functions**: snake_case (Python) / camelCase (JS/TS)
* **Constants**: UPPER_CASE

## **2. Architecture Patterns (架构模式)**

* 数据库访问层请使用 **Repository Pattern**。
* Controller 层不应包含业务逻辑，请将其移动到 Service 层。

## **3. Error Handling (错误处理)**

* 必须使用定义在 src/errors/ 中的自定义异常类 (Custom Exception)。
* 严禁捕获通用的 Exception 而不进行重新抛出 (re-raise) 或记录日志。

## **4. Tech Constraints (技术限制)**

* **Libraries**: 优先使用 dayjs 而非 moment。
* Async: 必须使用 async/await，避免使用 .then() 链式调用。
```

## **🧪 9. Testing Strategy (测试策略)**

**文件路径**: docs/guide/testing.md

```markdown

# **Testing Strategy (测试策略)**

## **1. Test Stack (测试技术栈)**

* Framework: pytest / jest
* Mocking: unittest.mock / jest.mock

## **2. Testing Rules (测试规则)**

* **Unit Tests**: 必须覆盖所有 Service 方法。Mock 所有数据库调用。
* **Integration Tests**: 使用测试数据库 (Test DB) 测试 API 端点。
* **Coverage Goal**: 目标覆盖率 > 80%

## **3. Fixtures & Factories**

* 使用 factories/user_factory.py 生成测试用户数据。
* 禁止在测试中硬编码 ID。
```