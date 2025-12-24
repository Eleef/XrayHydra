/**
 * UI Components for Xray-Prism
 * Reusable component rendering functions
 */

const Components = {
    /**
     * Create a subscription item element
     * @param {object} subscription - Subscription data
     * @param {boolean} isActive - Whether this subscription is selected
     * @returns {HTMLElement}
     */
    subscriptionItem(subscription, isActive = false) {
        const div = document.createElement('div');
        div.className = `subscription-item${isActive ? ' active' : ''}`;
        div.dataset.id = subscription.id;

        const lastUpdated = subscription.last_updated
            ? new Date(subscription.last_updated).toLocaleDateString('zh-CN')
            : '未更新';

        div.innerHTML = `
            <div class="subscription-info">
                <span class="subscription-name">${this.escapeHtml(subscription.name)}</span>
                <div class="subscription-meta">
                    <span>${subscription.node_count} 节点</span>
                    <span>•</span>
                    <span>${lastUpdated}</span>
                </div>
            </div>
            <div class="subscription-actions">
                <button class="btn btn-icon btn-sm" data-action="refresh" title="刷新">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6"></path>
                        <path d="M1 20v-6h6"></path>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="delete" title="删除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        return div;
    },

    /**
     * Create a node item element
     * @param {object} node - Node data
     * @param {boolean} isSelected - Whether this node is selected
     * @returns {HTMLElement}
     */
    nodeItem(node, isSelected = false) {
        const div = document.createElement('div');
        div.className = `node-item${isSelected ? ' selected' : ''}`;
        div.dataset.id = node.id;

        const statusIcon = this.getStatusIcon(node.test_status);
        const statusText = this.getStatusText(node.test_status, node.latency_ms);

        div.innerHTML = `
            <input type="checkbox" class="node-checkbox" ${isSelected ? 'checked' : ''}>
            <div class="node-info">
                <span class="node-name">${this.escapeHtml(node.name)}</span>
                <div class="node-details">
                    <span class="node-protocol">${node.protocol}</span>
                    <span>${this.escapeHtml(node.address)}:${node.port}</span>
                </div>
            </div>
            <div class="node-status ${node.test_status}">
                ${statusIcon}
                <span>${statusText}</span>
            </div>
        `;

        return div;
    },

    /**
     * Create a proxy item element
     * @param {object} proxy - Proxy data
     * @returns {HTMLElement}
     */
    proxyItem(proxy) {
        const div = document.createElement('div');
        div.className = 'proxy-item';
        div.dataset.port = proxy.port;

        const latencyClass = this.getLatencyClass(proxy.latency_ms);
        const latencyText = proxy.latency_ms ? `${proxy.latency_ms}ms` : '--';
        const ipText = proxy.exit_ip || '--';

        div.innerHTML = `
            <div class="proxy-port">
                <span>:</span>${proxy.port}
            </div>
            <div class="proxy-info">
                <span class="proxy-name">${this.escapeHtml(proxy.node_name)}</span>
                <div class="proxy-meta">
                    <span class="node-protocol">${proxy.protocol}</span>
                    ${proxy.exit_ip ? `<span class="proxy-ip">${ipText}</span>` : ''}
                    ${proxy.latency_ms ? `<span class="proxy-latency ${latencyClass}">${latencyText}</span>` : ''}
                </div>
            </div>
            <div class="proxy-actions">
                <button class="btn btn-icon btn-sm" data-action="copy" title="复制代理地址">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="test" title="测试">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="remove" title="移除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;

        return div;
    },

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in milliseconds
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
            error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
            warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
            info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Get status icon HTML
     * @param {string} status - Test status
     * @returns {string} SVG icon HTML
     */
    getStatusIcon(status) {
        const icons = {
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
            failed: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
            testing: '<svg class="spinner-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle></svg>',
            pending: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
        };
        return icons[status] || icons.pending;
    },

    /**
     * Get status text
     * @param {string} status - Test status
     * @param {number|null} latencyMs - Latency in milliseconds
     * @returns {string}
     */
    getStatusText(status, latencyMs) {
        if (status === 'success' && latencyMs) {
            return `${latencyMs}ms`;
        }
        const texts = {
            success: '可用',
            failed: '失败',
            testing: '测试中',
            pending: '未测试'
        };
        return texts[status] || '未知';
    },

    /**
     * Get latency class for styling
     * @param {number|null} latencyMs - Latency in milliseconds
     * @returns {string}
     */
    getLatencyClass(latencyMs) {
        if (!latencyMs) return '';
        if (latencyMs < 300) return 'fast';
        if (latencyMs < 800) return 'medium';
        return 'slow';
    },

    /**
     * Escape HTML special characters
     * @param {string} str - String to escape
     * @returns {string}
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
