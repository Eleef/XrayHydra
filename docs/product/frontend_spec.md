# **Web Frontend Requirements**

> **Moved from**: `docs/specs/004_web_frontend_Spec.md`
> **Last Updated**: 2026-01-02

## **1. UI Layout (界面布局)**

采用 **三栏并排** 的现代化布局，确保信息密度适中且操作直观。

*   **Left (Subscriptions)**: 宽度固定 (260px)。展示订阅列表、节点总数、最后更新时间。
*   **Center (Nodes)**: 自适应宽度。展示选中订阅的所有节点，支持搜索过滤。
*   **Right (Active Proxies)**: 自适应宽度。展示当前映射的本地端口、健康状态、出口 IP。

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

### **3.1 Global Dashboard (统计看板)**
*   **Metrics**: 
    *   资源池水位 (Available / Total Healthy)
    *   当前活跃租约数 (Active Leases)
    *   当前冷却中数 (Cooldowns)
    *   Top Workspaces 排行

### **3.2 Active Leases Monitor (租约监控)**
*   **List View**: Workspace | Proxy Port | TTL Countdown | Actions
*   **Actions**:
    *   **Force Release**: 管理员强制终止租约。

### **3.3 Cooldown Pool (冷却池)**
*   **List View**: Proxy Port | Source Workspace | Cooldown Timer | Actions
*   **Actions**:
    *   **Reset Now**: 强制清除冷却状态，立即恢复可用。

### **3.4 Lease Playground (调试器)**
*   提供一个简易表单，允许开发者在 UI 上模拟 API 调用：
    *   输入: `Workspace ID`, `TTL`
    *   操作: `Acquire`, `Release (with cooldown)`
    *   反馈: 实时显示 API 响应结果 (JSON)。

## **4. Tech Stack (技术栈)**
*   **HTML5 / CSS3 (Grid Layout)**
*   **Vanilla JavaScript (ES6+)**
*   **No Build Tool Required**: 直接由 FastAPI 静态服务托管。
