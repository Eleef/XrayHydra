# **Web Frontend Requirements**

> **Moved from**: `docs/specs/004_web_frontend_Spec.md`
> **Last Updated**: 2026-03-07

## **1. UI Layout (界面布局)**

采用 **三栏并排** 的现代化布局，确保信息密度适中且操作直观。

*   **Left (Subscriptions)**: 宽度固定 (260px)。展示订阅列表、节点总数、最后更新时间。
*   **Center (Nodes)**: 相对较窄，约占中右两栏的 1/3。展示选中订阅的所有节点，支持搜索过滤。
*   **Right (Proxies / Leases)**: 相对较宽，约占中右两栏的 2/3。展示当前映射的本地端口、workspace 代理状态、租约监控与调试工具。

## **2. Functional Flows (功能流程)**

### **2.1 Subscription Management**
*   **Add**: 弹出 Modal 输入 URL 和名称。
*   **Refresh**: 调用 API 重新获取节点，不影响现有代理。

### **2.2 Proxy Activation**
*   **Select**: 在中间栏勾选一个或多个节点。
*   **Add to Proxy**: 自动分配下一个可用端口（Starting from 10000）。
*   **Visual Feedback**: 右侧栏立即出现新代理卡片。

### **2.3 Health Visualization**
每个代理卡片均有脉冲指示器：
*   🟢 **Green**: Healthy
*   🟡 **Yellow**: Degraded
*   ⚪ **Gray**: Disabled (Penalty mode)

## **3. Proxy Lease Management UI (Phase 3)**
> 目标：提供 Lease API 的可视化监控与调试能力。建议入口：Active Proxies 栏顶部 Tab 切换。

### **3.1 Workspace Header (当前 Workspace 头部)**
*   位于右侧代理面板顶部，作用于 `Proxies` 和 `Leases` 两个 Tab。
*   只展示“已有活跃租约或冷却记录”的 workspace。
*   默认恢复浏览器上次选择的 workspace；如果记录不存在，则回退到当前列表中的第一个。
*   当没有任何 workspace 时，显示空态并禁用依赖 workspace 的手动管理动作。

### **3.2 Global Dashboard (统计看板)**
*   **Metrics**:
    *   当前可用代理数 (Available)
    *   当前活跃租约数 (Active Leases)
    *   当前冷却数 (Cooldowns)
*   看板保持全局统计；下方列表则切换为“当前 workspace 视图”。

### **3.3 Active Leases Monitor (租约监控)**
*   **List View**: Proxy Port | Lease ID | TTL Countdown
*   **Scope**: 仅显示当前 workspace 的活跃租约。
*   **Out of Scope**: 本阶段不提供强制释放活跃租约。

### **3.4 Cooldown Pool (冷却池)**
*   **List View**: Proxy Port | Cooldown Source (`manual` / `timed`) | Cooldown Timer
*   **Scope**: 仅显示当前 workspace 的冷却记录。
*   **Behavior**:
    *   `manual`: 不自动过期，只能通过手动召回结束。
    *   `timed`: 保留原有倒计时冷却语义，可等待到期，也可手动召回提前结束。

### **3.5 Proxy List Manual Management (代理栏手动管理)**
*   在 `Proxies` Tab 中，所有代理都基于“当前 workspace”展示状态：
    *   **可用**: 可点击“冷却”。
    *   **冷却中**: 可点击“召回”。
    *   **已租约中**: 不允许冷却，也不提供强制释放。
*   手动管理仅作用于 `workspace + proxy_port` 维度，不影响其他 workspace 对同一代理的使用。

### **3.6 Lease Playground (调试器)**
*   提供一个简易表单，允许开发者在 UI 上模拟 API 调用：
    *   输入: `Workspace ID`, `TTL`
    *   操作: `Acquire`, `Release (with cooldown)`
    *   反馈: 实时显示 API 响应结果 (JSON)。

## **4. Tech Stack (技术栈)**
*   **HTML5 / CSS3 (Grid Layout)**
*   **Vanilla JavaScript (ES6+)**
*   **No Build Tool Required**: 直接由 FastAPI 静态服务托管。
