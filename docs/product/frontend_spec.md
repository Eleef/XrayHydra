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

## **3. Tech Stack (技术栈)**
*   **HTML5 / CSS3 (Grid Layout)**
*   **Vanilla JavaScript (ES6+)**
*   **No Build Tool Required**: 直接由 FastAPI 静态服务托管。
