/**
 * UI Components for Xray-Prism
 * Reusable component rendering functions
 */

const Components = {
    /**
     * Create a group item element
     * @param {object} group - Group data
     * @param {boolean} isActive - Whether this group is selected
     * @returns {HTMLElement}
     */
    groupItem(group, isActive = false) {
        const div = document.createElement('div');
        div.className = `subscription-item${isActive ? ' active' : ''}`;
        div.dataset.id = group.id;
        const groupType = group.group_type || 'subscription';
        div.dataset.groupType = groupType;

        const updatedAt = groupType === 'custom'
            ? (group.updated_at || group.created_at)
            : group.last_updated;
        const lastUpdated = updatedAt
            ? new Date(updatedAt).toLocaleDateString('zh-CN')
            : '未更新';
        const groupTypeLabel = groupType === 'custom' ? '自定义' : '订阅';
        const showRefresh = groupType === 'subscription';
        const showImport = groupType === 'custom';
        const showRename = groupType === 'custom';
        const deleteTitle = groupType === 'custom' ? '删除分组' : '删除订阅';

        div.innerHTML = `
            <div class="subscription-info">
                <span class="subscription-name">
                    ${this.escapeHtml(group.name)}
                    <span class="group-type-badge ${groupType === 'custom' ? 'custom' : 'subscription'}">${groupTypeLabel}</span>
                </span>
                <div class="subscription-meta">
                    <span>${group.node_count} 节点</span>
                    <span>•</span>
                    <span>${lastUpdated}</span>
                </div>
            </div>
            <div class="subscription-actions">
                <button class="btn btn-icon btn-sm" data-action="refresh" title="刷新" ${showRefresh ? '' : 'style="display:none"'}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6"></path>
                        <path d="M1 20v-6h6"></path>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="import" title="导入" ${showImport ? '' : 'style="display:none"'}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 4v12"></path>
                        <polyline points="8 12 12 16 16 12"></polyline>
                        <path d="M4 20h16"></path>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="rename" title="重命名" ${showRename ? '' : 'style="display:none"'}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm" data-action="delete" title="${deleteTitle}">
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
     * @param {object} options - Rendering options
     * @returns {HTMLElement}
     */
    nodeItem(node, isSelected = false, options = {}) {
        const div = document.createElement('div');
        const inProxyPool = Boolean(node.in_proxy_pool);
        const runtimeUnsupported = node?.runtime_supported === false;
        const runtimeSupportReason = node?.runtime_support_reason || '当前运行环境不支持此协议';
        const disableNodeCheckbox = Boolean(options.disableNodeCheckbox || inProxyPool || runtimeUnsupported);
        const disableTestButton = Boolean(options.disableTestButton || runtimeUnsupported);
        const disableCopyToGroup = Boolean(options.disableCopyToGroup || runtimeUnsupported);
        const showRemoveFromGroup = Boolean(options.showRemoveFromGroup);
        const disableRemoveFromGroup = Boolean(options.disableRemoveFromGroup);
        div.className = `node-item${isSelected ? ' selected' : ''}${inProxyPool ? ' in-proxy-pool' : ''}${runtimeUnsupported ? ' unsupported-protocol' : ''}`;
        div.dataset.id = node.id;

        const statusIcon = this.getStatusIcon(node.test_status);
        const statusText = this.getStatusText(node.test_status, node.latency_ms);
        const diagnostics = this.getNodeDiagnostics(node, {
            runtimeUnsupported,
            runtimeSupportReason,
        });
        const pooledTag = inProxyPool
            ? `<span class="node-pool-tag">已入池${node.proxy_port ? ` :${node.proxy_port}` : ''}</span>`
            : '';
        const unsupportedTag = runtimeUnsupported
            ? `<span class="node-unsupported-tag" title="${this.escapeHtml(runtimeSupportReason)}">不兼容</span>`
            : '';

        div.innerHTML = `
            <input type="checkbox" class="node-checkbox" ${isSelected ? 'checked' : ''} ${disableNodeCheckbox ? 'disabled' : ''}>
            <div class="node-info">
                <span class="node-name">${this.escapeHtml(node.name)}</span>
                <div class="node-details">
                    <span class="node-protocol">${node.protocol}</span>
                    <span>${this.escapeHtml(node.address)}:${node.port}</span>
                    ${pooledTag}
                    ${unsupportedTag}
                </div>
                ${diagnostics}
            </div>
            <div class="node-item-side">
                <div class="node-status ${node.test_status}">
                    ${statusIcon}
                    <span>${statusText}</span>
                </div>
                <button class="btn btn-icon btn-sm node-test-btn" data-node-action="test" title="${runtimeUnsupported ? this.escapeHtml(runtimeSupportReason) : '测试节点'}" ${disableTestButton ? 'disabled' : ''}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </button>
                <button class="btn btn-icon btn-sm node-copy-btn" data-node-action="copy-to-group" title="${runtimeUnsupported ? this.escapeHtml(runtimeSupportReason) : '复制到分组'}" ${disableCopyToGroup ? 'disabled' : ''}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="8" y="8" width="10" height="10" rx="2"></rect>
                        <path d="M5 7V4a2 2 0 0 1 2-2h7"></path>
                        <polyline points="9 8 9 4 13 4"></polyline>
                    </svg>
                </button>
                ${showRemoveFromGroup ? `
                <button class="btn btn-icon btn-sm node-remove-btn" data-node-action="remove-from-group" title="移出分组" ${disableRemoveFromGroup ? 'disabled' : ''}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
                ` : ''}
            </div>
        `;

        return div;
    },

    /**
     * Backward compatible alias for legacy callsites
     * @param {object} subscription
     * @param {boolean} isActive
     * @returns {HTMLElement}
     */
    subscriptionItem(subscription, isActive = false) {
        return this.groupItem(subscription, isActive);
    },

    /**
     * Create a proxy item element
     * @param {object} proxy - Proxy data
     * @returns {HTMLElement}
     */
    proxyItem(proxy, workspaceState = null) {
        const div = document.createElement('div');
        div.className = 'proxy-item';
        div.dataset.port = proxy.port;

        const latencyClass = this.getLatencyClass(proxy.latency_ms);
        const latencyText = proxy.latency_ms ? `${proxy.latency_ms}ms` : '--';
        const ipText = proxy.exit_ip ? `出口IP ${proxy.exit_ip}` : '出口IP --';
        const state = workspaceState || {
            stateClass: 'unscoped',
            stateLabel: '未选择 workspace',
            sourceLabel: '',
            note: '请选择一个已有 workspace 后再做手动管理。',
            canCopy: true,
            canTest: true,
            canCooldown: false,
            canRecall: false,
            copyTitle: '复制代理地址',
            testTitle: '测试',
            cooldownTitle: '手动冷却',
            recallTitle: '召回冷却',
        };

        div.innerHTML = `
            <div class="proxy-item-main">
                <div class="proxy-port">
                    <span>:</span>${proxy.port}
                </div>
                <div class="proxy-info">
                    <span class="proxy-name">${this.escapeHtml(proxy.node_name)}</span>
                    <div class="proxy-meta">
                        <span class="node-protocol">${proxy.protocol}</span>
                        <span class="proxy-ip">${this.escapeHtml(ipText)}</span>
                        ${proxy.latency_ms ? `<span class="proxy-latency ${latencyClass}">${latencyText}</span>` : ''}
                    </div>
                    <span class="proxy-workspace-note">${this.escapeHtml(state.note || '')}</span>
                    ${this.renderProxyLeaseMetrics(state.metrics, {
                        workspaceLabel: state.metricsWorkspaceLabel,
                        showWorkspaceLabel: Boolean(state.showMetricsWorkspaceLabel),
                    })}
                </div>
            </div>
            <div class="proxy-item-side">
                <span class="proxy-state ${state.stateClass}">
                    <span>${this.escapeHtml(state.stateLabel)}</span>
                    ${state.sourceLabel ? `<span class="proxy-state-source">${this.escapeHtml(state.sourceLabel)}</span>` : ''}
                </span>
                <div class="proxy-actions">
                    <button class="btn btn-icon btn-sm" data-action="copy" title="${this.escapeHtml(state.copyTitle || '复制代理地址')}" ${state.canCopy === false ? 'disabled' : ''}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-sm" data-action="test" title="${this.escapeHtml(state.testTitle || '测试')}" ${state.canTest === false ? 'disabled' : ''}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-sm" data-action="cooldown" title="${this.escapeHtml(state.cooldownTitle || '手动冷却')}" ${state.canCooldown ? '' : 'disabled'}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-sm" data-action="recall" title="${this.escapeHtml(state.recallTitle || '召回冷却')}" ${state.canRecall ? '' : 'disabled'}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 12a9 9 0 1 1-2.64-6.36"></path>
                            <polyline points="21 3 21 9 15 9"></polyline>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-sm" data-action="remove" title="移除">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        return div;
    },

    renderProxyLeaseMetrics(metrics, options = {}) {
        if (!metrics) return '';
        const usageCount = Number(metrics?.usage_count ?? 0);
        const successCount = Number(metrics?.success_count ?? 0);
        const failureCount = Number(metrics?.failure_count ?? 0);
        const workspaceLabel = options.workspaceLabel ? this.escapeHtml(options.workspaceLabel) : '';

        return `
            <div class="proxy-lease-metrics">
                ${options.showWorkspaceLabel && workspaceLabel ? `<span class="proxy-metric-scope">${workspaceLabel}</span>` : ''}
                <span class="lease-metric usage">用 ${usageCount}</span>
                <span class="lease-metric success">成 ${successCount}</span>
                <span class="lease-metric failure">败 ${failureCount}</span>
            </div>
        `;
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
        if (status === 'success' && latencyMs !== null && latencyMs !== undefined) {
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

    getNodeDiagnostics(node, options = {}) {
        const status = node?.test_status || 'pending';
        const successfulTarget = node?.successful_target || node?.test_target || node?.target_hit || null;
        const testedTarget = node?.tested_target || node?.last_test_target || null;
        const failureReason = node?.test_error || node?.error || node?.error_message || null;
        const connectivityStatus = node?.connectivity_status || (status === 'success' ? 'success' : 'failed');
        const successfulTargetCount = Number(node?.successful_target_count || 0);
        const testedTargets = Array.isArray(node?.tested_targets) ? node.tested_targets : [];
        const exitInfoComplete = node?.exit_info_complete !== false;
        const runtimeUnsupported = Boolean(options.runtimeUnsupported);
        const runtimeSupportReason = options.runtimeSupportReason || '当前运行环境不支持此协议';

        const rows = [];
        if (runtimeUnsupported) {
            rows.push(`
                <div class="node-diagnostic unsupported">
                    <span class="node-diagnostic-label">不可用原因</span>
                    <span class="node-diagnostic-value">${this.escapeHtml(runtimeSupportReason)}</span>
                </div>
            `);
        }
        if (status === 'success' && successfulTarget) {
            rows.push(`
                <div class="node-diagnostic success">
                    <span class="node-diagnostic-label">命中目标</span>
                    <span class="node-diagnostic-value">${this.escapeHtml(successfulTarget)}</span>
                </div>
            `);
        }
        const connectivityTargetCount = testedTargets.filter((target) =>
            target.includes('generate_204') || target.includes('cp.cloudflare.com')
        ).length || 3;
        if (status !== 'pending') {
            rows.push(`
                <div class="node-diagnostic neutral">
                    <span class="node-diagnostic-label">连通</span>
                    <span class="node-diagnostic-value">${this.escapeHtml(connectivityStatus)} / ${successfulTargetCount}/${connectivityTargetCount}</span>
                </div>
            `);
        }
        if (status === 'success' && !exitInfoComplete) {
            rows.push(`
                <div class="node-diagnostic neutral">
                    <span class="node-diagnostic-label">出口</span>
                    <span class="node-diagnostic-value">未完整识别</span>
                </div>
            `);
        }

        if (status === 'failed') {
            if (failureReason) {
                rows.push(`
                    <div class="node-diagnostic failed">
                        <span class="node-diagnostic-label">失败原因</span>
                        <span class="node-diagnostic-value">${this.escapeHtml(failureReason)}</span>
                    </div>
                `);
            }
            if (testedTarget) {
                rows.push(`
                    <div class="node-diagnostic neutral">
                        <span class="node-diagnostic-label">最后目标</span>
                        <span class="node-diagnostic-value">${this.escapeHtml(testedTarget)}</span>
                    </div>
                `);
            }
        }

        if (rows.length === 0) {
            return '';
        }

        return `<div class="node-diagnostics">${rows.join('')}</div>`;
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
