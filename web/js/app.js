/**
 * Main Application Logic for Xray-Prism
 * Handles UI interactions and state management
 */

const ALL_WORKSPACES_ID = '__all_workspaces__';
const GLOBAL_WORKSPACE_ID = '__global__';
const NODE_EXCLUSION_STORAGE_KEY = 'xray-prism.nodeExclusionKeywords';
const CURRENT_SUBSCRIPTION_STORAGE_KEY = 'xray-prism.currentSubscriptionId';
const CURRENT_GROUP_STORAGE_KEY = 'xray-prism.currentGroup';
const LEASE_PLAYGROUND_COLLAPSED_STORAGE_KEY = 'xray-prism.leasePlaygroundCollapsed';

class App {
    constructor() {
        // State
        this.subscriptions = [];
        this.customGroups = [];
        this.groups = [];
        this.currentSubscription = null;
        this.currentGroup = null;
        this.currentSubscriptionId = localStorage.getItem(CURRENT_SUBSCRIPTION_STORAGE_KEY) || null;
        this.currentGroupKey = localStorage.getItem(CURRENT_GROUP_STORAGE_KEY) || null;
        this.nodes = [];
        this.selectedNodeIds = new Set();
        this.isNodeTesting = false;
        this.nodeViewFilters = {
            onlyAvailable: false,
            onlyNotInPool: false,
            onlyFailed: false,
            sortBy: 'default',
        };
        this.nodeExcludeKeywords = this.loadNodeExclusionKeywords();
        this.nodeTestProgress = {
            active: false,
            total: 0,
            completed: 0,
            success: 0,
            failed: 0,
            percent: 0,
            actionLabel: '',
            note: '',
            statusText: '待开始',
            activeTarget: null,
            targetIndex: null,
            targetTotal: null,
            currentTargetCompleted: 0,
            currentTargetTotal: 0,
        };
        this.proxies = [];
        this.xrayStatus = 'stopped';
        this.healthStates = {};  // {port: healthState}
        this.healthConfig = null;
        this.currentTab = 'proxies';  // 'proxies' or 'leases'
        this.leaseRefreshInterval = null;
        this.leaseStatus = {
            active_leases: [],
            cooldowns: [],
            workspaces: [],
            total_active: 0,
            total_cooldowns: 0,
        };
        this.leaseStats = {
            proxies_by_usage: [],
        };
        this.currentWorkspaceId = localStorage.getItem('xray-prism.currentWorkspaceId') || null;
        this.isLeasePlaygroundCollapsed = localStorage.getItem(LEASE_PLAYGROUND_COLLAPSED_STORAGE_KEY) !== 'false';
        this.pendingTestCooldownReview = null;
        this.pendingExitIpDedupeReview = null;
        this.pendingCustomGroupTargetId = null;
        this.pendingCustomGroupTargetName = '';
        this.pendingCopyNodeIds = [];
        this.pendingRenameGroupId = null;
        this.pendingDeleteGroupId = null;
        this.pendingRemoveNodeId = null;

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
            btnTestSelectedNodes: document.getElementById('btn-test-selected-nodes'),
            btnTestAllNodes: document.getElementById('btn-test-all-nodes'),
            btnAddSuccessToProxy: document.getElementById('btn-add-success-to-proxy'),
            btnAddToGroup: document.getElementById('btn-add-to-group'),
            btnAddToProxy: document.getElementById('btn-add-to-proxy'),
            nodeFilterAvailable: document.getElementById('node-filter-available'),
            nodeFilterNotInPool: document.getElementById('node-filter-not-in-pool'),
            nodeFilterFailed: document.getElementById('node-filter-failed'),
            nodeSort: document.getElementById('node-sort'),
            nodeExclusionInput: document.getElementById('node-exclusion-input'),
            nodeExclusionAdd: document.getElementById('btn-node-exclusion-add'),
            nodeExclusionTags: document.getElementById('node-exclusion-tags'),
            nodeTestProgress: document.getElementById('node-test-progress'),
            nodeTestProgressTitle: document.getElementById('node-test-progress-title'),
            nodeTestProgressStatus: document.getElementById('node-test-progress-status'),
            nodeTestProgressCounter: document.getElementById('node-test-progress-counter'),
            nodeTestProgressFill: document.getElementById('node-test-progress-fill'),
            nodeTestProgressSuccess: document.getElementById('node-test-progress-success'),
            nodeTestProgressFailed: document.getElementById('node-test-progress-failed'),
            nodeTestProgressRate: document.getElementById('node-test-progress-rate'),
            nodeTestProgressMeta: document.getElementById('node-test-progress-meta'),
            proxiesContainer: document.getElementById('proxies-container'),
            proxiesCount: document.getElementById('proxies-count'),
            btnTestAll: document.getElementById('btn-test-all'),
            btnDedupeExitIp: document.getElementById('btn-dedupe-exit-ip'),
            btnClearProxies: document.getElementById('btn-clear-proxies'),
            testCooldownEnabled: document.getElementById('test-cooldown-enabled'),
            testCooldownAttempts: document.getElementById('test-cooldown-attempts'),
            testCooldownSeconds: document.getElementById('test-cooldown-seconds'),
            testCooldownHint: document.getElementById('test-cooldown-hint'),
            workspaceChipList: document.getElementById('workspace-chip-list'),
            currentWorkspaceName: document.getElementById('current-workspace-name'),
            workspaceBarHint: document.getElementById('workspace-bar-hint'),
            btnResetWorkspace: document.getElementById('btn-reset-workspace'),
            cooldownList: document.getElementById('cooldown-list'),
            leasePlayground: document.getElementById('lease-playground'),
            btnToggleLeasePlayground: document.getElementById('btn-toggle-lease-playground'),
            modalCreateGroupEntry: document.getElementById('modal-create-group-entry'),
            modalAddSubscription: document.getElementById('modal-add-subscription'),
            btnOpenAddSubscription: document.getElementById('btn-open-add-subscription'),
            btnOpenAddCustomGroup: document.getElementById('btn-open-add-custom-group'),
            modalAddCustomGroup: document.getElementById('modal-add-custom-group'),
            customGroupModalTitle: document.getElementById('custom-group-modal-title'),
            customGroupSubmitText: document.getElementById('custom-group-submit-text'),
            customGroupNameRow: document.getElementById('custom-group-name-row'),
            customGroupModeRow: document.getElementById('custom-group-mode-row'),
            customGroupName: document.getElementById('custom-group-name'),
            customGroupImportMode: document.getElementById('custom-group-import-mode'),
            customGroupContentWrap: document.getElementById('custom-group-content-wrap'),
            customGroupContent: document.getElementById('custom-group-content'),
            btnConfirmAddCustomGroup: document.getElementById('btn-confirm-add-custom-group'),
            customGroupTargetRow: document.getElementById('custom-group-target-row'),
            customGroupTargetName: document.getElementById('custom-group-target-name'),
            modalRenameCustomGroup: document.getElementById('modal-rename-custom-group'),
            renameCustomGroupName: document.getElementById('rename-custom-group-name'),
            btnConfirmRenameCustomGroup: document.getElementById('btn-confirm-rename-custom-group'),
            modalDeleteCustomGroup: document.getElementById('modal-delete-custom-group'),
            deleteCustomGroupName: document.getElementById('delete-custom-group-name'),
            btnConfirmDeleteCustomGroup: document.getElementById('btn-confirm-delete-custom-group'),
            modalRemoveNodeFromGroup: document.getElementById('modal-remove-node-from-group'),
            removeNodeName: document.getElementById('remove-node-name'),
            btnConfirmRemoveNodeFromGroup: document.getElementById('btn-confirm-remove-node-from-group'),
            modalCopyToGroup: document.getElementById('modal-copy-to-group'),
            copyGroupSelect: document.getElementById('copy-group-select'),
            copyGroupNewName: document.getElementById('copy-group-new-name'),
            btnConfirmCopyToGroup: document.getElementById('btn-confirm-copy-to-group'),
            modalTestCooldownReview: document.getElementById('modal-test-cooldown-review'),
            testCooldownReviewMeta: document.getElementById('test-cooldown-review-meta'),
            testCooldownReviewList: document.getElementById('test-cooldown-review-list'),
            btnConfirmTestCooldownReview: document.getElementById('btn-confirm-test-cooldown-review'),
            modalExitIpDedupeReview: document.getElementById('modal-exit-ip-dedupe-review'),
            exitIpDedupeReviewMeta: document.getElementById('exit-ip-dedupe-review-meta'),
            exitIpDedupeReviewList: document.getElementById('exit-ip-dedupe-review-list'),
            btnConfirmExitIpDedupe: document.getElementById('btn-confirm-exit-ip-dedupe'),
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
        this.renderNodeExclusionTags();
        await this.loadInitialData();

        // Auto-refresh status every 5 seconds
        setInterval(() => this.updateSystemStatus(), 5000);

        // Keep workspace/lease state fresh for both proxy and lease tabs
        setInterval(() => this.refreshLeaseData(), 5000);

        // Auto-refresh health status every 10 seconds
        setInterval(() => this.refreshHealthStatus(), 10000);
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Header
        this.elements.btnToggleXray.addEventListener('click', () => this.toggleXray());

        // Groups
        this.elements.btnAddSubscription.addEventListener('click', () => this.openCreateGroupEntryModal());
        this.elements.subscriptionList.addEventListener('click', (e) => this.handleSubscriptionClick(e));

        // Nodes
        this.elements.nodeSearch.addEventListener('input', (e) => this.filterNodes(e.target.value));
        this.elements.nodeFilterAvailable?.addEventListener('change', () => this.handleNodeFilterOrSortChange());
        this.elements.nodeFilterNotInPool?.addEventListener('change', () => this.handleNodeFilterOrSortChange());
        this.elements.nodeFilterFailed?.addEventListener('change', () => this.handleNodeFilterOrSortChange());
        this.elements.nodeSort?.addEventListener('change', () => this.handleNodeFilterOrSortChange());
        if (this.elements.nodeExclusionAdd) {
            this.elements.nodeExclusionAdd.addEventListener('click', () => this.addNodeExclusionKeywords());
        }
        if (this.elements.nodeExclusionInput) {
            this.elements.nodeExclusionInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.addNodeExclusionKeywords();
                }
            });
        }
        this.elements.nodeExclusionTags?.addEventListener('click', (e) => this.handleNodeExclusionTagClick(e));
        this.elements.btnSelectAll.addEventListener('click', () => this.toggleSelectAll());
        this.elements.btnTestSelectedNodes?.addEventListener('click', () => this.testSelectedNodes());
        this.elements.btnTestAllNodes?.addEventListener('click', () => this.testAllNodes());
        this.elements.btnAddSuccessToProxy?.addEventListener('click', () => this.addSuccessfulToProxy());
        this.elements.btnAddToGroup?.addEventListener('click', () => this.openCopyToGroupModal());
        this.elements.btnAddToProxy.addEventListener('click', () => this.addSelectedToProxy());
        this.elements.nodesContainer.addEventListener('click', (e) => this.handleNodeClick(e));
        this.elements.nodesContainer.addEventListener('change', (e) => this.handleNodeCheckbox(e));

        // Proxies
        this.elements.btnTestAll.addEventListener('click', () => this.testAllProxies());
        this.elements.btnDedupeExitIp?.addEventListener('click', () => this.previewExitIpDedupe());
        this.elements.btnClearProxies.addEventListener('click', () => this.clearAllProxies());
        this.elements.testCooldownEnabled?.addEventListener('change', () => this.updateTestCooldownControls());
        this.elements.proxiesContainer.addEventListener('click', (e) => this.handleProxyClick(e));
        this.elements.workspaceChipList?.addEventListener('click', (e) => this.handleWorkspaceChipClick(e));
        this.elements.cooldownList?.addEventListener('click', (e) => this.handleCooldownListClick(e));
        this.elements.proxiesContainer.addEventListener('contextmenu', (e) => {
            const item = e.target.closest('.proxy-item');
            if (item) {
                const port = parseInt(item.dataset.port);
                this.showProxyContextMenu(e, port);
            }
        });

        // Modal
        this.elements.btnConfirmAdd.addEventListener('click', () => this.confirmAddSubscription());
        this.elements.btnOpenAddSubscription?.addEventListener('click', () => this.openAddSubscriptionModal());
        this.elements.btnOpenAddCustomGroup?.addEventListener('click', () => this.openAddCustomGroupModal());
        this.elements.customGroupImportMode?.addEventListener('change', () => this.handleCustomGroupImportModeChange());
        this.elements.btnConfirmAddCustomGroup?.addEventListener('click', () => this.confirmAddCustomGroup());
        this.elements.btnConfirmCopyToGroup?.addEventListener('click', () => this.confirmCopyToGroup());
        this.elements.btnConfirmRenameCustomGroup?.addEventListener('click', () => this.confirmRenameCustomGroup());
        this.elements.btnConfirmDeleteCustomGroup?.addEventListener('click', () => this.confirmDeleteCustomGroup());
        this.elements.btnConfirmRemoveNodeFromGroup?.addEventListener('click', () => this.confirmRemoveNodeFromGroup());
        document.querySelectorAll('[data-close-modal]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });
        this.elements.modalCreateGroupEntry?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalCreateGroupEntry) {
                this.closeModals();
            }
        });
        this.elements.modalAddSubscription.addEventListener('click', (e) => {
            if (e.target === this.elements.modalAddSubscription) {
                this.closeModals();
            }
        });
        this.elements.modalAddCustomGroup?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalAddCustomGroup) {
                this.closeModals();
            }
        });
        this.elements.modalRenameCustomGroup?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalRenameCustomGroup) {
                this.closeModals();
            }
        });
        this.elements.modalDeleteCustomGroup?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalDeleteCustomGroup) {
                this.closeModals();
            }
        });
        this.elements.modalRemoveNodeFromGroup?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalRemoveNodeFromGroup) {
                this.closeModals();
            }
        });
        this.elements.modalCopyToGroup?.addEventListener('click', (e) => {
            if (e.target === this.elements.modalCopyToGroup) {
                this.closeModals();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModals();
        });

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.closest('.tab-btn').dataset.tab));
        });

        // Lease Playground
        const pgAcquire = document.getElementById('pg-acquire');
        const pgRelease = document.getElementById('pg-release');
        const btnRefreshLeases = document.getElementById('btn-refresh-leases');

        if (pgAcquire) pgAcquire.addEventListener('click', () => this.playgroundAcquire());
        if (pgRelease) pgRelease.addEventListener('click', () => this.playgroundRelease());
        if (btnRefreshLeases) btnRefreshLeases.addEventListener('click', () => this.refreshLeaseData());
        if (this.elements.btnToggleLeasePlayground) {
            this.elements.btnToggleLeasePlayground.addEventListener('click', () => this.toggleLeasePlayground());
        }
        if (this.elements.btnResetWorkspace) {
            this.elements.btnResetWorkspace.addEventListener('click', () => this.resetCurrentWorkspace());
        }
        if (this.elements.btnConfirmTestCooldownReview) {
            this.elements.btnConfirmTestCooldownReview.addEventListener('click', () => this.confirmTestCooldownReview());
        }
        if (this.elements.btnConfirmExitIpDedupe) {
            this.elements.btnConfirmExitIpDedupe.addEventListener('click', () => this.confirmExitIpDedupe());
        }
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            this.syncLeasePlaygroundState();
            // Load subscriptions
            await this.loadSubscriptions();

            // Load proxies
            await this.loadProxies();

            // Load workspace-aware lease status
            await this.refreshLeaseData();

            // Update system status
            await this.updateSystemStatus();

            // Load health status
            await this.refreshHealthStatus();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            Components.showToast('加载数据失败', 'error');
        }
    }

    // ==================== Groups ====================

    getGroupKey(groupType, id) {
        return `${groupType}:${id}`;
    }

    getGroupFromKey(groupKey) {
        if (!groupKey || typeof groupKey !== 'string') return null;
        const [groupType, id] = groupKey.split(':', 2);
        if (!groupType || !id) return null;
        return this.groups.find((item) => item.group_type === groupType && item.id === id) || null;
    }

    getGroupUpdatedAt(group) {
        if (!group) return '';
        return group.updated_at || group.last_updated || group.created_at || '';
    }

    async loadSubscriptions() {
        try {
            const [subscriptionData, customGroupData] = await Promise.all([
                api.getSubscriptions(),
                api.getCustomGroups(),
            ]);
            this.subscriptions = subscriptionData.subscriptions || [];
            this.customGroups = customGroupData.groups || [];
            this.groups = [
                ...this.subscriptions.map((item) => ({ ...item, group_type: 'subscription' })),
                ...this.customGroups.map((item) => ({ ...item, group_type: 'custom' })),
            ];
            this.groups.sort((a, b) => this.getGroupUpdatedAt(b).localeCompare(this.getGroupUpdatedAt(a)));
            this.renderSubscriptions();
            await this.restoreSubscriptionSelection();
        } catch (error) {
            console.error('Failed to load groups:', error);
            this.elements.subscriptionList.innerHTML = `
                <div class="empty-state">
                    <p>加载节点组失败</p>
                </div>
            `;
        }
    }

    renderSubscriptions() {
        if (this.groups.length === 0) {
            this.currentSubscription = null;
            this.currentSubscriptionId = null;
            this.currentGroup = null;
            this.currentGroupKey = null;
            localStorage.removeItem(CURRENT_SUBSCRIPTION_STORAGE_KEY);
            localStorage.removeItem(CURRENT_GROUP_STORAGE_KEY);
            this.elements.subscriptionList.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                    </svg>
                    <p>暂无节点组</p>
                    <span class="hint">点击上方 + 新建订阅组或自定义组</span>
                </div>
            `;
            return;
        }

        this.elements.subscriptionList.innerHTML = '';
        this.groups.forEach((group) => {
            const isActive = this.currentGroup?.id === group.id && this.currentGroup?.group_type === group.group_type;
            const item = Components.groupItem(group, isActive);
            this.elements.subscriptionList.appendChild(item);
        });
    }

    async restoreSubscriptionSelection() {
        if (this.groups.length === 0) return;

        const preferredFromGroup = this.getGroupFromKey(this.currentGroupKey);
        const preferredFromLegacy = this.subscriptions.find((sub) => sub.id === this.currentSubscriptionId)
            ? this.groups.find((item) => item.group_type === 'subscription' && item.id === this.currentSubscriptionId)
            : null;
        const preferred = preferredFromGroup || preferredFromLegacy || this.groups[0];
        if (preferred) {
            await this.selectGroup(preferred.group_type, preferred.id);
        }
    }

    async handleSubscriptionClick(e) {
        const item = e.target.closest('.subscription-item');
        if (!item) return;

        const action = e.target.closest('[data-action]')?.dataset.action;
        const groupId = item.dataset.id;
        const groupType = item.dataset.groupType || 'subscription';
        const group = this.groups.find((entry) => entry.group_type === groupType && entry.id === groupId);

        if (action === 'refresh' && groupType === 'subscription') {
            await this.refreshSubscription(groupId);
            return;
        }
        if (action === 'import' && groupType === 'custom' && group) {
            this.openCustomGroupModal({ targetGroupId: groupId, targetGroupName: group.name });
            return;
        }
        if (action === 'rename' && groupType === 'custom') {
            this.openRenameCustomGroupModal(groupId);
            return;
        }
        if (action === 'delete') {
            if (groupType === 'custom') {
                this.openDeleteCustomGroupModal(groupId);
            } else {
                await this.deleteSubscription(groupId);
            }
            return;
        }
        await this.selectGroup(groupType, groupId);
    }

    async selectGroup(groupType, groupId) {
        const group = this.groups.find((item) => item.group_type === groupType && item.id === groupId);
        if (!group) return;

        this.currentGroup = group;
        this.currentGroupKey = this.getGroupKey(groupType, groupId);
        localStorage.setItem(CURRENT_GROUP_STORAGE_KEY, this.currentGroupKey);
        if (groupType === 'subscription') {
            this.currentSubscription = this.subscriptions.find((item) => item.id === groupId) || null;
            this.currentSubscriptionId = groupId;
            localStorage.setItem(CURRENT_SUBSCRIPTION_STORAGE_KEY, groupId);
        } else {
            this.currentSubscription = null;
            this.currentSubscriptionId = null;
            localStorage.removeItem(CURRENT_SUBSCRIPTION_STORAGE_KEY);
        }
        this.selectedNodeIds.clear();
        this.updateAddToProxyButton();

        document.querySelectorAll('.subscription-item').forEach((el) => {
            el.classList.toggle(
                'active',
                el.dataset.id === groupId && (el.dataset.groupType || 'subscription') === groupType
            );
        });

        await this.loadNodes(groupId, groupType);
    }

    async selectSubscription(subId) {
        await this.selectGroup('subscription', subId);
    }

    async refreshSubscription(subId) {
        try {
            Components.showToast('正在刷新订阅组...', 'info');
            const result = await api.refreshSubscription(subId);
            const index = this.subscriptions.findIndex((item) => item.id === subId);
            if (index !== -1) {
                this.subscriptions[index] = result;
            }
            await this.loadSubscriptions();
            if (this.currentGroup?.id === subId && this.currentGroup?.group_type === 'subscription') {
                await this.loadNodes(subId, 'subscription');
            }
            Components.showToast(`刷新成功，共 ${result.node_count} 个节点`, 'success');
        } catch (error) {
            Components.showToast(`刷新失败: ${error.message}`, 'error');
        }
    }

    async deleteSubscription(subId) {
        if (!confirm('确定要删除这个订阅组吗？')) return;

        try {
            await api.deleteSubscription(subId);
            this.subscriptions = this.subscriptions.filter((item) => item.id !== subId);
            this.groups = this.groups.filter((item) => !(item.group_type === 'subscription' && item.id === subId));

            if (this.currentGroup?.group_type === 'subscription' && this.currentGroup?.id === subId) {
                this.currentGroup = null;
                this.currentGroupKey = null;
                localStorage.removeItem(CURRENT_GROUP_STORAGE_KEY);
                this.currentSubscription = null;
                this.currentSubscriptionId = null;
                localStorage.removeItem(CURRENT_SUBSCRIPTION_STORAGE_KEY);
                this.nodes = [];
                this.renderNodes();
            }
            this.renderSubscriptions();
            await this.restoreSubscriptionSelection();
            Components.showToast('订阅组已删除', 'success');
        } catch (error) {
            Components.showToast(`删除失败: ${error.message}`, 'error');
        }
    }

    openCreateGroupEntryModal() {
        this.elements.modalCreateGroupEntry?.classList.add('active');
    }

    openAddSubscriptionModal() {
        this.elements.subName.value = '';
        this.elements.subUrl.value = '';
        this.elements.modalCreateGroupEntry?.classList.remove('active');
        this.elements.modalAddSubscription.classList.add('active');
        this.elements.subName.focus();
    }

    openAddCustomGroupModal() {
        this.openCustomGroupModal({ targetGroupId: null, importMode: 'none' });
    }

    openCustomGroupModal({ targetGroupId = null, targetGroupName = '', importMode = 'none' } = {}) {
        this.pendingCustomGroupTargetId = targetGroupId;
        this.pendingCustomGroupTargetName = targetGroupName;
        const isImportIntoExisting = Boolean(targetGroupId);
        if (this.elements.customGroupModalTitle) {
            this.elements.customGroupModalTitle.textContent = isImportIntoExisting ? '导入到自定义组' : '新建自定义组';
        }
        if (targetGroupId) {
            this.elements.customGroupNameRow?.classList.add('hidden');
            this.elements.customGroupModeRow?.classList.add('hidden');
            this.elements.customGroupTargetRow?.classList.remove('hidden');
            if (this.elements.customGroupTargetName) {
                this.elements.customGroupTargetName.textContent = targetGroupName || '-';
            }
        } else {
            this.elements.customGroupNameRow?.classList.remove('hidden');
            this.elements.customGroupModeRow?.classList.remove('hidden');
            this.elements.customGroupTargetRow?.classList.add('hidden');
        }
        if (this.elements.customGroupName && !targetGroupId) {
            this.elements.customGroupName.value = '';
        }
        if (this.elements.customGroupContent) {
            this.elements.customGroupContent.value = '';
        }
        if (this.elements.customGroupImportMode) {
            this.elements.customGroupImportMode.value = targetGroupId ? 'paste' : (importMode || 'none');
        }
        this.handleCustomGroupImportModeChange();
        this.elements.modalCreateGroupEntry?.classList.remove('active');
        this.elements.modalAddCustomGroup?.classList.add('active');
        if (!targetGroupId) {
            this.elements.customGroupName?.focus();
        } else {
            this.elements.customGroupContent?.focus();
        }
    }

    handleCustomGroupImportModeChange() {
        if (!this.elements.customGroupImportMode || !this.elements.customGroupContentWrap) return;
        const mode = this.elements.customGroupImportMode.value;
        this.elements.customGroupContentWrap.classList.toggle('hidden', mode !== 'paste');
        if (this.elements.customGroupSubmitText) {
            this.elements.customGroupSubmitText.textContent = this.pendingCustomGroupTargetId
                ? '导入节点'
                : (mode === 'paste' ? '创建并导入' : '创建分组');
        }
    }

    async confirmAddCustomGroup() {
        const shouldImport = (this.elements.customGroupImportMode?.value || 'none') === 'paste';
        const content = (this.elements.customGroupContent?.value || '').trim();
        const targetGroupId = this.pendingCustomGroupTargetId;
        if (shouldImport && !content) {
            Components.showToast('请输入节点内容', 'warning');
            return;
        }

        if (targetGroupId) {
            if (!shouldImport) {
                Components.showToast('请选择“粘贴节点链接”导入模式', 'warning');
                return;
            }
            try {
                const result = await api.importCustomGroupNodes(targetGroupId, content);
                await this.loadSubscriptions();
                this.closeModals();
                if (this.currentGroup?.group_type === 'custom' && this.currentGroup?.id === targetGroupId) {
                    await this.selectGroup('custom', targetGroupId);
                }
                Components.showToast(
                    `导入完成: ${result.imported_count} 新增，${result.skipped_duplicates} 重复，忽略 ${result.ignored_unsupported_count || 0} 个不支持节点`,
                    'success'
                );
            } catch (error) {
                Components.showToast(`导入失败: ${error.message}`, 'error');
            }
            return;
        }

        const name = (this.elements.customGroupName?.value || '').trim();
        if (!name) {
            Components.showToast('请输入分组名称', 'warning');
            return;
        }

        try {
            const group = await api.createCustomGroup(name);
            let importResult = null;
            if (shouldImport) {
                try {
                    importResult = await api.importCustomGroupNodes(group.id, content);
                } catch (error) {
                    try {
                        await api.deleteCustomGroup(group.id);
                    } catch (cleanupError) {
                        console.warn('Failed to rollback empty custom group after import error:', cleanupError);
                    }
                    throw error;
                }
            }
            await this.loadSubscriptions();
            this.closeModals();
            await this.selectGroup('custom', group.id);
            if (shouldImport && importResult) {
                Components.showToast(
                    `导入完成: ${importResult.imported_count} 新增，${importResult.skipped_duplicates} 重复，忽略 ${importResult.ignored_unsupported_count || 0} 个不支持节点`,
                    'success'
                );
            } else {
                Components.showToast('自定义分组已创建', 'success');
            }
        } catch (error) {
            Components.showToast(`创建失败: ${error.message}`, 'error');
        }
    }

    openRenameCustomGroupModal(groupId) {
        const target = this.customGroups.find((item) => item.id === groupId);
        if (!target) return;
        this.pendingRenameGroupId = groupId;
        if (this.elements.renameCustomGroupName) {
            this.elements.renameCustomGroupName.value = target.name;
            this.elements.renameCustomGroupName.focus();
        }
        this.elements.modalRenameCustomGroup?.classList.add('active');
    }

    async confirmRenameCustomGroup() {
        const groupId = this.pendingRenameGroupId;
        const nextName = (this.elements.renameCustomGroupName?.value || '').trim();
        if (!groupId) return;
        if (!nextName) {
            Components.showToast('分组名称不能为空', 'warning');
            return;
        }

        try {
            await api.renameCustomGroup(groupId, nextName);
            await this.loadSubscriptions();
            this.closeModals();
            await this.selectGroup('custom', groupId);
            Components.showToast('分组已重命名', 'success');
        } catch (error) {
            Components.showToast(`重命名失败: ${error.message}`, 'error');
        }
    }

    openDeleteCustomGroupModal(groupId) {
        const target = this.customGroups.find((item) => item.id === groupId);
        if (!target) return;
        this.pendingDeleteGroupId = groupId;
        if (this.elements.deleteCustomGroupName) {
            this.elements.deleteCustomGroupName.textContent = target.name;
        }
        this.elements.modalDeleteCustomGroup?.classList.add('active');
    }

    async confirmDeleteCustomGroup() {
        const groupId = this.pendingDeleteGroupId;
        if (!groupId) return;

        try {
            await api.deleteCustomGroup(groupId);
            this.customGroups = this.customGroups.filter((item) => item.id !== groupId);
            this.groups = this.groups.filter((item) => !(item.group_type === 'custom' && item.id === groupId));
            if (this.currentGroup?.group_type === 'custom' && this.currentGroup?.id === groupId) {
                this.currentGroup = null;
                this.currentGroupKey = null;
                localStorage.removeItem(CURRENT_GROUP_STORAGE_KEY);
                this.nodes = [];
                this.renderNodes();
            }
            this.renderSubscriptions();
            await this.restoreSubscriptionSelection();
            this.closeModals();
            Components.showToast('自定义分组已删除', 'success');
        } catch (error) {
            Components.showToast(`删除失败: ${error.message}`, 'error');
        }
    }

    /**
     * Close all modals
     */
    closeModals() {
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.classList.remove('active');
        });
        this.pendingTestCooldownReview = null;
        this.pendingExitIpDedupeReview = null;
        this.pendingCopyNodeIds = [];
        this.pendingCustomGroupTargetId = null;
        this.pendingCustomGroupTargetName = '';
        this.pendingRenameGroupId = null;
        this.pendingDeleteGroupId = null;
        this.pendingRemoveNodeId = null;
        this.resetCustomGroupModalState();
    }

    resetCustomGroupModalState() {
        this.elements.customGroupNameRow?.classList.remove('hidden');
        this.elements.customGroupModeRow?.classList.remove('hidden');
        this.elements.customGroupTargetRow?.classList.add('hidden');
        if (this.elements.customGroupTargetName) {
            this.elements.customGroupTargetName.textContent = '-';
        }
        if (this.elements.customGroupModalTitle) {
            this.elements.customGroupModalTitle.textContent = '自定义节点组';
        }
        if (this.elements.customGroupName) {
            this.elements.customGroupName.value = '';
        }
        if (this.elements.customGroupImportMode) {
            this.elements.customGroupImportMode.value = 'none';
        }
        if (this.elements.customGroupContent) {
            this.elements.customGroupContent.value = '';
        }
        this.handleCustomGroupImportModeChange();
    }

    updateTestCooldownControls() {
        const enabledCheckbox = this.elements.testCooldownEnabled;
        const attemptsInput = this.elements.testCooldownAttempts;
        const secondsInput = this.elements.testCooldownSeconds;
        const hint = this.elements.testCooldownHint;
        if (!enabledCheckbox || !attemptsInput || !secondsInput || !hint) return;

        const scope = this.getTestCooldownScope();
        const hasScope = Boolean(scope);
        enabledCheckbox.disabled = !hasScope;
        if (!hasScope) {
            enabledCheckbox.checked = false;
        }

        const optionEnabled = hasScope && enabledCheckbox.checked;
        attemptsInput.disabled = !optionEnabled;
        secondsInput.disabled = !optionEnabled;

        if (!hasScope) {
            hint.textContent = '未激活具体 workspace 时，将按“所有代理”执行测试并可加入全局冷却';
        } else if (scope.scopeId === GLOBAL_WORKSPACE_ID && optionEnabled) {
            hint.textContent = `测试开始后将锁定为 ${scope.scopeLabel}，确认后会加入全局冷却池`;
        } else if (scope.scopeId === GLOBAL_WORKSPACE_ID) {
            hint.textContent = '当前视图: 所有代理。测试失败后可选择加入全局冷却池';
        } else if (optionEnabled) {
            hint.textContent = `测试开始后将锁定为 ${scope.scopeLabel}，确认后才会加入冷却池`;
        } else {
            hint.textContent = `当前范围: ${scope.scopeLabel}`;
        }
    }

    openTestCooldownReviewModal(review) {
        const modal = this.elements.modalTestCooldownReview;
        const meta = this.elements.testCooldownReviewMeta;
        const list = this.elements.testCooldownReviewList;
        if (!modal || !meta || !list) return;

        this.pendingTestCooldownReview = review;
        meta.textContent = `以下代理在 ${review.scopeLabel} 下连续 ${review.attempts} 次测试失败。确认后会加入 ${review.cooldownSeconds} 秒定时冷却。取消则不会加入。`;
        list.innerHTML = review.candidates.map((item) => `
            <div class="test-cooldown-review-item">
                <div class="test-cooldown-review-info">
                    <span class="test-cooldown-review-name">${this.escapeHtml(item.name)}</span>
                    <span class="test-cooldown-review-detail">失败 ${item.failed_attempts} 次${item.error ? ` · ${this.escapeHtml(item.error)}` : ''}</span>
                </div>
                <span class="test-cooldown-review-port">:${item.proxy_port}</span>
            </div>
        `).join('');
        modal.classList.add('active');
    }

    async confirmTestCooldownReview() {
        const review = this.pendingTestCooldownReview;
        if (!review) return;

        try {
            const result = await api.applyTimedLeaseCooldownBatch(
                review.scopeId,
                review.candidates.map((item) => item.proxy_port),
                review.cooldownSeconds,
                'failure'
            );
            await this.refreshLeaseData();
            this.closeModals();
            Components.showToast(
                `已向 ${review.scopeLabel} 加入 ${result.applied_ports.length} 个冷却，跳过 ${result.skipped_ports.length} 个`,
                result.skipped_ports.length === 0 ? 'success' : 'warning'
            );
        } catch (error) {
            Components.showToast(`加入冷却失败: ${error.message}`, 'error');
        }
    }

    getExitIpDuplicatePreviewFromProxies() {
        const groups = new Map();
        this.proxies.forEach((proxy) => {
            if (!proxy || proxy.pool_status === 'dedupe_disabled') return;
            const exitIp = String(proxy.exit_ip || '').trim();
            if (!exitIp) return;
            const list = groups.get(exitIp) || [];
            list.push(proxy);
            groups.set(exitIp, list);
        });

        const duplicates = [];
        groups.forEach((items, exitIp) => {
            if (items.length < 2) return;
            duplicates.push({
                exit_ip: exitIp,
                proxies: items,
            });
        });
        return duplicates;
    }

    updateExitIpDedupeButton() {
        const button = this.elements.btnDedupeExitIp;
        if (!button) return;
        const duplicateGroups = this.getExitIpDuplicatePreviewFromProxies();
        const duplicateCount = duplicateGroups.reduce((sum, group) => sum + Math.max(0, group.proxies.length - 1), 0);
        button.disabled = duplicateCount === 0;
        button.textContent = duplicateCount > 0 ? `出口IP去重 (${duplicateCount})` : '出口IP去重';
        button.title = duplicateCount > 0 ? '查看重复出口 IP 并确认去重' : '当前代理池中没有可去重的重复出口 IP';
    }

    openExitIpDedupeReviewModal(review) {
        const modal = this.elements.modalExitIpDedupeReview;
        const meta = this.elements.exitIpDedupeReviewMeta;
        const list = this.elements.exitIpDedupeReviewList;
        if (!modal || !meta || !list) return;

        this.pendingExitIpDedupeReview = review;
        meta.textContent = `检测到 ${review.duplicate_group_count} 组重复出口 IP，共建议禁用 ${review.duplicate_proxy_count} 个代理。确认后将保留每组中优先级最高的 1 个代理，其余代理会保留在代理池中但不再参与运行或测试。`;
        list.innerHTML = review.groups.map((group) => `
            <div class="test-cooldown-review-item">
                <div class="test-cooldown-review-info">
                    <span class="test-cooldown-review-name">出口IP ${this.escapeHtml(group.exit_ip)}</span>
                    <span class="test-cooldown-review-detail">保留 :${group.keep_proxy.port} · ${this.escapeHtml(group.keep_proxy.node_name)}${group.keep_proxy.latency_ms ? ` · ${group.keep_proxy.latency_ms}ms` : ''}</span>
                    ${group.remove_proxies.map((proxy) => `
                        <span class="test-cooldown-review-detail">禁用 :${proxy.port} · ${this.escapeHtml(proxy.node_name)}${proxy.latency_ms ? ` · ${proxy.latency_ms}ms` : ''}</span>
                    `).join('')}
                </div>
                <span class="test-cooldown-review-port">-${group.remove_proxies.length}</span>
            </div>
        `).join('');
        modal.classList.add('active');
    }

    async previewExitIpDedupe() {
        try {
            const review = await api.previewProxyExitIpDuplicates();
            if (!review.groups || review.groups.length === 0) {
                Components.showToast('当前代理池中没有重复出口 IP', 'success');
                await this.loadProxies();
                return;
            }
            this.openExitIpDedupeReviewModal(review);
        } catch (error) {
            Components.showToast(`获取重复出口IP失败: ${error.message}`, 'error');
        }
    }

    async confirmExitIpDedupe() {
        const review = this.pendingExitIpDedupeReview;
        if (!review) return;
        const disablePorts = (review.groups || []).flatMap((group) => (group.remove_proxies || []).map((proxy) => proxy.port));
        if (disablePorts.length === 0) {
            this.closeModals();
            return;
        }

        try {
            const result = await api.dedupeProxiesByExitIp(disablePorts);
            this.closeModals();
            await this.loadProxies();
            Components.showToast(
                `已禁用 ${result.disabled_count} 个重复代理，保留 ${result.kept_ports.length} 个出口IP主项`,
                'success'
            );
        } catch (error) {
            Components.showToast(`出口IP去重失败: ${error.message}`, 'error');
        }
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
            await this.loadSubscriptions();
            this.closeModals();
            Components.showToast(`添加成功，共 ${result.node_count} 个节点`, 'success');

            // Auto-select the new subscription
            await this.selectGroup('subscription', result.id);
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
     * Load nodes for a group
     */
    async loadNodes(groupId, groupType = 'subscription') {
        this.setNodeTestProgress({
            active: false,
            total: 0,
            completed: 0,
            success: 0,
            failed: 0,
            actionLabel: '',
            note: '',
        });
        this.elements.nodesContainer.innerHTML = `
            <div class="loading-placeholder">
                <div class="spinner"></div>
                <span>加载节点中...</span>
            </div>
        `;

        try {
            const data = groupType === 'custom'
                ? await api.getCustomGroupNodes(groupId)
                : await api.getSubscriptionNodes(groupId);
            this.nodes = this.mergeProxyPoolState(data.nodes || []);
            this.syncSelectedNodeIds();
            this.renderNodeExclusionTags();
            this.renderCurrentNodeView();
        } catch (error) {
            this.nodes = [];
            this.selectedNodeIds.clear();
            this.elements.nodesCount.textContent = '0';
            this.renderNodeExclusionTags();
            this.updateNodeActionButtons();
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
        const visibleCount = nodesToRender.length;
        const totalCount = this.nodes.length;
        this.elements.nodesCount.textContent = totalCount === visibleCount ? `${totalCount}` : `${visibleCount}/${totalCount}`;

        const visibleSelectableCount = nodesToRender.filter((node) => this.isNodeSelectable(node)).length;
        this.elements.btnSelectAll.disabled = this.isNodeTesting || visibleSelectableCount === 0;

        if (nodesToRender.length === 0) {
            const hasActiveQuery = this.getCurrentNodeFilterQuery().length > 0;
            const hasActiveFilter = this.hasActiveNodeFilters();
            const emptyText = this.currentGroup
                ? (hasActiveQuery || hasActiveFilter ? '没有匹配的节点' : '当前节点组暂无节点')
                : '请先选择一个节点组';
            this.elements.nodesContainer.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="7" height="7"></rect>
                        <rect x="14" y="3" width="7" height="7"></rect>
                        <rect x="14" y="14" width="7" height="7"></rect>
                        <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    <p>${emptyText}</p>
                </div>
            `;
            this.updateNodeActionButtons();
            return;
        }

        this.elements.nodesContainer.innerHTML = '';
        nodesToRender.forEach((node) => {
            const isSelected = this.selectedNodeIds.has(node.id);
            const item = Components.nodeItem(node, isSelected, {
                disableNodeCheckbox: !this.isNodeSelectable(node),
                disableTestButton: this.isNodeTesting,
                disableCopyToGroup: this.isNodeTesting,
                showRemoveFromGroup: this.currentGroup?.group_type === 'custom',
                disableRemoveFromGroup: this.isNodeTesting,
            });
            this.elements.nodesContainer.appendChild(item);
        });

        this.updateNodeActionButtons();
    }

    loadNodeExclusionKeywords() {
        const raw = localStorage.getItem(NODE_EXCLUSION_STORAGE_KEY);
        if (!raw) return [];
        try {
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return [];
            return parsed
                .map((entry) => {
                    if (typeof entry === 'string') {
                        const trimmed = entry.trim();
                        return trimmed ? { value: this.normalizeNodeExclusionValue(trimmed), label: trimmed } : null;
                    }
                    if (entry && typeof entry === 'object') {
                        const label = (entry.label || entry.value || '').toString().trim();
                        const value = this.normalizeNodeExclusionValue(entry.value || label);
                        return value ? { value, label: label || value } : null;
                    }
                    return null;
                })
                .filter(Boolean);
        } catch {
            return [];
        }
    }

    saveNodeExclusionKeywords() {
        localStorage.setItem(NODE_EXCLUSION_STORAGE_KEY, JSON.stringify(this.nodeExcludeKeywords));
    }

    normalizeNodeExclusionValue(value) {
        return (value || '')
            .toString()
            .trim()
            .toLowerCase()
            .replace(/[\s_-]+/g, '');
    }

    parseKeywordEntries(raw) {
        const entries = (raw || '').split(/[\n,，;]+/).map((item) => item.trim()).filter(Boolean);
        const unique = new Map();
        entries.forEach((item) => {
            const normalized = this.normalizeNodeExclusionValue(item);
            if (normalized && !unique.has(normalized)) {
                unique.set(normalized, { value: normalized, label: item });
            }
        });
        return Array.from(unique.values());
    }

    addNodeExclusionKeywords() {
        if (!this.elements.nodeExclusionInput) return;
        const raw = this.elements.nodeExclusionInput.value;
        const additions = this.parseKeywordEntries(raw);
        if (!additions.length) return;
        const combined = new Map(this.nodeExcludeKeywords.map((item) => [item.value, item]));
        additions.forEach((item) => {
            if (!combined.has(item.value)) {
                combined.set(item.value, item);
            }
        });
        this.nodeExcludeKeywords = Array.from(combined.values());
        this.saveNodeExclusionKeywords();
        this.elements.nodeExclusionInput.value = '';
        this.renderNodeExclusionTags();
        this.pruneExcludedSelections();
        this.renderCurrentNodeView();
    }

    renderNodeExclusionTags() {
        if (!this.elements.nodeExclusionTags) return;
        this.elements.nodeExclusionTags.innerHTML = '';
        this.nodeExcludeKeywords.forEach((keyword) => {
            const count = this.getNodeExclusionMatchCount(keyword);
            const tag = document.createElement('span');
            tag.className = 'node-exclusion-tag';
            tag.dataset.value = keyword.value;
            const label = document.createElement('span');
            label.textContent = `${keyword.label} (${count})`;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.innerHTML = '&times;';
            remove.title = '移除关键词';
            tag.appendChild(label);
            tag.appendChild(remove);
            this.elements.nodeExclusionTags.appendChild(tag);
        });
    }

    handleNodeExclusionTagClick(e) {
        const remove = e.target.closest('.node-exclusion-tag button');
        if (!remove) return;
        const tag = remove.closest('.node-exclusion-tag');
        const value = tag?.dataset.value;
        if (!value) return;
        this.nodeExcludeKeywords = this.nodeExcludeKeywords.filter((item) => item.value !== value);
        this.saveNodeExclusionKeywords();
        this.renderNodeExclusionTags();
        this.pruneExcludedSelections();
        this.renderCurrentNodeView();
    }

    matchesNodeExclusion(node) {
        if (!node || this.nodeExcludeKeywords.length === 0) {
            return false;
        }

        const rawText = `${node.name || ''} ${node.address || ''}`.toLowerCase();
        const normalizedText = this.normalizeNodeExclusionValue(`${node.name || ''}${node.address || ''}`);

        return this.nodeExcludeKeywords.some((keyword) => (
            rawText.includes((keyword.label || '').toLowerCase()) || normalizedText.includes(keyword.value)
        ));
    }

    getNodeExclusionMatchCount(keyword) {
        if (!keyword) return 0;

        const loweredLabel = (keyword.label || '').toLowerCase();
        return this.nodes.filter((node) => {
            const rawText = `${node.name || ''} ${node.address || ''}`.toLowerCase();
            const normalizedText = this.normalizeNodeExclusionValue(`${node.name || ''}${node.address || ''}`);
            return rawText.includes(loweredLabel) || normalizedText.includes(keyword.value);
        }).length;
    }

    pruneExcludedSelections() {
        if (this.nodeExcludeKeywords.length === 0) {
            return;
        }

        this.nodes.forEach((node) => {
            if (!node.in_proxy_pool && this.matchesNodeExclusion(node)) {
                this.selectedNodeIds.delete(node.id);
            }
        });
    }

    handleNodeFilterOrSortChange() {
        this.nodeViewFilters = this.getNodeViewFilters();
        this.renderCurrentNodeView();
    }

    getNodeViewFilters() {
        return {
            onlyAvailable: Boolean(this.elements.nodeFilterAvailable?.checked),
            onlyNotInPool: Boolean(this.elements.nodeFilterNotInPool?.checked),
            onlyFailed: Boolean(this.elements.nodeFilterFailed?.checked),
            sortBy: this.elements.nodeSort?.value || 'default',
        };
    }

    hasActiveNodeFilters() {
        const filters = this.nodeViewFilters || {};
        return Boolean(filters.onlyAvailable || filters.onlyNotInPool || filters.onlyFailed || this.nodeExcludeKeywords.length > 0);
    }

    getNodeStatusRank(status) {
        const rank = {
            success: 0,
            testing: 1,
            pending: 2,
            failed: 3,
        };
        return rank[status] ?? 9;
    }

    applyNodeSort(nodes, sortBy = 'default') {
        if (!Array.isArray(nodes) || nodes.length <= 1 || sortBy === 'default') {
            return nodes;
        }

        const sorted = [...nodes];
        if (sortBy === 'test_status') {
            sorted.sort((a, b) => {
                const rankDelta = this.getNodeStatusRank(a.test_status) - this.getNodeStatusRank(b.test_status);
                if (rankDelta !== 0) return rankDelta;
                const latencyA = typeof a.latency_ms === 'number' ? a.latency_ms : Number.POSITIVE_INFINITY;
                const latencyB = typeof b.latency_ms === 'number' ? b.latency_ms : Number.POSITIVE_INFINITY;
                if (latencyA !== latencyB) return latencyA - latencyB;
                return (a.name || '').localeCompare(b.name || '', 'zh-CN');
            });
            return sorted;
        }

        if (sortBy === 'latency_ms') {
            sorted.sort((a, b) => {
                const latencyA = typeof a.latency_ms === 'number' ? a.latency_ms : Number.POSITIVE_INFINITY;
                const latencyB = typeof b.latency_ms === 'number' ? b.latency_ms : Number.POSITIVE_INFINITY;
                if (latencyA !== latencyB) return latencyA - latencyB;
                const rankDelta = this.getNodeStatusRank(a.test_status) - this.getNodeStatusRank(b.test_status);
                if (rankDelta !== 0) return rankDelta;
                return (a.name || '').localeCompare(b.name || '', 'zh-CN');
            });
            return sorted;
        }

        return sorted;
    }

    getNodesForCurrentView(query = '') {
        const lowerQuery = (query || '').trim().toLowerCase();
        const filters = this.nodeViewFilters || this.getNodeViewFilters();

        const filtered = this.nodes.filter((node) => {
            if (this.matchesNodeExclusion(node)) {
                return false;
            }

            if (lowerQuery) {
                const name = (node.name || '').toLowerCase();
                const address = (node.address || '').toLowerCase();
                const protocol = (node.protocol || '').toLowerCase();
                const matchesQuery =
                    name.includes(lowerQuery) ||
                    address.includes(lowerQuery) ||
                    protocol.includes(lowerQuery);
                if (!matchesQuery) {
                    return false;
                }
            }

            if (filters.onlyAvailable && node.test_status !== 'success') {
                return false;
            }
            if (filters.onlyNotInPool && node.in_proxy_pool) {
                return false;
            }
            if (filters.onlyFailed && node.test_status !== 'failed') {
                return false;
            }

            return true;
        });

        return this.applyNodeSort(filtered, filters.sortBy);
    }

    /**
     * Filter nodes by search query
     */
    filterNodes(query) {
        this.nodeViewFilters = this.getNodeViewFilters();
        const nodesToRender = this.getNodesForCurrentView(query);
        this.renderNodes(nodesToRender);
    }

    mergeProxyPoolState(nodes, { preferProxyMap = false } = {}) {
        const proxyPortByNodeId = new Map(
            (this.proxies || [])
                .filter((proxy) => proxy && proxy.node_id)
                .map((proxy) => [proxy.node_id, proxy.port])
        );

        return nodes.map((node) => {
            const fallbackPort = proxyPortByNodeId.get(node.id) ?? null;
            const hasExplicitPoolFlag = typeof node.in_proxy_pool === 'boolean';
            const inProxyPool = preferProxyMap
                ? Boolean(fallbackPort !== null)
                : (hasExplicitPoolFlag ? node.in_proxy_pool : Boolean(fallbackPort !== null));
            return {
                ...node,
                in_proxy_pool: inProxyPool,
                proxy_port: inProxyPool
                    ? (preferProxyMap ? fallbackPort : (node.proxy_port ?? fallbackPort))
                    : null,
            };
        });
    }

    syncSelectedNodeIds() {
        const nodeById = new Map(this.nodes.map((node) => [node.id, node]));
        const nextSelected = new Set();

        this.selectedNodeIds.forEach((nodeId) => {
            const node = nodeById.get(nodeId);
            if (node && (node.in_proxy_pool || this.isNodeSelectable(node))) {
                nextSelected.add(nodeId);
            }
        });

        this.nodes.forEach((node) => {
            if (node.in_proxy_pool) {
                nextSelected.add(node.id);
            }
        });

        this.selectedNodeIds = nextSelected;
        this.pruneExcludedSelections();
    }

    isNodeSelectable(node) {
        return Boolean(node) && !node.in_proxy_pool && this.isNodeRuntimeSupported(node);
    }

    isNodeRuntimeSupported(node) {
        return node?.runtime_supported !== false;
    }

    getNodeRuntimeSupportReason(node) {
        return node?.runtime_support_reason || '当前运行环境不支持此协议';
    }

    getCurrentNodeFilterQuery() {
        return (this.elements.nodeSearch?.value || '').trim();
    }

    renderCurrentNodeView() {
        const query = this.getCurrentNodeFilterQuery();
        this.filterNodes(query);
    }

    getActionableNodesForCurrentView() {
        return this.getNodesForCurrentView(this.getCurrentNodeFilterQuery())
            .filter((node) => this.isNodeRuntimeSupported(node));
    }

    /**
     * Handle node item click
     */
    async handleNodeClick(e) {
        const item = e.target.closest('.node-item');
        if (!item) return;
        const node = this.nodes.find((candidate) => candidate.id === item.dataset.id);
        if (!node) return;

        const action = e.target.closest('[data-node-action]')?.dataset.nodeAction;
        if (action === 'test') {
            if (!this.isNodeRuntimeSupported(node)) {
                Components.showToast(this.getNodeRuntimeSupportReason(node), 'warning');
                return;
            }
            await this.testSingleNode(item.dataset.id);
            return;
        }
        if (action === 'copy-to-group') {
            if (!this.isNodeRuntimeSupported(node)) {
                Components.showToast(this.getNodeRuntimeSupportReason(node), 'warning');
                return;
            }
            this.openCopyToGroupModal([item.dataset.id]);
            return;
        }
        if (action === 'remove-from-group') {
            this.removeNodeFromCurrentCustomGroup(item.dataset.id);
            return;
        }

        // Don't toggle if clicking on checkbox directly
        if (e.target.closest('.node-checkbox')) return;

        if (!this.isNodeSelectable(node) || this.isNodeTesting) return;

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
        if (checkbox.disabled) {
            checkbox.checked = true;
            return;
        }

        const item = checkbox.closest('.node-item');
        const nodeId = item.dataset.id;

        if (checkbox.checked) {
            this.selectedNodeIds.add(nodeId);
            item.classList.add('selected');
        } else {
            this.selectedNodeIds.delete(nodeId);
            item.classList.remove('selected');
        }

        this.updateNodeActionButtons();
    }

    /**
     * Toggle select all nodes
     */
    toggleSelectAll() {
        if (this.isNodeTesting) return;

        const selectableNodes = this.getNodesForCurrentView(this.getCurrentNodeFilterQuery())
            .filter((node) => this.isNodeSelectable(node));
        if (selectableNodes.length === 0) {
            this.updateNodeActionButtons();
            return;
        }

        const allSelected = selectableNodes.every((node) => this.selectedNodeIds.has(node.id));

        if (allSelected) {
            // Deselect all
            selectableNodes.forEach((node) => this.selectedNodeIds.delete(node.id));
        } else {
            // Select all
            selectableNodes.forEach((node) => this.selectedNodeIds.add(node.id));
        }

        this.syncSelectedNodeIds();
        this.renderCurrentNodeView();
    }

    /**
     * Update add to proxy button state
     */
    updateAddToProxyButton() {
        const count = this.getSelectedAddableNodeIds().length;
        this.elements.btnAddToProxy.disabled = count === 0 || this.isNodeTesting;
        this.elements.btnAddToProxy.title = this.isNodeTesting
            ? '节点测试进行中，请稍候'
            : (count > 0 ? '将已勾选且未入池的节点加入代理池' : '请先勾选未入池节点');
        this.elements.btnAddToProxy.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14"></path>
                <path d="m12 5 7 7-7 7"></path>
            </svg>
            添加到代理${count > 0 ? ` (${count})` : ''}
        `;
    }

    updateAddToGroupButton() {
        if (!this.elements.btnAddToGroup) return;
        const count = this.getSelectedCopyableNodeIds().length;
        this.elements.btnAddToGroup.disabled = this.isNodeTesting || count === 0;
        if (this.isNodeTesting) {
            this.elements.btnAddToGroup.title = '节点测试进行中，请稍候';
        } else if (count === 0) {
            this.elements.btnAddToGroup.title = '请先勾选当前可见的可复制节点';
        } else {
            this.elements.btnAddToGroup.title = '将当前可见的勾选节点复制到自定义分组';
        }
        this.elements.btnAddToGroup.textContent = `加入到分组${count > 0 ? ` (${count})` : ''}`;
    }

    updateSelectAllButton() {
        if (!this.elements.btnSelectAll) return;
        const visibleSelectableCount = this.getNodesForCurrentView(this.getCurrentNodeFilterQuery())
            .filter((node) => this.isNodeSelectable(node)).length;
        this.elements.btnSelectAll.disabled = this.isNodeTesting || visibleSelectableCount === 0;
        this.elements.btnSelectAll.textContent = visibleSelectableCount > 0 ? `全选 (${visibleSelectableCount})` : '全选';
        this.elements.btnSelectAll.title = this.isNodeTesting
            ? '节点测试进行中，请稍候'
            : (visibleSelectableCount > 0
                ? '勾选当前筛选结果中的未入池节点'
                : (this.currentGroup ? '当前列表没有可勾选节点' : '请先选择节点组'));
    }

    updateNodeTestButtons() {
        const selectedCount = this.getSelectedTestableNodeIds().length;
        if (this.elements.btnTestSelectedNodes) {
            this.elements.btnTestSelectedNodes.disabled = selectedCount === 0 || this.isNodeTesting;
            this.elements.btnTestSelectedNodes.title = this.isNodeTesting
                ? '节点测试进行中，请稍候'
                : (selectedCount > 0 ? '测试当前勾选的未入池节点' : '请先勾选未入池节点');
            this.elements.btnTestSelectedNodes.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                测试选中${selectedCount > 0 ? ` (${selectedCount})` : ''}
            `;
        }

        if (this.elements.btnTestAllNodes) {
            const totalCount = this.getActionableNodesForCurrentView().length;
            this.elements.btnTestAllNodes.disabled = totalCount === 0 || this.isNodeTesting;
            this.elements.btnTestAllNodes.title = this.isNodeTesting
                ? '节点测试进行中，请稍候'
                : (totalCount > 0 ? '测试当前筛选结果中的全部节点' : (this.currentGroup ? '当前筛选结果没有节点' : '请先选择节点组'));
            this.elements.btnTestAllNodes.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                测试全部${totalCount > 0 ? ` (${totalCount})` : ''}
            `;
        }
    }

    updateAddSuccessToProxyButton() {
        if (!this.elements.btnAddSuccessToProxy) return;
        const count = this.getSuccessfulAddableNodeIds().length;
        this.elements.btnAddSuccessToProxy.disabled = count === 0 || this.isNodeTesting;
        this.elements.btnAddSuccessToProxy.title = this.isNodeTesting
            ? '节点测试进行中，请稍候'
            : (count > 0 ? '将当前筛选结果中测试成功且未入池的节点一次性加入代理池' : '当前筛选结果中暂无测试成功且未入池节点');
        this.elements.btnAddSuccessToProxy.textContent = `一键加入成功项${count > 0 ? ` (${count})` : ''}`;
    }

    getSelectedAddableNodeIds() {
        const visibleIds = new Set(this.getActionableNodesForCurrentView().map((node) => node.id));
        return this.nodes
            .filter((node) => visibleIds.has(node.id) && this.isNodeSelectable(node) && this.selectedNodeIds.has(node.id))
            .map((node) => node.id);
    }

    getSelectedTestableNodeIds() {
        const visibleIds = new Set(this.getActionableNodesForCurrentView().map((node) => node.id));
        return this.nodes
            .filter((node) => visibleIds.has(node.id) && this.isNodeSelectable(node) && this.selectedNodeIds.has(node.id))
            .map((node) => node.id);
    }

    getSuccessfulAddableNodeIds() {
        return this.getActionableNodesForCurrentView()
            .filter((node) => this.isNodeSelectable(node) && node.test_status === 'success')
            .map((node) => node.id);
    }

    setNodeTestingState(isTesting) {
        this.isNodeTesting = isTesting;
        this.updateNodeActionButtons();
    }

    updateNodeActionButtons() {
        this.updateAddToProxyButton();
        this.updateAddToGroupButton();
        this.updateNodeTestButtons();
        this.updateAddSuccessToProxyButton();
        this.updateSelectAllButton();
    }

    setNodeTestProgress(patch = {}) {
        this.nodeTestProgress = {
            ...this.nodeTestProgress,
            ...patch,
        };
        this.renderNodeTestProgress();
    }

    renderNodeTestProgress() {
        const container = this.elements.nodeTestProgress;
        if (!container) return;

        const progress = this.nodeTestProgress || {};
        const total = progress.total || 0;
        if (total <= 0) {
            container.classList.add('hidden');
            return;
        }

        const completed = Math.max(0, Math.min(total, progress.completed || 0));
        const percent = Math.max(0, Math.min(100, progress.percent ?? (total > 0 ? Math.round((completed / total) * 100) : 0)));
        const currentTargetCompleted = Math.max(0, progress.currentTargetCompleted || 0);
        const currentTargetTotal = Math.max(0, progress.currentTargetTotal || 0);

        const title = this.elements.nodeTestProgressTitle;
        const status = this.elements.nodeTestProgressStatus;
        const counter = this.elements.nodeTestProgressCounter;
        const fill = this.elements.nodeTestProgressFill;
        const success = this.elements.nodeTestProgressSuccess;
        const failed = this.elements.nodeTestProgressFailed;
        const rate = this.elements.nodeTestProgressRate;
        const meta = this.elements.nodeTestProgressMeta;
        const successCount = progress.success || 0;
        const failedCount = progress.failed || 0;
        const successRate = total > 0 ? Math.round((successCount / total) * 100) : 0;

        if (title) {
            const prefix = progress.actionLabel || '节点测试';
            title.textContent = progress.active ? `${prefix}进行中` : `${prefix}完成`;
        }
        if (status) {
            status.textContent = progress.statusText || (progress.active ? '正在测试' : (completed >= total ? '已完成' : '待开始'));
        }
        if (counter) {
            counter.textContent = progress.active && currentTargetTotal > 0
                ? `${currentTargetCompleted}/${currentTargetTotal}`
                : `${completed}/${total}`;
        }
        if (fill) {
            fill.style.width = `${percent}%`;
        }
        if (success) {
            success.textContent = `成功 ${successCount}`;
        }
        if (failed) {
            failed.textContent = `失败 ${failedCount}`;
        }
        if (rate) {
            rate.textContent = progress.active ? `进度 ${percent}%` : `成功率 ${successRate}%`;
        }
        if (meta) {
            if (progress.active) {
                const targetLabel = progress.targetIndex && progress.targetTotal
                    ? `目标 ${progress.targetIndex}/${progress.targetTotal}`
                    : '目标测试中';
                const targetUrl = progress.activeTarget ? ` · ${progress.activeTarget}` : '';
                const currentLabel = currentTargetTotal > 0
                    ? `当前 ${currentTargetCompleted}/${currentTargetTotal}`
                    : `已确认 ${completed}/${total}`;
                const extraNote = progress.note ? ` · ${progress.note}` : '';
                meta.textContent = `${targetLabel} · ${currentLabel} · 已确认 ${completed}/${total}${targetUrl}${extraNote}`;
            } else {
                const note = progress.note ? ` · ${progress.note}` : '';
                meta.textContent = `已完成 ${completed} / ${total}${note}`;
            }
        }

        container.classList.toggle('testing', Boolean(progress.active));
        container.classList.toggle('done', !progress.active && completed >= total);
        container.classList.remove('hidden');
    }

    markNodesAsTesting(nodeIds) {
        const targetSet = new Set(nodeIds);
        this.nodes = this.nodes.map((node) => {
            if (targetSet.has(node.id)) {
                return {
                    ...node,
                    test_status: 'testing',
                    test_error: null,
                    successful_target: null,
                    tested_target: null,
                };
            }
            return node;
        });
        this.renderNodeExclusionTags();
    }

    applyNodeTestResults(results) {
        if (!Array.isArray(results) || results.length === 0) return;

        const resultById = new Map(results.map((result) => [result.node_id, result]));
        this.nodes = this.nodes.map((node) => {
            const result = resultById.get(node.id);
            if (!result) return node;

            return {
                ...node,
                test_status: result.status || node.test_status,
                latency_ms: result.latency_ms ?? null,
                exit_ip: result.exit_ip ?? null,
                exit_country: result.exit_country ?? null,
                test_error: result.error ?? result.error_message ?? result.reason ?? null,
                successful_target: result.successful_target ?? result.success_target ?? result.target_hit ?? null,
                tested_target: result.tested_target ?? result.last_test_target ?? null,
            };
        });
        this.renderNodeExclusionTags();
    }

    autoSelectSuccessNodes(targetNodeIds, results) {
        const resultById = new Map((results || []).map((result) => [result.node_id, result]));
        targetNodeIds.forEach((nodeId) => {
            const node = this.nodes.find((item) => item.id === nodeId);
            if (!node || node.in_proxy_pool) {
                return;
            }
            const result = resultById.get(nodeId);
            if (result?.status === 'success') {
                this.selectedNodeIds.add(nodeId);
            } else if (result?.status === 'failed') {
                this.selectedNodeIds.delete(nodeId);
            }
        });
    }

    async pollNodeTestJob(jobId, actionLabel) {
        while (true) {
            const snapshot = await api.getNodeTestJob(jobId);
            this.setNodeTestProgress({
                active: snapshot.status === 'queued' || snapshot.status === 'running',
                total: snapshot.total || 0,
                completed: snapshot.completed_count || 0,
                success: snapshot.success_count || 0,
                failed: snapshot.failed_count || 0,
                percent: snapshot.progress_percent || 0,
                actionLabel,
                note: snapshot.note || '',
                statusText: snapshot.status === 'queued'
                    ? '排队中'
                    : (snapshot.status === 'running'
                        ? '正在测试'
                        : (snapshot.status === 'completed' ? '已完成' : '失败')),
                activeTarget: snapshot.active_target || null,
                targetIndex: snapshot.target_index ?? null,
                targetTotal: snapshot.target_total ?? null,
                currentTargetCompleted: snapshot.current_target_completed || 0,
                currentTargetTotal: snapshot.current_target_total || 0,
            });

            if (snapshot.status === 'completed' || snapshot.status === 'failed') {
                return snapshot;
            }

            await new Promise((resolve) => setTimeout(resolve, 350));
        }
    }

    async runNodeTests(nodeIds, { autoSelectSuccess = false, actionLabel = '测试' } = {}) {
        const requestedNodeIds = Array.from(new Set((nodeIds || []).filter(Boolean)));
        const uniqueNodeIds = requestedNodeIds.filter((nodeId) => {
            const node = this.nodes.find((item) => item.id === nodeId);
            return this.isNodeRuntimeSupported(node);
        });
        if (requestedNodeIds.length > 0 && uniqueNodeIds.length === 0) {
            const firstNode = this.nodes.find((item) => item.id === requestedNodeIds[0]);
            Components.showToast(this.getNodeRuntimeSupportReason(firstNode), 'warning');
            return;
        }
        if (uniqueNodeIds.length === 0) {
            Components.showToast('请先选择可测试节点', 'warning');
            return;
        }

        const previousResultsByNodeId = new Map();
        uniqueNodeIds.forEach((nodeId) => {
            const node = this.nodes.find((item) => item.id === nodeId);
            if (!node) return;
            previousResultsByNodeId.set(nodeId, {
                test_status: node.test_status,
                latency_ms: node.latency_ms,
                exit_ip: node.exit_ip,
                exit_country: node.exit_country,
                test_error: node.test_error,
                successful_target: node.successful_target,
                tested_target: node.tested_target,
            });
        });

        this.setNodeTestProgress({
            active: true,
            total: uniqueNodeIds.length,
            completed: 0,
            success: 0,
            failed: 0,
            percent: 0,
            actionLabel,
            note: '等待任务启动',
            statusText: '排队中',
            activeTarget: null,
            targetIndex: null,
            targetTotal: null,
            currentTargetCompleted: 0,
            currentTargetTotal: 0,
        });
        this.setNodeTestingState(true);
        this.markNodesAsTesting(uniqueNodeIds);
        this.renderCurrentNodeView();

        try {
            const job = await api.startNodeTestJob(uniqueNodeIds, 5, 'multi_target');
            const result = await this.pollNodeTestJob(job.job_id, actionLabel);
            if (result.status === 'failed') {
                throw new Error(result.error || result.note || '节点测试任务失败');
            }
            const results = result.results || [];
            this.applyNodeTestResults(results);

            const successCount = typeof result.success_count === 'number'
                ? result.success_count
                : results.filter((item) => item.status === 'success').length;
            const failedCount = typeof result.failed_count === 'number'
                ? result.failed_count
                : results.filter((item) => item.status === 'failed').length;
            const hitTargets = Array.from(
                new Set(
                    results
                        .filter((item) => item.status === 'success')
                        .map((item) => item.successful_target || item.success_target || item.target_hit)
                        .filter(Boolean)
                )
            );
            this.setNodeTestProgress({
                active: false,
                total: uniqueNodeIds.length,
                completed: uniqueNodeIds.length,
                success: successCount,
                failed: failedCount,
                percent: 100,
                actionLabel,
                note: hitTargets.length > 0 ? `命中目标源 ${hitTargets.length}` : '',
                statusText: '已完成',
                activeTarget: null,
                targetIndex: null,
                targetTotal: null,
                currentTargetCompleted: 0,
                currentTargetTotal: 0,
            });

            if (autoSelectSuccess) {
                this.autoSelectSuccessNodes(uniqueNodeIds, results);
            }

            this.syncSelectedNodeIds();
            this.renderCurrentNodeView();
            Components.showToast(
                `${actionLabel}完成: ${successCount} 成功, ${failedCount} 失败`,
                failedCount === 0 ? 'success' : 'warning'
            );
        } catch (error) {
            this.setNodeTestProgress({
                active: false,
                total: uniqueNodeIds.length,
                completed: uniqueNodeIds.length,
                success: 0,
                failed: uniqueNodeIds.length,
                percent: 100,
                actionLabel,
                note: '请求失败',
                statusText: '失败',
                activeTarget: null,
                targetIndex: null,
                targetTotal: null,
                currentTargetCompleted: 0,
                currentTargetTotal: 0,
            });
            Components.showToast(`${actionLabel}失败: ${error.message}`, 'error');
            this.nodes = this.nodes.map((node) => {
                const previous = previousResultsByNodeId.get(node.id);
                if (previous) {
                    return {
                        ...node,
                        test_status: previous.test_status,
                        latency_ms: previous.latency_ms,
                        exit_ip: previous.exit_ip,
                        exit_country: previous.exit_country,
                        test_error: previous.test_error,
                        successful_target: previous.successful_target,
                        tested_target: previous.tested_target,
                    };
                }
                return node;
            });
            this.renderCurrentNodeView();
        } finally {
            this.setNodeTestingState(false);
        }
    }

    async testSingleNode(nodeId) {
        const node = this.nodes.find((item) => item.id === nodeId);
        if (!node) return;
        if (!this.isNodeRuntimeSupported(node)) {
            Components.showToast(this.getNodeRuntimeSupportReason(node), 'warning');
            return;
        }
        await this.runNodeTests([nodeId], {
            autoSelectSuccess: false,
            actionLabel: `节点 ${node.name} 测试`,
        });
    }

    async testSelectedNodes() {
        const nodeIds = this.getSelectedTestableNodeIds();
        await this.runNodeTests(nodeIds, {
            autoSelectSuccess: true,
            actionLabel: '选中节点测试',
        });
    }

    async testAllNodes() {
        const nodeIds = this.getActionableNodesForCurrentView().map((node) => node.id);
        await this.runNodeTests(nodeIds, {
            autoSelectSuccess: true,
            actionLabel: '全部节点测试',
        });
    }

    /**
     * Add selected nodes to proxy list
     */
    async addSelectedToProxy() {
        const nodeIds = this.getSelectedAddableNodeIds();
        if (nodeIds.length === 0) return;
        await this.addNodesToProxy(nodeIds, 'selected');
    }

    async addSuccessfulToProxy() {
        const nodeIds = this.getSuccessfulAddableNodeIds();
        if (nodeIds.length === 0) {
            Components.showToast('暂无可加入的成功节点', 'warning');
            return;
        }
        await this.addNodesToProxy(nodeIds, 'success_only');
    }

    async addNodesToProxy(nodeIds, mode = 'selected') {
        try {
            const addedProxies = await api.addProxies(nodeIds);

            if (Array.isArray(addedProxies)) {
                const addedByNodeId = new Map(
                    addedProxies
                        .filter((proxy) => proxy?.node_id)
                        .map((proxy) => [proxy.node_id, proxy.port || null])
                );

                this.nodes = this.nodes.map((node) => {
                    if (!addedByNodeId.has(node.id)) return node;
                    return {
                        ...node,
                        in_proxy_pool: true,
                        proxy_port: addedByNodeId.get(node.id),
                    };
                });
            }

            this.syncSelectedNodeIds();
            this.renderCurrentNodeView();

            await this.loadProxies();
            const message = mode === 'success_only'
                ? `已一键添加 ${nodeIds.length} 个可用节点到代理列表`
                : `已添加 ${nodeIds.length} 个节点到代理列表`;
            Components.showToast(message, 'success');
        } catch (error) {
            Components.showToast(`添加失败: ${error.message}`, 'error');
        }
    }

    getSelectedCopyableNodeIds() {
        const visibleIds = new Set(this.getActionableNodesForCurrentView().map((node) => node.id));
        return this.nodes
            .filter((node) => visibleIds.has(node.id) && this.isNodeSelectable(node) && this.selectedNodeIds.has(node.id))
            .map((node) => node.id);
    }

    openCopyToGroupModal(nodeIds = null) {
        const sourceNodeIds = Array.isArray(nodeIds) && nodeIds.length > 0
            ? nodeIds.filter((nodeId) => {
                const node = this.nodes.find((item) => item.id === nodeId);
                return this.isNodeRuntimeSupported(node);
            })
            : this.getSelectedCopyableNodeIds();
        if (sourceNodeIds.length === 0) {
            Components.showToast('请先勾选当前可见且兼容的可复制节点', 'warning');
            return;
        }
        if (!this.elements.copyGroupSelect) return;
        this.pendingCopyNodeIds = sourceNodeIds;

        const options = this.customGroups.map((group) =>
            `<option value="${group.id}">${this.escapeHtml(group.name)} (${group.node_count || 0})</option>`
        );
        this.elements.copyGroupSelect.innerHTML = options.length > 0
            ? options.join('')
            : '<option value="">暂无可选分组（可直接输入新分组名称）</option>';
        if (this.elements.copyGroupNewName) {
            this.elements.copyGroupNewName.value = '';
        }
        this.elements.modalCopyToGroup?.classList.add('active');
    }

    async confirmCopyToGroup() {
        const sourceNodeIds = Array.isArray(this.pendingCopyNodeIds) ? [...this.pendingCopyNodeIds] : [];
        this.pendingCopyNodeIds = [];
        if (sourceNodeIds.length === 0) {
            Components.showToast('请先勾选节点', 'warning');
            return;
        }

        let targetGroupId = this.elements.copyGroupSelect?.value || '';
        const newGroupName = (this.elements.copyGroupNewName?.value || '').trim();
        let createdGroupId = null;

        try {
            if (newGroupName) {
                const created = await api.createCustomGroup(newGroupName);
                targetGroupId = created.id;
                createdGroupId = created.id;
            }
            if (!targetGroupId) {
                Components.showToast('请选择目标分组或输入新分组名称', 'warning');
                return;
            }

            const result = await api.copyNodesToCustomGroup(targetGroupId, sourceNodeIds);
            await this.loadSubscriptions();
            if (this.currentGroup?.group_type === 'custom' && this.currentGroup?.id === targetGroupId) {
                await this.selectGroup('custom', targetGroupId);
            }
            this.closeModals();
            Components.showToast(
                `加入分组完成: ${result.copied_count} 新增，${result.skipped_duplicates} 重复`,
                'success'
            );
        } catch (error) {
            if (createdGroupId) {
                try {
                    await api.deleteCustomGroup(createdGroupId);
                } catch (cleanupError) {
                    console.warn('Failed to rollback empty custom group after copy error:', cleanupError);
                }
            }
            Components.showToast(`加入分组失败: ${error.message}`, 'error');
        }
    }

    removeNodeFromCurrentCustomGroup(nodeId) {
        if (!this.currentGroup || this.currentGroup.group_type !== 'custom') {
            return;
        }
        const node = this.nodes.find((item) => item.id === nodeId);
        if (!node) return;
        this.pendingRemoveNodeId = nodeId;
        if (this.elements.removeNodeName) {
            this.elements.removeNodeName.textContent = node.name;
        }
        this.elements.modalRemoveNodeFromGroup?.classList.add('active');
    }

    async confirmRemoveNodeFromGroup() {
        const nodeId = this.pendingRemoveNodeId;
        if (!nodeId || !this.currentGroup || this.currentGroup.group_type !== 'custom') {
            return;
        }
        try {
            await api.deleteCustomGroupNode(this.currentGroup.id, nodeId);
            this.nodes = this.nodes.filter((item) => item.id !== nodeId);
            this.selectedNodeIds.delete(nodeId);
            this.renderNodeExclusionTags();
            this.renderCurrentNodeView();
            await this.loadSubscriptions();
            await this.selectGroup('custom', this.currentGroup.id);
            this.closeModals();
            Components.showToast('节点已移出分组', 'success');
        } catch (error) {
            Components.showToast(`移出失败: ${error.message}`, 'error');
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
            if (this.nodes.length > 0) {
                this.nodes = this.mergeProxyPoolState(this.nodes, { preferProxyMap: true });
                this.syncSelectedNodeIds();
                this.renderNodeExclusionTags();
                this.renderCurrentNodeView();
            }
            this.renderProxies();
            this.updateXrayStatus();
        } catch (error) {
            console.error('Failed to load proxies:', error);
        }
    }

    getEnabledProxies() {
        return (this.proxies || []).filter((proxy) => (
            proxy?.pool_status !== 'dedupe_disabled' && this.isProxyRuntimeLoaded(proxy)
        ));
    }

    getProxyByPort(port) {
        return (this.proxies || []).find((proxy) => proxy?.port === port) || null;
    }

    isProxyRuntimeLoaded(proxy) {
        return proxy?.runtime_loaded !== false;
    }

    getProxyRuntimeLoadReason(proxy) {
        return proxy?.runtime_load_reason
            || proxy?.runtime_support_reason
            || '该代理已在代理池中，但当前未加载到 Xray 运行配置。';
    }

    /**
     * Render proxies list
     */
    renderProxies() {
        const enabledProxyCount = this.getEnabledProxies().length;
        this.elements.proxiesCount.textContent = this.proxies.length;
        this.elements.btnTestAll.disabled = enabledProxyCount === 0 || this.xrayStatus !== 'running';
        this.elements.btnClearProxies.disabled = this.proxies.length === 0;
        this.updateExitIpDedupeButton();

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
            const item = Components.proxyItem(proxy, this.getProxyWorkspaceState(proxy));
            this.elements.proxiesContainer.appendChild(item);
        });
    }

    handleWorkspaceChipClick(e) {
        const chip = e.target.closest('[data-workspace-id]');
        if (!chip) return;
        this.setCurrentWorkspace(chip.dataset.workspaceId);
    }

    getProxyWorkspaceState(proxy) {
        const activeLeases = this.leaseStatus.active_leases || [];
        const cooldowns = this.leaseStatus.cooldowns || [];
        const activeLeaseForPort = activeLeases.find((lease) => lease.proxy_port === proxy.port);
        const cooldownsForPort = cooldowns.filter((item) => item.proxy_port === proxy.port);
        const metricsDisplay = this.getProxyMetricsDisplay(proxy, {
            activeLease: activeLeaseForPort,
            cooldowns: cooldownsForPort,
        });

        if (proxy?.pool_status === 'dedupe_disabled') {
            return {
                stateClass: 'dedupe-disabled',
                stateLabel: '去重禁用',
                sourceLabel: 'exit-ip',
                note: '该代理因重复出口 IP 被禁用，仍保留在代理池中以避免重复加入。',
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: false,
                canTest: false,
                canCooldown: false,
                canRecall: false,
                testTitle: '去重禁用代理不可测试',
                cooldownTitle: '去重禁用代理不参与冷却',
                recallTitle: '去重禁用代理不参与召回',
            };
        }

        if (!this.isProxyRuntimeLoaded(proxy)) {
            const reason = this.getProxyRuntimeLoadReason(proxy);
            return {
                stateClass: 'runtime-unavailable',
                stateLabel: '未加载到Xray',
                sourceLabel: 'runtime',
                note: reason,
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: false,
                canCooldown: false,
                canRecall: false,
                testTitle: reason,
                cooldownTitle: reason,
                recallTitle: reason,
            };
        }

        if (!this.currentWorkspaceId) {
            return {
                stateClass: 'unscoped',
                stateLabel: '未选择 workspace',
                sourceLabel: '',
                note: '请选择一个已有 workspace 后再做手动管理。',
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: true,
                canCooldown: false,
                canRecall: false,
                cooldownTitle: '请先选择具体 workspace 后再手动冷却',
                recallTitle: '当前不在冷却状态',
            };
        }

        if (this.isAllWorkspacesSelected()) {
            const activeLease = activeLeaseForPort;
            if (activeLease) {
                return {
                    stateClass: 'leased',
                    stateLabel: '已租约中',
                    sourceLabel: '',
                    note: `${activeLease.workspace_id} 正在使用该代理。`,
                    metrics: metricsDisplay.metrics,
                    metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                    showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                    canCopy: true,
                    canTest: true,
                    canCooldown: false,
                    canRecall: false,
                    cooldownTitle: '租约中代理不可手动冷却',
                    recallTitle: '该代理当前不在冷却状态',
                };
            }

            const globalCooldown = cooldownsForPort.find(
                (item) => item.workspace_id === GLOBAL_WORKSPACE_ID && item.proxy_port === proxy.port
            );
            if (globalCooldown) {
                return {
                    stateClass: 'cooldown',
                    stateLabel: '全局冷却中',
                    sourceLabel: globalCooldown.source === 'manual' ? 'manual' : 'timed',
                    note: globalCooldown.source === 'manual'
                        ? '该代理已被手动加入全局冷却，需手动召回。'
                        : '该代理正处于全局定时冷却，可等待到期或手动召回。',
                    metrics: metricsDisplay.metrics,
                    metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                    showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                    canCopy: true,
                    canTest: true,
                    canCooldown: false,
                    canRecall: true,
                    cooldownTitle: '冷却中代理不可重复冷却',
                };
            }

            return {
                stateClass: 'unscoped',
                stateLabel: '全局视图',
                sourceLabel: '',
                note: '请选择具体 workspace 进行手动冷却；测试全部可使用全局冷却。',
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: true,
                canCooldown: false,
                canRecall: false,
                cooldownTitle: '请先选择具体 workspace 后再手动冷却',
                recallTitle: '当前不在冷却状态',
            };
        }

        const globalCooldown = cooldownsForPort.find(
            (item) => item.workspace_id === GLOBAL_WORKSPACE_ID && item.proxy_port === proxy.port
        );
        if (globalCooldown) {
            return {
                stateClass: 'cooldown',
                stateLabel: '全局冷却中',
                sourceLabel: globalCooldown.source === 'manual' ? 'manual' : 'timed',
                note: '该代理已被全局冷却，请切换到“所有代理”后再召回。',
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: true,
                canCooldown: false,
                canRecall: false,
                cooldownTitle: '全局冷却中代理不可重复冷却',
                recallTitle: '请切换到“所有代理”视图召回',
            };
        }

        const activeLease = activeLeases.find(
            (lease) => lease.workspace_id === this.currentWorkspaceId && lease.proxy_port === proxy.port
        );
        if (activeLease) {
            return {
                stateClass: 'leased',
                stateLabel: '已租约中',
                sourceLabel: '',
                note: `${this.currentWorkspaceId} 正在使用该代理。`,
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: true,
                canCooldown: false,
                canRecall: false,
                cooldownTitle: '租约中代理不可手动冷却',
                recallTitle: '该代理当前不在冷却状态',
            };
        }

        const cooldown = cooldowns.find(
            (item) => item.workspace_id === this.currentWorkspaceId && item.proxy_port === proxy.port
        );
        if (cooldown) {
            const sourceLabel = cooldown.source === 'manual' ? 'manual' : 'timed';
            const note = cooldown.source === 'manual'
                ? `${this.currentWorkspaceId} 已手动冷却该代理，召回后才会恢复。`
                : `${this.currentWorkspaceId} 已进入定时冷却，可等待到期或手动召回。`;
            return {
                stateClass: 'cooldown',
                stateLabel: '冷却中',
                sourceLabel,
                note,
                metrics: metricsDisplay.metrics,
                metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
                showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
                canCopy: true,
                canTest: true,
                canCooldown: false,
                canRecall: true,
                cooldownTitle: '冷却中代理不可重复冷却',
            };
        }

        return {
            stateClass: 'available',
            stateLabel: '可用',
            sourceLabel: '',
            note: `${this.currentWorkspaceId} 可手动冷却该代理。`,
            metrics: metricsDisplay.metrics,
            metricsWorkspaceLabel: metricsDisplay.workspaceLabel,
            showMetricsWorkspaceLabel: metricsDisplay.showWorkspaceLabel,
            canCopy: true,
            canTest: true,
            canCooldown: true,
            canRecall: false,
            recallTitle: '该代理当前不在冷却状态',
        };
    }

    getLeaseMetricEntriesForPort(port) {
        return (this.leaseStats?.proxies_by_usage || [])
            .filter((item) => Number(item?.port) === Number(port));
    }

    rankLeaseMetricEntry(entry) {
        return [
            Number(entry?.usage_count ?? 0),
            Number(entry?.success_count ?? 0),
            -Number(entry?.failure_count ?? 0),
            String(entry?.workspace_id || ''),
        ];
    }

    compareLeaseMetricEntries(a, b) {
        const left = this.rankLeaseMetricEntry(a);
        const right = this.rankLeaseMetricEntry(b);
        for (let index = 0; index < left.length; index += 1) {
            if (left[index] === right[index]) continue;
            return left[index] > right[index] ? -1 : 1;
        }
        return 0;
    }

    buildEmptyLeaseMetrics() {
        return {
            usage_count: 0,
            success_count: 0,
            failure_count: 0,
            last_used_at: null,
        };
    }

    getProxyMetricsDisplay(proxy, context = {}) {
        const entries = this.getLeaseMetricEntriesForPort(proxy.port);
        const activeLease = context.activeLease || null;
        const cooldowns = Array.isArray(context.cooldowns) ? context.cooldowns : [];

        if (!this.currentWorkspaceId) {
            return {
                metrics: entries[0] || this.buildEmptyLeaseMetrics(),
                workspaceLabel: entries[0]?.workspace_id ? this.getWorkspaceDisplayLabel(entries[0].workspace_id) : null,
                showWorkspaceLabel: Boolean(entries[0]?.workspace_id),
            };
        }

        if (!this.isAllWorkspacesSelected()) {
            const entry = entries.find((item) => item.workspace_id === this.currentWorkspaceId);
            return {
                metrics: entry || this.buildEmptyLeaseMetrics(),
                workspaceLabel: this.currentWorkspaceId,
                showWorkspaceLabel: false,
            };
        }

        const preferredWorkspaceId = activeLease?.workspace_id
            || cooldowns.find((item) => item.workspace_id !== GLOBAL_WORKSPACE_ID)?.workspace_id
            || null;
        const preferredEntry = preferredWorkspaceId
            ? entries.find((item) => item.workspace_id === preferredWorkspaceId)
            : null;
        const fallbackEntry = entries.slice().sort((a, b) => this.compareLeaseMetricEntries(a, b))[0] || null;
        const entry = preferredEntry || fallbackEntry;

        return {
            metrics: entry || this.buildEmptyLeaseMetrics(),
            workspaceLabel: (entry?.workspace_id || preferredWorkspaceId)
                ? this.getWorkspaceDisplayLabel(entry?.workspace_id || preferredWorkspaceId)
                : null,
            showWorkspaceLabel: Boolean(entry?.workspace_id || preferredWorkspaceId),
        };
    }

    /**
     * Handle proxy item click
     */
    async handleProxyClick(e) {
        const item = e.target.closest('.proxy-item');
        if (!item) return;

        const button = e.target.closest('button');
        if (button?.disabled) return;

        const action = e.target.closest('[data-action]')?.dataset.action;
        const port = parseInt(item.dataset.port);

        if (action === 'copy') {
            await this.copyProxyAddress(port);
        } else if (action === 'test') {
            await this.testSingleProxy(port);
        } else if (action === 'cooldown') {
            await this.setManualCooldown(port);
        } else if (action === 'recall') {
            await this.recallCooldown(port);
        } else if (action === 'remove') {
            await this.removeProxy(port);
        }
    }

    async handleCooldownListClick(e) {
        const button = e.target.closest('[data-action="recall"]');
        if (!button || button.disabled) return;

        const item = e.target.closest('.lease-item');
        if (!item) return;

        const port = parseInt(item.dataset.port, 10);
        const workspaceId = item.dataset.workspaceId || null;
        if (Number.isNaN(port)) return;

        await this.recallCooldown(port, workspaceId);
    }

    /**
     * Copy proxy address to clipboard
     */
    async copyProxyAddress(port) {
        const proxy = this.getProxyByPort(port);
        if (proxy?.pool_status === 'dedupe_disabled') {
            Components.showToast('该代理已被去重禁用，当前不提供可用出口地址', 'warning');
            return;
        }
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
        const proxy = this.getProxyByPort(port);
        if (proxy?.pool_status === 'dedupe_disabled') {
            Components.showToast('该代理已被去重禁用，不能参与测试', 'warning');
            return;
        }
        if (proxy && !this.isProxyRuntimeLoaded(proxy)) {
            Components.showToast(this.getProxyRuntimeLoadReason(proxy), 'warning');
            return;
        }
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

    async setManualCooldown(port) {
        const proxy = this.getProxyByPort(port);
        if (proxy?.pool_status === 'dedupe_disabled') {
            Components.showToast('去重禁用代理不参与冷却管理', 'warning');
            return;
        }
        if (proxy && !this.isProxyRuntimeLoaded(proxy)) {
            Components.showToast(this.getProxyRuntimeLoadReason(proxy), 'warning');
            return;
        }
        if (!this.currentWorkspaceId) {
            Components.showToast('请先选择一个 workspace', 'warning');
            return;
        }

        if (this.isAllWorkspacesSelected()) {
            Components.showToast('请选择具体 workspace 后再手动冷却', 'warning');
            return;
        }

        try {
            await api.setManualLeaseCooldown(this.currentWorkspaceId, port);
            await this.refreshLeaseData();
            Components.showToast(`已为 ${this.currentWorkspaceId} 冷却代理 :${port}`, 'success');
        } catch (error) {
            Components.showToast(`冷却失败: ${error.message}`, 'error');
        }
    }

    async recallCooldown(port, workspaceId = null) {
        const proxy = this.getProxyByPort(port);
        if (proxy?.pool_status === 'dedupe_disabled') {
            Components.showToast('去重禁用代理不参与召回', 'warning');
            return;
        }
        if (proxy && !this.isProxyRuntimeLoaded(proxy)) {
            Components.showToast(this.getProxyRuntimeLoadReason(proxy), 'warning');
            return;
        }

        const selectedWorkspaceId = workspaceId || this.currentWorkspaceId;
        if (!selectedWorkspaceId) {
            Components.showToast('请先选择一个 workspace', 'warning');
            return;
        }

        const targetWorkspaceId = selectedWorkspaceId === ALL_WORKSPACES_ID
            ? GLOBAL_WORKSPACE_ID
            : selectedWorkspaceId;

        try {
            await api.recallLeaseCooldown(targetWorkspaceId, port);
            await this.refreshLeaseData();
            Components.showToast(`已召回 ${this.getWorkspaceDisplayLabel(targetWorkspaceId)} 的代理 :${port}`, 'success');
        } catch (error) {
            Components.showToast(`召回失败: ${error.message}`, 'error');
        }
    }


    async resetCurrentWorkspace() {
        if (!this.currentWorkspaceId) {
            Components.showToast('请先选择一个 workspace', 'warning');
            return;
        }

        if (this.isAllWorkspacesSelected()) {
            Components.showToast('“所有代理”视图不支持复位，请先切换到具体 workspace', 'warning');
            return;
        }

        const workspaceId = this.currentWorkspaceId;
        const confirmed = confirm(`确定要复位 workspace ${workspaceId} 吗？这会清空它的活跃租约和冷却记录。`);
        if (!confirmed) {
            return;
        }

        const clearMetrics = confirm(`是否同时清空 workspace ${workspaceId} 的使用/成功/失败统计？\n选择“确定”会一并清空统计；选择“取消”仅复位租约与冷却。`);

        try {
            const result = await api.resetWorkspaceLeaseState(workspaceId, clearMetrics);
            await this.refreshLeaseData();
            Components.showToast(
                `已复位 ${workspaceId}，释放 ${result.released_count} 个租约，召回 ${result.recalled_count} 个冷却${clearMetrics ? `，清空 ${result.cleared_metric_entries} 条统计` : ''}`,
                'success'
            );
        } catch (error) {
            Components.showToast(`复位失败: ${error.message}`, 'error');
        }
    }

    /**
     * Test all proxies
     */
    async testAllProxies() {
        if (this.getEnabledProxies().length === 0) {
            Components.showToast('当前没有可测试的有效代理', 'warning');
            return;
        }
        if (this.xrayStatus !== 'running') {
            Components.showToast('请先启动 Xray', 'warning');
            return;
        }

        const scope = this.getTestCooldownScope();
        const useCooldown = Boolean(this.elements.testCooldownEnabled?.checked && scope);
        const capturedScope = useCooldown ? scope : null;
        const attempts = useCooldown ? Math.max(1, parseInt(this.elements.testCooldownAttempts?.value, 10) || 2) : 1;
        const cooldownSeconds = useCooldown ? Math.max(1, parseInt(this.elements.testCooldownSeconds?.value, 10) || 300) : 300;
        this.pendingTestCooldownReview = null;

        this.elements.btnTestAll.disabled = true;
        this.elements.btnTestAll.innerHTML = `
            <div class="spinner-sm"></div>
            测试中...
        `;

        try {
            const result = await api.testAllProxies(5, 20, attempts);
            await this.loadProxies();

            if (useCooldown && capturedScope) {
                const candidates = result.cooldown_candidates || [];
                if (candidates.length > 0) {
                    this.openTestCooldownReviewModal({
                        scopeId: capturedScope.scopeId,
                        scopeLabel: capturedScope.scopeLabel,
                        attempts,
                        cooldownSeconds,
                        candidates,
                    });
                }
                Components.showToast(
                    `测试完成: ${result.success_count} 成功, ${result.failed_count} 失败，候选冷却 ${candidates.length} 个`,
                    result.failed_count === 0 ? 'success' : 'warning'
                );
            } else {
                Components.showToast(
                    `测试完成: ${result.success_count} 成功, ${result.failed_count} 失败`,
                    result.failed_count === 0 ? 'success' : 'warning'
                );
            }
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
        this.elements.btnTestAll.disabled = this.getEnabledProxies().length === 0 || !isRunning;
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

    // ==================== Health Monitoring ====================

    /**
     * Refresh health status for all proxies
     */
    async refreshHealthStatus() {
        if (this.getEnabledProxies().length === 0) {
            this.healthStates = {};
            this.updateProxyHealthDisplay();
            return;
        }

        try {
            const data = await api.getHealthStatus();

            // Build health states map
            this.healthStates = {};
            (data.states || []).forEach(state => {
                this.healthStates[state.proxy_port] = state;
            });

            // Update proxy display
            this.updateProxyHealthDisplay();
        } catch (error) {
            console.error('Failed to refresh health status:', error);
        }
    }

    /**
     * Get health state for a specific port
     */
    getHealthForPort(port) {
        return this.healthStates[port] || { status: 'healthy', failure_count: 0 };
    }

    /**
     * Update proxy items with health status
     */
    updateProxyHealthDisplay() {
        document.querySelectorAll('.proxy-item').forEach(item => {
            const port = parseInt(item.dataset.port);
            const proxy = this.getProxyByPort(port);
            const health = this.getHealthForPort(port);

            // Update or create health indicator
            let indicator = item.querySelector('.health-indicator');
            if (!indicator) {
                indicator = document.createElement('span');
                indicator.className = 'health-indicator';
                const portEl = item.querySelector('.proxy-port');
                if (portEl) {
                    portEl.insertAdjacentElement('afterend', indicator);
                }
            }

            if (proxy?.pool_status === 'dedupe_disabled') {
                indicator.className = 'health-indicator dedupe-disabled';
                indicator.title = '去重禁用';
                return;
            }

            if (!this.isProxyRuntimeLoaded(proxy)) {
                indicator.className = 'health-indicator runtime-unavailable';
                indicator.title = `未加载到 Xray | ${this.getProxyRuntimeLoadReason(proxy)}`;
                return;
            }

            indicator.className = `health-indicator ${health.status}`;
            indicator.title = this.getHealthTooltip(health);
        });
    }

    /**
     * Get tooltip text for health indicator
     */
    getHealthTooltip(health) {
        const statusTexts = {
            healthy: '健康',
            degraded: '降级',
            disabled: '禁用'
        };

        let tooltip = statusTexts[health.status] || health.status;

        if (health.status === 'disabled' && health.penalty_remaining_seconds) {
            tooltip += ` (剩余 ${this.formatPenaltyTime(health.penalty_remaining_seconds)})`;
        }

        if (health.last_latency_ms) {
            tooltip += ` | 延迟: ${health.last_latency_ms}ms`;
        }

        const category = (health.last_error_category || '').trim();
        const message = (health.last_error_message || '').trim();
        if (category) {
            const categoryLabelMap = {
                runtime_unavailable: '运行不可用',
                probe_failed: '探测失败',
            };
            tooltip += ` | 分类: ${categoryLabelMap[category] || category}`;
        }
        if (message) {
            tooltip += ` | ${message}`;
        }

        return tooltip;
    }

    /**
     * Format penalty time remaining
     */
    formatPenaltyTime(seconds) {
        if (seconds < 60) {
            return `${seconds}秒`;
        } else if (seconds < 3600) {
            return `${Math.ceil(seconds / 60)}分钟`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const mins = Math.ceil((seconds % 3600) / 60);
            return `${hours}小时${mins}分钟`;
        }
    }

    /**
     * Reset health state for a proxy
     */
    async resetProxyHealth(port) {
        const proxy = this.getProxyByPort(port);
        if (proxy?.pool_status === 'dedupe_disabled') {
            Components.showToast('去重禁用代理不参与健康状态管理', 'warning');
            return;
        }
        try {
            await api.resetProxyHealth(port);
            await this.refreshHealthStatus();
            Components.showToast(`端口 ${port} 健康状态已重置`, 'success');
        } catch (error) {
            Components.showToast(`重置失败: ${error.message}`, 'error');
        }
    }

    /**
     * Show context menu for proxy
     */
    showProxyContextMenu(e, port) {
        e.preventDefault();

        // Remove existing context menu
        const existing = document.querySelector('.context-menu');
        if (existing) existing.remove();

        const health = this.getHealthForPort(port);
        const proxy = this.getProxyByPort(port);
        const runtimeReady = proxy ? this.isProxyRuntimeLoaded(proxy) : true;

        const menu = document.createElement('div');
        menu.className = 'context-menu active';
        menu.style.left = `${e.clientX}px`;
        menu.style.top = `${e.clientY}px`;

        menu.innerHTML = `
            <div class="context-menu-item" data-action="copy">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                复制地址
            </div>
            <div class="context-menu-item${runtimeReady ? '' : ' disabled'}" data-action="test">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                测试连通性
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item${runtimeReady ? '' : ' disabled'}" data-action="reset-health">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
                    <path d="M21 3v5h-5"></path>
                    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
                    <path d="M8 16H3v5"></path>
                </svg>
                重置健康状态
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item danger" data-action="remove">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                移除代理
            </div>
        `;

        document.body.appendChild(menu);

        // Handle menu item clicks
        menu.addEventListener('click', async (e) => {
            const item = e.target.closest('.context-menu-item');
            if (!item) return;
            if (item.classList.contains('disabled')) return;

            const action = item.dataset.action;
            menu.remove();

            if (action === 'copy') {
                await this.copyProxyAddress(port);
            } else if (action === 'test') {
                await this.testSingleProxy(port);
            } else if (action === 'reset-health') {
                await this.resetProxyHealth(port);
            } else if (action === 'remove') {
                await this.removeProxy(port);
            }
        });

        // Close menu on click outside
        const closeMenu = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    }

    // ==================== Lease Management ====================

    /**
     * Switch between Proxies and Leases tabs
     */
    switchTab(tabName) {
        if (this.currentTab === tabName) return;
        this.currentTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        // Load lease data when switching to leases tab
        if (tabName === 'leases') {
            this.syncLeasePlaygroundState();
            this.refreshLeaseData();
        }
    }

    toggleLeasePlayground() {
        this.isLeasePlaygroundCollapsed = !this.isLeasePlaygroundCollapsed;
        localStorage.setItem(
            LEASE_PLAYGROUND_COLLAPSED_STORAGE_KEY,
            this.isLeasePlaygroundCollapsed ? 'true' : 'false'
        );
        this.syncLeasePlaygroundState();
    }

    syncLeasePlaygroundState() {
        const playground = this.elements.leasePlayground;
        const toggleButton = this.elements.btnToggleLeasePlayground;
        if (!playground || !toggleButton) return;

        playground.classList.toggle('collapsed', this.isLeasePlaygroundCollapsed);
        toggleButton.setAttribute('aria-expanded', this.isLeasePlaygroundCollapsed ? 'false' : 'true');

        const textEl = toggleButton.querySelector('.lease-playground-toggle-text');
        if (textEl) {
            textEl.textContent = this.isLeasePlaygroundCollapsed ? '展开' : '收起';
        }
    }

    /**
     * Refresh lease data (stats + status)
     */
    async refreshLeaseData() {
        try {
            const [stats, status] = await Promise.all([
                api.getLeaseStats(),
                api.getLeaseStatus()
            ]);

            this.leaseStats = stats || { proxies_by_usage: [] };
            this.leaseStatus = {
                active_leases: status.active_leases || [],
                cooldowns: status.cooldowns || [],
                workspaces: status.workspaces || [],
                total_active: status.total_active || 0,
                total_cooldowns: status.total_cooldowns || 0,
            };
            this.syncCurrentWorkspace();
            this.renderLeaseStats(stats);
            this.renderWorkspaceSelector();
            this.renderCurrentWorkspaceLeaseViews();
            this.renderProxies();
        } catch (error) {
            console.error('Failed to refresh lease data:', error);
        }
    }

    /**
     * Render lease statistics dashboard
     */
    renderLeaseStats(stats) {
        const availableEl = document.getElementById('lease-available');
        const activeEl = document.getElementById('lease-active');
        const cooldownEl = document.getElementById('lease-cooldown');

        if (availableEl) availableEl.textContent = stats.total_available_proxies ?? '-';
        if (activeEl) activeEl.textContent = stats.total_active_leases ?? '-';
        if (cooldownEl) cooldownEl.textContent = stats.total_cooldowns ?? '-';
    }

    syncCurrentWorkspace() {
        const workspaces = this.leaseStatus.workspaces || [];
        const isValidAll = this.currentWorkspaceId === ALL_WORKSPACES_ID;
        const exists = workspaces.some((item) => item.workspace_id === this.currentWorkspaceId);
        if (isValidAll || (this.currentWorkspaceId && exists)) {
            return;
        }

        const nextWorkspace = ALL_WORKSPACES_ID;
        this.setCurrentWorkspace(nextWorkspace, { persist: true, rerender: false });
    }

    setCurrentWorkspace(workspaceId, { persist = true, rerender = true } = {}) {
        this.currentWorkspaceId = workspaceId || null;

        if (persist) {
            if (this.currentWorkspaceId) {
                localStorage.setItem('xray-prism.currentWorkspaceId', this.currentWorkspaceId);
            } else {
                localStorage.removeItem('xray-prism.currentWorkspaceId');
            }
        }

        if (rerender) {
            this.renderWorkspaceSelector();
            this.renderCurrentWorkspaceLeaseViews();
            this.renderProxies();
        }
    }

    renderWorkspaceSelector() {
        const container = this.elements.workspaceChipList;
        const title = this.elements.currentWorkspaceName;
        const hint = this.elements.workspaceBarHint;
        if (!container || !title || !hint) return;

        const resetButton = this.elements.btnResetWorkspace;
        const workspaces = this.leaseStatus.workspaces || [];
        const currentSummary = workspaces.find((item) => item.workspace_id === this.currentWorkspaceId) || null;
        const allWorkspaceSelected = this.isAllWorkspacesSelected();
        const totalCount = this.proxies.length;

        if (allWorkspaceSelected) {
            title.textContent = '所有代理';
            hint.textContent = workspaces.length === 0
                ? '当前无 workspace 记录；仍可在此视图下测试所有代理，并选择对失败代理执行全局冷却。'
                : `全量代理视图：活跃 ${this.leaseStatus.total_active || 0} / 冷却 ${this.leaseStatus.total_cooldowns || 0}。测试全部可使用全局冷却。`;
            if (resetButton) {
                resetButton.disabled = true;
            }
        } else if (!this.currentWorkspaceId || !currentSummary) {
            title.textContent = '未选择';
            hint.textContent = workspaces.length === 0
                ? '暂无活跃租约或冷却记录，创建租约后会出现在这里。'
                : '请选择一个 workspace 查看对应的租约和代理状态。';
            if (resetButton) {
                resetButton.disabled = true;
            }
        } else {
            title.textContent = currentSummary.workspace_id;
            hint.textContent = `活跃 ${currentSummary.active_count} / 冷却 ${currentSummary.cooldown_count}`;
            if (resetButton) {
                resetButton.disabled = false;
            }
        }

        const chips = [
            `
                <button class="workspace-chip${allWorkspaceSelected ? ' active' : ''}" data-workspace-id="${ALL_WORKSPACES_ID}">
                    <span>所有代理</span>
                    <span class="workspace-chip-count">${totalCount}</span>
                </button>
            `,
            ...workspaces.map((workspace) => {
            const total = (workspace.active_count || 0) + (workspace.cooldown_count || 0);
            const active = workspace.workspace_id === this.currentWorkspaceId ? ' active' : '';
            return `
                <button class="workspace-chip${active}" data-workspace-id="${this.escapeHtml(workspace.workspace_id)}">
                    <span>${this.escapeHtml(workspace.workspace_id)}</span>
                    <span class="workspace-chip-count">${total}</span>
                </button>
            `;
            }),
        ];

        if (workspaces.length === 0) {
            chips.push('<div class="workspace-empty">暂无具体 workspace，当前可使用“所有代理”视图。</div>');
        }

        container.innerHTML = chips.join('');
        this.updateTestCooldownControls();
    }

    renderCurrentWorkspaceLeaseViews() {
        const workspaceName = this.getCurrentWorkspaceLabel();
        const activeCaption = document.getElementById('active-lease-caption');
        const cooldownCaption = document.getElementById('cooldown-caption');
        if (activeCaption) activeCaption.textContent = workspaceName;
        if (cooldownCaption) cooldownCaption.textContent = workspaceName;

        if (!this.currentWorkspaceId) {
            this.renderActiveLeases([]);
            this.renderCooldownPool([]);
            return;
        }

        const activeLeases = this.isAllWorkspacesSelected()
            ? (this.leaseStatus.active_leases || [])
            : (this.leaseStatus.active_leases || []).filter(
                (lease) => lease.workspace_id === this.currentWorkspaceId
            );
        const cooldowns = this.isAllWorkspacesSelected()
            ? (this.leaseStatus.cooldowns || [])
            : (this.leaseStatus.cooldowns || []).filter(
                (cooldown) => cooldown.workspace_id === this.currentWorkspaceId || cooldown.workspace_id === GLOBAL_WORKSPACE_ID
            );

        this.renderActiveLeases(activeLeases);
        this.renderCooldownPool(cooldowns);
    }

    /**
     * Render active leases list
     */
    renderActiveLeases(leases) {
        const container = document.getElementById('active-leases-list');
        if (!container) return;

        if (!this.currentWorkspaceId) {
            container.innerHTML = `
                <div class="empty-state small">
                    <p>请选择 workspace 后查看活跃租约</p>
                </div>
            `;
            return;
        }

        if (leases.length === 0) {
            container.innerHTML = `
                <div class="empty-state small">
                    <p>${this.isAllWorkspacesSelected() ? '当前没有活跃租约' : '当前 workspace 暂无活跃租约'}</p>
                </div>
            `;
            return;
        }

        container.innerHTML = leases.map(lease => {
            const expiresAt = new Date(lease.expires_at);
            const now = new Date();
            const remainingSeconds = Math.max(0, Math.floor((expiresAt - now) / 1000));
            const isExpiring = remainingSeconds < 30;
            const nodeName = lease.node_name || `代理 :${lease.proxy_port}`;
            const metaParts = [];
            if (this.isAllWorkspacesSelected()) {
                metaParts.push(`工作区: ${lease.workspace_id}`);
            }
            metaParts.push(`ID: ${lease.lease_id.slice(0, 8)}...`);

            return `
                <div class="lease-item" data-lease-id="${lease.lease_id}">
                    <span class="lease-item-port">${lease.proxy_port}</span>
                    <div class="lease-item-info">
                        <span class="lease-item-title">${this.escapeHtml(nodeName)}</span>
                        <span class="lease-item-meta">${this.escapeHtml(metaParts.join(' · '))}</span>
                        ${this.renderLeaseMetrics(lease.metrics)}
                    </div>
                    <span class="lease-item-timer${isExpiring ? ' expiring' : ''}">${this.formatTime(remainingSeconds)}</span>
                </div>
            `;
        }).join('');
    }

    /**
     * Render cooldown pool list
     */
    renderCooldownPool(cooldowns) {
        const container = document.getElementById('cooldown-list');
        if (!container) return;

        if (!this.currentWorkspaceId) {
            container.innerHTML = `
                <div class="empty-state small">
                    <p>请选择 workspace 后查看冷却代理</p>
                </div>
            `;
            return;
        }

        if (cooldowns.length === 0) {
            container.innerHTML = `
                <div class="empty-state small">
                    <p>${this.isAllWorkspacesSelected() ? '当前没有冷却中的代理' : '当前 workspace 无冷却中的代理'}</p>
                </div>
            `;
            return;
        }

        container.innerHTML = cooldowns.map(cd => {
            const until = cd.until ? new Date(cd.until) : null;
            const now = new Date();
            const remainingSeconds = until ? Math.max(0, Math.floor((until - now) / 1000)) : null;
            const timerLabel = cd.source === 'manual'
                ? '手动召回'
                : this.formatTime(remainingSeconds ?? 0);
            const nodeName = cd.node_name || `代理 :${cd.proxy_port}`;
            const scopeLabel = cd.workspace_id === GLOBAL_WORKSPACE_ID ? '全局冷却' : `工作区: ${cd.workspace_id}`;
            const metaParts = [scopeLabel, cd.source === 'manual' ? '手动冷却' : '定时冷却'];

            return `
                <div class="lease-item" data-port="${cd.proxy_port}" data-workspace-id="${this.escapeHtml(cd.workspace_id)}">
                    <span class="lease-item-port">${cd.proxy_port}</span>
                    <div class="lease-item-info">
                        <span class="lease-item-title">${this.escapeHtml(nodeName)}</span>
                        <span class="lease-item-meta">${this.escapeHtml(metaParts.join(' · '))}</span>
                        ${this.renderLeaseMetrics(cd.metrics)}
                    </div>
                    <div class="lease-item-actions">
                        <span class="lease-item-timer">${timerLabel}</span>
                        <button class="btn btn-icon btn-sm" data-action="recall" title="召回冷却">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 12a9 9 0 1 1-2.64-6.36"></path>
                                <polyline points="21 3 21 9 15 9"></polyline>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    isAllWorkspacesSelected() {
        return this.currentWorkspaceId === ALL_WORKSPACES_ID;
    }

    getCurrentWorkspaceLabel() {
        return this.isAllWorkspacesSelected() ? '所有代理' : (this.currentWorkspaceId || '所有代理');
    }

    getWorkspaceDisplayLabel(workspaceId) {
        if (workspaceId === GLOBAL_WORKSPACE_ID) {
            return '所有代理（全局冷却）';
        }
        if (workspaceId === ALL_WORKSPACES_ID) {
            return '所有代理';
        }
        return workspaceId || '所有代理';
    }

    renderLeaseMetrics(metrics) {
        const usageCount = Number(metrics?.usage_count ?? 0);
        const successCount = Number(metrics?.success_count ?? 0);
        const failureCount = Number(metrics?.failure_count ?? 0);
        return `
            <div class="lease-item-metrics">
                <span class="lease-metric usage">用 ${usageCount}</span>
                <span class="lease-metric success">成 ${successCount}</span>
                <span class="lease-metric failure">败 ${failureCount}</span>
            </div>
        `;
    }

    getTestCooldownScope() {
        if (!this.currentWorkspaceId) {
            return {
                scopeId: GLOBAL_WORKSPACE_ID,
                scopeLabel: '所有代理（全局冷却）',
            };
        }
        if (this.isAllWorkspacesSelected()) {
            return {
                scopeId: GLOBAL_WORKSPACE_ID,
                scopeLabel: '所有代理（全局冷却）',
            };
        }
        return {
            scopeId: this.currentWorkspaceId,
            scopeLabel: this.currentWorkspaceId,
        };
    }

    /**
     * Playground: Acquire a lease
     */
    async playgroundAcquire() {
        const workspaceInput = document.getElementById('pg-workspace');
        const ttlInput = document.getElementById('pg-ttl');
        const resultEl = document.getElementById('pg-result');

        const workspaceId = workspaceInput?.value.trim();
        const ttl = parseInt(ttlInput?.value) || 60;

        if (!workspaceId) {
            this.showPlaygroundResult({ error: 'Workspace ID is required' }, false);
            return;
        }

        try {
            const result = await api.acquireLease(workspaceId, ttl);
            this.showPlaygroundResult(result, true);

            // Auto-fill proxy address for release
            if (result.proxy_address) {
                const proxyAddressInput = document.getElementById('pg-proxy-address');
                if (proxyAddressInput) proxyAddressInput.value = result.proxy_address;
            }

            // Refresh data
            await this.refreshLeaseData();
            this.setCurrentWorkspace(workspaceId);
        } catch (error) {
            this.showPlaygroundResult({ error: error.message }, false);
        }
    }

    /**
     * Playground: Release a lease
     */
    async playgroundRelease() {
        const workspaceInput = document.getElementById('pg-workspace');
        const proxyAddressInput = document.getElementById('pg-proxy-address');
        const resultEl = document.getElementById('pg-result');

        const workspaceId = workspaceInput?.value.trim();
        const proxyAddress = proxyAddressInput?.value.trim();

        if (!workspaceId || !proxyAddress) {
            this.showPlaygroundResult({ error: 'Workspace ID and Proxy Address are required' }, false);
            return;
        }

        try {
            const result = await api.releaseLease(workspaceId, proxyAddress, 300);
            this.showPlaygroundResult(result, true);

            // Refresh data
            await this.refreshLeaseData();
            if ((this.leaseStatus.workspaces || []).some((item) => item.workspace_id === workspaceId)) {
                this.setCurrentWorkspace(workspaceId);
            }
        } catch (error) {
            this.showPlaygroundResult({ error: error.message }, false);
        }
    }

    /**
     * Show playground result
     */
    showPlaygroundResult(result, success) {
        const resultEl = document.getElementById('pg-result');
        if (!resultEl) return;

        resultEl.textContent = JSON.stringify(result, null, 2);
        resultEl.className = `playground-result ${success ? 'success' : 'error'}`;
    }

    /**
     * Format seconds to MM:SS
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
