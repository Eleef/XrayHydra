/**
 * Main Application Logic for Xray-Prism
 * Handles UI interactions and state management
 */

class App {
    constructor() {
        // State
        this.subscriptions = [];
        this.currentSubscription = null;
        this.nodes = [];
        this.selectedNodeIds = new Set();
        this.proxies = [];
        this.xrayStatus = 'stopped';

        // DOM Elements
        this.elements = {
            xrayStatus: document.getElementById('xray-status'),
            btnToggleXray: document.getElementById('btn-toggle-xray'),
            btnAddSubscription: document.getElementById('btn-add-subscription'),
            subscriptionList: document.getElementById('subscription-list'),
            nodesContainer: document.getElementById('nodes-container'),
            nodesCount: document.getElementById('nodes-count'),
            nodeSearch: document.getElementById('node-search'),
            btnSelectAll: document.getElementById('btn-select-all'),
            btnAddToProxy: document.getElementById('btn-add-to-proxy'),
            proxiesContainer: document.getElementById('proxies-container'),
            proxiesCount: document.getElementById('proxies-count'),
            btnTestAll: document.getElementById('btn-test-all'),
            btnClearProxies: document.getElementById('btn-clear-proxies'),
            modalAddSubscription: document.getElementById('modal-add-subscription'),
            subName: document.getElementById('sub-name'),
            subUrl: document.getElementById('sub-url'),
            btnConfirmAdd: document.getElementById('btn-confirm-add'),
        };

        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        this.bindEvents();
        await this.loadInitialData();

        // Auto-refresh status every 5 seconds
        setInterval(() => this.updateSystemStatus(), 5000);
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Header
        this.elements.btnToggleXray.addEventListener('click', () => this.toggleXray());

        // Subscription
        this.elements.btnAddSubscription.addEventListener('click', () => this.openAddSubscriptionModal());
        this.elements.subscriptionList.addEventListener('click', (e) => this.handleSubscriptionClick(e));

        // Nodes
        this.elements.nodeSearch.addEventListener('input', (e) => this.filterNodes(e.target.value));
        this.elements.btnSelectAll.addEventListener('click', () => this.toggleSelectAll());
        this.elements.btnAddToProxy.addEventListener('click', () => this.addSelectedToProxy());
        this.elements.nodesContainer.addEventListener('click', (e) => this.handleNodeClick(e));
        this.elements.nodesContainer.addEventListener('change', (e) => this.handleNodeCheckbox(e));

        // Proxies
        this.elements.btnTestAll.addEventListener('click', () => this.testAllProxies());
        this.elements.btnClearProxies.addEventListener('click', () => this.clearAllProxies());
        this.elements.proxiesContainer.addEventListener('click', (e) => this.handleProxyClick(e));

        // Modal
        this.elements.btnConfirmAdd.addEventListener('click', () => this.confirmAddSubscription());
        document.querySelectorAll('[data-close-modal]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });
        this.elements.modalAddSubscription.addEventListener('click', (e) => {
            if (e.target === this.elements.modalAddSubscription) {
                this.closeModals();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModals();
        });
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            // Load subscriptions
            await this.loadSubscriptions();

            // Load proxies
            await this.loadProxies();

            // Update system status
            await this.updateSystemStatus();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            Components.showToast('加载数据失败', 'error');
        }
    }

    // ==================== Subscriptions ====================

    /**
     * Load and render subscriptions
     */
    async loadSubscriptions() {
        try {
            const data = await api.getSubscriptions();
            this.subscriptions = data.subscriptions || [];
            this.renderSubscriptions();
        } catch (error) {
            console.error('Failed to load subscriptions:', error);
            this.elements.subscriptionList.innerHTML = `
                <div class="empty-state">
                    <p>加载订阅失败</p>
                </div>
            `;
        }
    }

    /**
     * Render subscriptions list
     */
    renderSubscriptions() {
        if (this.subscriptions.length === 0) {
            this.elements.subscriptionList.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                    </svg>
                    <p>暂无订阅</p>
                    <span class="hint">点击上方"添加"按钮添加订阅</span>
                </div>
            `;
            return;
        }

        this.elements.subscriptionList.innerHTML = '';
        this.subscriptions.forEach(sub => {
            const isActive = this.currentSubscription?.id === sub.id;
            const item = Components.subscriptionItem(sub, isActive);
            this.elements.subscriptionList.appendChild(item);
        });
    }

    /**
     * Handle subscription item click
     */
    async handleSubscriptionClick(e) {
        const item = e.target.closest('.subscription-item');
        if (!item) return;

        const action = e.target.closest('[data-action]')?.dataset.action;
        const subId = item.dataset.id;

        if (action === 'refresh') {
            await this.refreshSubscription(subId);
        } else if (action === 'delete') {
            await this.deleteSubscription(subId);
        } else {
            await this.selectSubscription(subId);
        }
    }

    /**
     * Select a subscription and load its nodes
     */
    async selectSubscription(subId) {
        const sub = this.subscriptions.find(s => s.id === subId);
        if (!sub) return;

        this.currentSubscription = sub;
        this.selectedNodeIds.clear();
        this.updateAddToProxyButton();

        // Update UI
        document.querySelectorAll('.subscription-item').forEach(el => {
            el.classList.toggle('active', el.dataset.id === subId);
        });

        // Load nodes
        await this.loadNodes(subId);
    }

    /**
     * Refresh a subscription
     */
    async refreshSubscription(subId) {
        try {
            Components.showToast('正在刷新订阅...', 'info');
            const result = await api.refreshSubscription(subId);

            // Update local data
            const index = this.subscriptions.findIndex(s => s.id === subId);
            if (index !== -1) {
                this.subscriptions[index] = result;
            }

            this.renderSubscriptions();

            // Reload nodes if this is the current subscription
            if (this.currentSubscription?.id === subId) {
                await this.loadNodes(subId);
            }

            Components.showToast(`刷新成功，共 ${result.node_count} 个节点`, 'success');
        } catch (error) {
            Components.showToast(`刷新失败: ${error.message}`, 'error');
        }
    }

    /**
     * Delete a subscription
     */
    async deleteSubscription(subId) {
        if (!confirm('确定要删除这个订阅吗？')) return;

        try {
            await api.deleteSubscription(subId);
            this.subscriptions = this.subscriptions.filter(s => s.id !== subId);

            if (this.currentSubscription?.id === subId) {
                this.currentSubscription = null;
                this.nodes = [];
                this.renderNodes();
            }

            this.renderSubscriptions();
            Components.showToast('订阅已删除', 'success');
        } catch (error) {
            Components.showToast(`删除失败: ${error.message}`, 'error');
        }
    }

    /**
     * Open add subscription modal
     */
    openAddSubscriptionModal() {
        this.elements.subName.value = '';
        this.elements.subUrl.value = '';
        this.elements.modalAddSubscription.classList.add('active');
        this.elements.subName.focus();
    }

    /**
     * Close all modals
     */
    closeModals() {
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.classList.remove('active');
        });
    }

    /**
     * Confirm adding a new subscription
     */
    async confirmAddSubscription() {
        const name = this.elements.subName.value.trim();
        const url = this.elements.subUrl.value.trim();

        if (!name || !url) {
            Components.showToast('请填写完整信息', 'warning');
            return;
        }

        // Show loading state
        const btnText = this.elements.btnConfirmAdd.querySelector('.btn-text');
        const btnLoading = this.elements.btnConfirmAdd.querySelector('.btn-loading');
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');
        this.elements.btnConfirmAdd.disabled = true;

        try {
            const result = await api.createSubscription(name, url);
            this.subscriptions.push(result);
            this.renderSubscriptions();
            this.closeModals();
            Components.showToast(`添加成功，共 ${result.node_count} 个节点`, 'success');

            // Auto-select the new subscription
            await this.selectSubscription(result.id);
        } catch (error) {
            Components.showToast(`添加失败: ${error.message}`, 'error');
        } finally {
            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
            this.elements.btnConfirmAdd.disabled = false;
        }
    }

    // ==================== Nodes ====================

    /**
     * Load nodes for a subscription
     */
    async loadNodes(subId) {
        this.elements.nodesContainer.innerHTML = `
            <div class="loading-placeholder">
                <div class="spinner"></div>
                <span>加载节点中...</span>
            </div>
        `;

        try {
            const data = await api.getSubscriptionNodes(subId);
            this.nodes = data.nodes || [];
            this.renderNodes();
        } catch (error) {
            this.elements.nodesContainer.innerHTML = `
                <div class="empty-state">
                    <p>加载节点失败</p>
                </div>
            `;
        }
    }

    /**
     * Render nodes list
     */
    renderNodes(filteredNodes = null) {
        const nodesToRender = filteredNodes || this.nodes;
        this.elements.nodesCount.textContent = nodesToRender.length;

        if (nodesToRender.length === 0) {
            this.elements.nodesContainer.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="7" height="7"></rect>
                        <rect x="14" y="3" width="7" height="7"></rect>
                        <rect x="14" y="14" width="7" height="7"></rect>
                        <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    <p>${this.currentSubscription ? '没有找到节点' : '请先选择一个订阅'}</p>
                </div>
            `;
            return;
        }

        this.elements.nodesContainer.innerHTML = '';
        nodesToRender.forEach(node => {
            const isSelected = this.selectedNodeIds.has(node.id);
            const item = Components.nodeItem(node, isSelected);
            this.elements.nodesContainer.appendChild(item);
        });
    }

    /**
     * Filter nodes by search query
     */
    filterNodes(query) {
        if (!query) {
            this.renderNodes();
            return;
        }

        const lowerQuery = query.toLowerCase();
        const filtered = this.nodes.filter(node =>
            node.name.toLowerCase().includes(lowerQuery) ||
            node.address.toLowerCase().includes(lowerQuery) ||
            node.protocol.toLowerCase().includes(lowerQuery)
        );
        this.renderNodes(filtered);
    }

    /**
     * Handle node item click
     */
    handleNodeClick(e) {
        const item = e.target.closest('.node-item');
        if (!item) return;

        // Don't toggle if clicking on checkbox directly
        if (e.target.classList.contains('node-checkbox')) return;

        const checkbox = item.querySelector('.node-checkbox');
        checkbox.checked = !checkbox.checked;
        this.handleNodeCheckbox({ target: checkbox });
    }

    /**
     * Handle node checkbox change
     */
    handleNodeCheckbox(e) {
        const checkbox = e.target;
        if (!checkbox.classList.contains('node-checkbox')) return;

        const item = checkbox.closest('.node-item');
        const nodeId = item.dataset.id;

        if (checkbox.checked) {
            this.selectedNodeIds.add(nodeId);
            item.classList.add('selected');
        } else {
            this.selectedNodeIds.delete(nodeId);
            item.classList.remove('selected');
        }

        this.updateAddToProxyButton();
    }

    /**
     * Toggle select all nodes
     */
    toggleSelectAll() {
        const allSelected = this.selectedNodeIds.size === this.nodes.length;

        if (allSelected) {
            // Deselect all
            this.selectedNodeIds.clear();
        } else {
            // Select all
            this.nodes.forEach(node => this.selectedNodeIds.add(node.id));
        }

        // Update UI
        document.querySelectorAll('.node-item').forEach(item => {
            const checkbox = item.querySelector('.node-checkbox');
            const isSelected = this.selectedNodeIds.has(item.dataset.id);
            checkbox.checked = isSelected;
            item.classList.toggle('selected', isSelected);
        });

        this.updateAddToProxyButton();
    }

    /**
     * Update add to proxy button state
     */
    updateAddToProxyButton() {
        const count = this.selectedNodeIds.size;
        this.elements.btnAddToProxy.disabled = count === 0;
        this.elements.btnAddToProxy.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14"></path>
                <path d="m12 5 7 7-7 7"></path>
            </svg>
            添加到代理${count > 0 ? ` (${count})` : ''}
        `;
    }

    /**
     * Add selected nodes to proxy list
     */
    async addSelectedToProxy() {
        if (this.selectedNodeIds.size === 0) return;

        try {
            const nodeIds = Array.from(this.selectedNodeIds);
            await api.addProxies(nodeIds);

            this.selectedNodeIds.clear();
            this.renderNodes();
            this.updateAddToProxyButton();

            await this.loadProxies();
            Components.showToast(`已添加 ${nodeIds.length} 个节点到代理列表`, 'success');
        } catch (error) {
            Components.showToast(`添加失败: ${error.message}`, 'error');
        }
    }

    // ==================== Proxies ====================

    /**
     * Load and render proxies
     */
    async loadProxies() {
        try {
            const data = await api.getProxies();
            this.proxies = data.proxies || [];
            this.xrayStatus = data.xray_status || 'stopped';
            this.renderProxies();
            this.updateXrayStatus();
        } catch (error) {
            console.error('Failed to load proxies:', error);
        }
    }

    /**
     * Render proxies list
     */
    renderProxies() {
        this.elements.proxiesCount.textContent = this.proxies.length;
        this.elements.btnTestAll.disabled = this.proxies.length === 0 || this.xrayStatus !== 'running';
        this.elements.btnClearProxies.disabled = this.proxies.length === 0;

        if (this.proxies.length === 0) {
            this.elements.proxiesContainer.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"></path>
                    </svg>
                    <p>暂无活跃代理</p>
                    <span class="hint">从节点列表中选择节点并添加到代理</span>
                </div>
            `;
            return;
        }

        this.elements.proxiesContainer.innerHTML = '';
        this.proxies.forEach(proxy => {
            const item = Components.proxyItem(proxy);
            this.elements.proxiesContainer.appendChild(item);
        });
    }

    /**
     * Handle proxy item click
     */
    async handleProxyClick(e) {
        const item = e.target.closest('.proxy-item');
        if (!item) return;

        const action = e.target.closest('[data-action]')?.dataset.action;
        const port = parseInt(item.dataset.port);

        if (action === 'copy') {
            await this.copyProxyAddress(port);
        } else if (action === 'test') {
            await this.testSingleProxy(port);
        } else if (action === 'remove') {
            await this.removeProxy(port);
        }
    }

    /**
     * Copy proxy address to clipboard
     */
    async copyProxyAddress(port) {
        const address = `http://127.0.0.1:${port}`;
        try {
            await navigator.clipboard.writeText(address);
            Components.showToast(`已复制: ${address}`, 'success');
        } catch (error) {
            Components.showToast('复制失败', 'error');
        }
    }

    /**
     * Test a single proxy
     */
    async testSingleProxy(port) {
        if (this.xrayStatus !== 'running') {
            Components.showToast('请先启动 Xray', 'warning');
            return;
        }

        try {
            Components.showToast('正在测试...', 'info');
            const result = await api.testProxy(port);
            await this.loadProxies();

            if (result.status === 'success') {
                Components.showToast(`测试成功: ${result.latency_ms}ms`, 'success');
            } else {
                Components.showToast(`测试失败: ${result.error || '连接超时'}`, 'error');
            }
        } catch (error) {
            Components.showToast(`测试失败: ${error.message}`, 'error');
        }
    }

    /**
     * Remove a proxy
     */
    async removeProxy(port) {
        try {
            await api.removeProxy(port);
            await this.loadProxies();
            Components.showToast('代理已移除', 'success');
        } catch (error) {
            Components.showToast(`移除失败: ${error.message}`, 'error');
        }
    }

    /**
     * Test all proxies
     */
    async testAllProxies() {
        if (this.xrayStatus !== 'running') {
            Components.showToast('请先启动 Xray', 'warning');
            return;
        }

        this.elements.btnTestAll.disabled = true;
        this.elements.btnTestAll.innerHTML = `
            <div class="spinner-sm"></div>
            测试中...
        `;

        try {
            const result = await api.testAllProxies();
            await this.loadProxies();
            Components.showToast(
                `测试完成: ${result.success_count} 成功, ${result.failed_count} 失败`,
                result.failed_count === 0 ? 'success' : 'warning'
            );
        } catch (error) {
            Components.showToast(`测试失败: ${error.message}`, 'error');
        } finally {
            this.elements.btnTestAll.disabled = false;
            this.elements.btnTestAll.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                测试全部
            `;
        }
    }

    /**
     * Clear all proxies
     */
    async clearAllProxies() {
        if (!confirm('确定要清除所有代理吗？')) return;

        try {
            await api.clearProxies();
            await this.loadProxies();
            Components.showToast('已清除所有代理', 'success');
        } catch (error) {
            Components.showToast(`清除失败: ${error.message}`, 'error');
        }
    }

    // ==================== System ====================

    /**
     * Update system status display
     */
    async updateSystemStatus() {
        try {
            const status = await api.getSystemStatus();
            this.xrayStatus = status.xray_status || 'stopped';
            this.updateXrayStatus();
        } catch (error) {
            console.error('Failed to get system status:', error);
        }
    }

    /**
     * Update Xray status display
     */
    updateXrayStatus() {
        const statusDot = this.elements.xrayStatus.querySelector('.status-dot');
        const statusText = this.elements.xrayStatus.querySelector('.status-text');

        statusDot.className = `status-dot ${this.xrayStatus}`;

        const statusTexts = {
            running: '运行中',
            stopped: '已停止',
            starting: '启动中',
            error: '错误'
        };
        statusText.textContent = statusTexts[this.xrayStatus] || '未知';

        // Update toggle button icon
        const isRunning = this.xrayStatus === 'running';
        this.elements.btnToggleXray.innerHTML = isRunning ? `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
        ` : `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polygon points="10 8 16 12 10 16 10 8" fill="currentColor"></polygon>
            </svg>
        `;
        this.elements.btnToggleXray.title = isRunning ? '停止 Xray' : '启动 Xray';

        // Update test button state
        this.elements.btnTestAll.disabled = this.proxies.length === 0 || !isRunning;
    }

    /**
     * Toggle Xray on/off
     */
    async toggleXray() {
        const isRunning = this.xrayStatus === 'running';

        try {
            this.elements.btnToggleXray.disabled = true;

            if (isRunning) {
                const result = await api.stopXray();
                Components.showToast(result.message, result.success ? 'success' : 'error');
            } else {
                const result = await api.startXray();
                Components.showToast(result.message, result.success ? 'success' : 'error');
            }

            await this.loadProxies();
        } catch (error) {
            Components.showToast(`操作失败: ${error.message}`, 'error');
        } finally {
            this.elements.btnToggleXray.disabled = false;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
