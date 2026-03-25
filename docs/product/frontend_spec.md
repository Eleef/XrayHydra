# **Web Frontend Requirements**

> **Moved from**: `docs/specs/004_web_frontend_Spec.md`
> **Last Updated**: 2026-03-21

## **1. UI Layout (界面布局)**

采用 **三栏并排** 的现代化布局，确保信息密度适中且操作直观。

*   **Left (Node Groups)**: 宽度固定 (260px)。统一展示 `订阅组` 和 `自定义组`，显示节点总数、最近更新时间与类型徽标。
*   **Center (Nodes)**: 相对较窄，约占中右两栏的 1/3。展示选中节点组的所有节点，支持搜索过滤、批量测试、复制到自定义组。
*   **Right (Proxies / Leases)**: 相对较宽，约占中右两栏的 2/3。展示当前映射的本地端口、workspace 代理状态、租约监控与调试工具。

## **2. Functional Flows (功能流程)**

### **2.1 Group Management**
*   **Entry**: 左侧统一称为 `节点组`，顶部入口为 `新建节点组`。
*   **Subscription Group**:
    *   通过 Modal 输入 URL 和名称创建。
    *   支持刷新，不影响现有代理。
*   **Custom Group**:
    *   支持创建空分组，或在创建时直接粘贴多行节点链接导入。
    *   已有自定义组卡片提供 `导入`、`重命名`、`删除` 操作，均使用应用内弹窗，不再使用浏览器原生 `prompt()` / `confirm()`。
    *   支持重命名、删除整组、删除组内单节点。
    *   节点采用连接快照，不依赖原订阅节点继续存在。

### **2.2 Node Selection & Activation (先测后加)**
*   **Auto Mark Pooled Nodes**:
    *   已加入代理池的节点在中栏自动勾选。
    *   该勾选项为禁用态，不可取消。
    *   节点行显示 `已入池` 与对应端口（例如 `:10022`）。
*   **Manual Select**: 用户仅可操作“未入池”节点的勾选状态。
*   **Exclude Keywords (排除关键词)**:
    *   节点栏新增“排除关键词”输入框/标签区域，用户可以输入 `香港`、`Hong Kong`、`Hongkong` 等关键词，系统会在搜索之前过滤掉匹配 `node.name` 或 `node.address` 的节点（大小写不敏感）。
    *   支持用逗号或换行分隔多个关键词，并以可删除标签方式展示当前的排除列表。
    *   排除关键词只保存关键词列表到浏览器 `localStorage`（例如 `xray-prism.nodeExclusionKeywords`），并不会持久化勾选状态、测试状态或排序；刷新页面后关键字依旧生效。
    *   每个关键词标签后会附带括号内的匹配数量（例如 `Hong Kong (5)`），数量实时体现当前展示节点集中会被过滤掉的条目数，并在节点刷新或关键词更新时自动重新计算，帮助用户判断关键词的影响范围。
*   **Add to Proxy**: “添加”只提交“未入池且当前勾选”的节点，自动分配下一个可用端口（Starting from 10000）。
*   **Visual Feedback**: 添加成功后，右侧代理卡片立即出现，中栏节点同步切换为“已入池 + 禁用勾选”。
*   **Copy to Group**:
    *   节点工具栏新增 `加入到分组` 按钮，对当前筛选结果内、当前显式勾选的可操作节点生效。
    *   已入池或勾选禁用的节点，仍可通过节点行内的 `复制到分组` 按钮单独复制到自定义组。
    *   用户可以选择已有自定义组，或在弹窗中直接输入新分组名称后复制。
    *   自定义组内按连接语义去重；跨组允许重复。

### **2.3 Node Testing (单节点 / 批量)**
*   **Single Node Test**: 每个节点行提供测试按钮，用于即时验证该节点连通性。
*   **Batch Test Controls**: 节点栏顶部提供：
    *   `测试选中`
    *   `测试全部`
*   **Multi-Target Strategy**:
    *   默认采用 `multi_target`。
    *   对同一节点按“主目标 + 备选目标”顺序测试。
    *   任一目标成功即判定该节点可用；全部失败才判定失败。
*   **Progress Bar Feedback**:
    *   批量/单节点测试展示进度条，工具栏的总进度条显示待测节点总数以及已完成的项，行级进度条追踪单个节点尝试的目标序列。
    *   前端先调用 `POST /api/nodes/test-jobs` 创建测试任务，再轮询 `GET /api/nodes/test-jobs/{job_id}` 获取真实进度。任务响应会提供 `status`、`progress_percent`、`active_target`、`target_index`、`target_total`、`current_target_completed`、`current_target_total`、`success_count`、`failed_count` 等字段，驱动工具栏进度条和状态文案。
    *   任务执行中，工具栏显示“当前目标探测进度 + 已确认成功/失败数”；任务完成后再收敛到最终成功/失败统计，不再依赖前端模拟推进。
*   **Post-Test Selection**:
    *   批量测试后，成功且未入池节点自动勾选。
    *   失败节点保持未勾选，用户可继续筛选或重试。
    *   已入池节点始终保持“自动勾选 + 禁用”。

### **2.4 Health Visualization**
每个代理卡片均有脉冲指示器：
*   🟢 **Green**: Healthy
*   🟡 **Yellow**: Degraded
*   ⚪ **Gray**: Disabled (Penalty mode)

### **2.5 Proxy Pool Manual Dedupe (代理池手动去重)**
*   **Manual Trigger**: 代理栏工具区提供 `出口IP去重` 按钮，仅在当前代理池存在重复出口 IP 时启用，并在按钮文本后显示建议禁用数量（例如 `出口IP去重 (51)`）。
*   **Preview Before Apply**:
*   点击按钮后弹出确认弹窗，不直接改动代理池。
*   弹窗按 `exit_ip` 分组展示重复项，并明确列出每组中的 `保留` 代理和 `禁用` 代理。
*   保留规则优先参考测试结果与延迟：优先保留 `test_status = success` 的代理，再比较更低 `latency_ms`，最后以更小端口号兜底。
*   **Confirm Apply**:
*   用户点击 `确认去重` 后，系统只会把弹窗中列出的重复代理标记为 `去重禁用`，不会直接删除，也不会重新测试或自动补新节点。
*   被禁用的代理仍保留在代理池中，因此节点栏依旧显示它们“已入池”，避免用户后续重复加入；但这些代理不会进入 Xray 运行配置，也不会参与租约、健康测试或“测试全部”。
*   去重完成后，右侧代理卡片、顶部统计和按钮计数立即刷新。

## **3. Proxy Lease Management UI (Phase 3)**
> 目标：提供 Lease API 的可视化监控与调试能力。建议入口：Active Proxies 栏顶部 Tab 切换。

### **3.1 Scope Header (当前范围头部)**
*   位于右侧代理面板顶部，作用于 `Proxies` 和 `Leases` 两个 Tab。
*   选择器固定包含一个伪选项：`所有代理`。
*   除 `所有代理` 外，只展示“已有活跃租约或冷却记录”的 workspace。
*   默认恢复浏览器上次选择的 workspace；如果记录不存在，则回退到 `所有代理`。
*   即使没有任何 workspace 被激活，`所有代理` 视图下也允许执行“测试全部”和全局冷却。
*   `所有代理` 视图下禁用“复位 workspace”这类仅适用于具体 workspace 的动作。
*   具体 workspace 视图下提供 `复位 workspace` 按钮；执行时先确认是否清空活跃租约与冷却，再额外确认是否一并清空该 workspace 的租约统计。

### **3.2 Global Dashboard (统计看板)**
*   **Metrics**:
    *   当前可用代理数 (Available)
    *   当前活跃租约数 (Active Leases)
    *   当前冷却数 (Cooldowns)
*   看板保持全局统计；下方列表则切换为“当前 workspace 视图”。

### **3.3 Active Leases Monitor (租约监控)**
*   **List View**: Proxy Port | Lease ID | TTL Countdown
*   **Scope**:
    *   具体 workspace 视图：仅显示该 workspace 的活跃租约。
    *   `所有代理` 视图：显示全部活跃租约，并额外标出所属 workspace。
*   **Lease Metrics**:
    *   每条活跃租约在副信息区显示三项小号统计：`用 N`、`成 N`、`败 N`。
    *   三项统计按 `workspace + proxy_port` 维度记录，其中“用”为中性色，“成”为绿色，“败”为红色。
*   **Out of Scope**: 本阶段不提供强制释放活跃租约。

### **3.4 Cooldown Pool (冷却池)**
*   **List View**: Proxy Port | Cooldown Source (`manual` / `timed`) | Cooldown Timer
*   **Scope**:
    *   具体 workspace 视图：显示“当前 workspace 冷却 + 全局冷却”。
    *   `所有代理` 视图：显示全部冷却记录，并标出所属 workspace 或 `全局冷却`。
*   **Behavior**:
    *   `manual`: 不自动过期，只能通过手动召回结束。
    *   `timed`: 保留原有倒计时冷却语义，可等待到期，也可手动召回提前结束。
*   冷却池列表中的每一条记录都提供“召回”入口。
*   冷却池条目同样展示 `用 / 成 / 败` 三项统计，便于在召回前判断该代理在当前 workspace 下的使用表现。

### **3.5 Proxy List Manual Management (代理栏手动管理)**
*   在 `Proxies` Tab 中，所有代理都基于“当前 workspace”展示状态：
    *   **可用**: 可点击“冷却”。
    *   **冷却中**: 可点击“召回”。
    *   **已租约中**: 不允许冷却，也不提供强制释放。
*   手动管理仅作用于 `workspace + proxy_port` 维度，不影响其他 workspace 对同一代理的使用。
*   手动点击“测试全部”时，可选启用“失败后加入冷却池”：
    *   可对当前 workspace 生效；若当前选择为 `所有代理`，或当前没有激活 workspace，则改为全局冷却。
    *   测试开始时锁定目标范围，确认弹窗中必须明确展示所属 workspace 或 `所有代理（全局冷却）`。
    *   用户可配置“连续失败次数”和“冷却时间”，默认值分别为 2 次和 300 秒。
    *   测试结束后先弹出候选失败清单，用户确认后才批量加入定时冷却；取消则不做任何冷却变更。
*   `所有代理` 视图下，代理列表只允许召回全局冷却，不提供手动冷却按钮。

### **3.6 Lease Playground (调试器)**
*   提供一个简易表单，允许开发者在 UI 上模拟 API 调用：
    *   输入: `Workspace ID`, `TTL`
    *   操作: `Acquire`, `Release (with cooldown)`
    *   反馈: 实时显示 API 响应结果 (JSON)。

## **4. Tech Stack (技术栈)**
*   **HTML5 / CSS3 (Grid Layout)**
*   **Vanilla JavaScript (ES6+)**
*   **No Build Tool Required**: 直接由 FastAPI 静态服务托管。
