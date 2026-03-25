/**
 * API Client for Xray-Prism
 * Handles all HTTP requests to the backend API
 */

const API_BASE = '/api';

class ApiClient {
    /**
     * Make an HTTP request
     * @param {string} endpoint - API endpoint
     * @param {object} options - Fetch options
     * @returns {Promise<any>} Response data
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // ==================== Subscriptions ====================

    /**
     * Get all subscriptions
     * @returns {Promise<{subscriptions: Array, total: number}>}
     */
    async getSubscriptions() {
        return this.request('/subscriptions');
    }

    /**
     * Create a new subscription
     * @param {string} name - Subscription name
     * @param {string} url - Subscription URL
     * @returns {Promise<object>} Created subscription
     */
    async createSubscription(name, url) {
        return this.request('/subscriptions', {
            method: 'POST',
            body: JSON.stringify({ name, url }),
        });
    }

    /**
     * Delete a subscription
     * @param {string} subId - Subscription ID
     * @returns {Promise<object>}
     */
    async deleteSubscription(subId) {
        return this.request(`/subscriptions/${subId}`, {
            method: 'DELETE',
        });
    }

    /**
     * Refresh a subscription's nodes
     * @param {string} subId - Subscription ID
     * @returns {Promise<object>} Updated subscription
     */
    async refreshSubscription(subId) {
        return this.request(`/subscriptions/${subId}/refresh`, {
            method: 'POST',
        });
    }

    /**
     * Get nodes for a subscription
     * @param {string} subId - Subscription ID
     * @returns {Promise<{nodes: Array, total: number}>}
     */
    async getSubscriptionNodes(subId) {
        return this.request(`/subscriptions/${subId}/nodes`);
    }

    // ==================== Custom Groups ====================

    /**
     * Get all custom groups
     * @returns {Promise<{groups: Array, total: number}>}
     */
    async getCustomGroups() {
        return this.request('/custom-groups');
    }

    /**
     * Create a custom group
     * @param {string} name - Group name
     * @returns {Promise<object>}
     */
    async createCustomGroup(name) {
        return this.request('/custom-groups', {
            method: 'POST',
            body: JSON.stringify({ name }),
        });
    }

    /**
     * Rename a custom group
     * @param {string} groupId - Group ID
     * @param {string} name - New group name
     * @returns {Promise<object>}
     */
    async renameCustomGroup(groupId, name) {
        return this.request(`/custom-groups/${groupId}`, {
            method: 'PATCH',
            body: JSON.stringify({ name }),
        });
    }

    /**
     * Delete a custom group
     * @param {string} groupId - Group ID
     * @returns {Promise<object>}
     */
    async deleteCustomGroup(groupId) {
        return this.request(`/custom-groups/${groupId}`, {
            method: 'DELETE',
        });
    }

    /**
     * Get nodes for a custom group
     * @param {string} groupId - Group ID
     * @returns {Promise<{nodes: Array, total: number}>}
     */
    async getCustomGroupNodes(groupId) {
        return this.request(`/custom-groups/${groupId}/nodes`);
    }

    /**
     * Import pasted nodes into a custom group
     * @param {string} groupId - Group ID
     * @param {string} content - Multi-line node content
     * @returns {Promise<object>}
     */
    async importCustomGroupNodes(groupId, content) {
        return this.request(`/custom-groups/${groupId}/nodes/import`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        });
    }

    /**
     * Copy node snapshots into a custom group
     * @param {string} groupId - Group ID
     * @param {string[]} sourceNodeIds - Source node IDs
     * @returns {Promise<object>}
     */
    async copyNodesToCustomGroup(groupId, sourceNodeIds) {
        return this.request(`/custom-groups/${groupId}/nodes/copy`, {
            method: 'POST',
            body: JSON.stringify({ source_node_ids: sourceNodeIds }),
        });
    }

    /**
     * Delete one node from a custom group
     * @param {string} groupId - Group ID
     * @param {string} nodeId - Node ID
     * @returns {Promise<object>}
     */
    async deleteCustomGroupNode(groupId, nodeId) {
        return this.request(`/custom-groups/${groupId}/nodes/${nodeId}`, {
            method: 'DELETE',
        });
    }

    // ==================== Nodes ====================

    /**
     * Get a single node
     * @param {string} nodeId - Node ID
     * @returns {Promise<object>}
     */
    async getNode(nodeId) {
        return this.request(`/nodes/${nodeId}`);
    }

    /**
     * Test one or multiple nodes without adding them to proxy pool
     * @param {string[]} nodeIds - Node IDs to test
     * @param {number} timeout - Timeout in seconds
     * @param {string} testProfile - Test profile, defaults to multi_target
     * @returns {Promise<{results: Array, success_count: number, failed_count: number, test_profile: string}>}
     */
    async testNodes(nodeIds, timeout = 5, testProfile = 'multi_target') {
        return this.request('/nodes/test', {
            method: 'POST',
            body: JSON.stringify({
                node_ids: nodeIds,
                timeout,
                test_profile: testProfile,
            }),
        });
    }

    /**
     * Start an asynchronous node test job
     * @param {string[]} nodeIds - Node IDs to test
     * @param {number} timeout - Timeout in seconds
     * @param {string} testProfile - Test profile, defaults to multi_target
     * @returns {Promise<object>}
     */
    async startNodeTestJob(nodeIds, timeout = 5, testProfile = 'multi_target') {
        return this.request('/nodes/test-jobs', {
            method: 'POST',
            body: JSON.stringify({
                node_ids: nodeIds,
                timeout,
                test_profile: testProfile,
            }),
        });
    }

    /**
     * Poll an asynchronous node test job
     * @param {string} jobId - Test job id
     * @returns {Promise<object>}
     */
    async getNodeTestJob(jobId) {
        return this.request(`/nodes/test-jobs/${jobId}`);
    }

    // ==================== Proxies ====================

    /**
     * Get all active proxies
     * @returns {Promise<{proxies: Array, total: number, xray_status: string}>}
     */
    async getProxies() {
        return this.request('/proxies');
    }

    /**
     * Add nodes to proxy list
     * @param {string[]} nodeIds - Array of node IDs
     * @param {number} startPort - Starting port number
     * @returns {Promise<Array>} Added proxies
     */
    async addProxies(nodeIds, startPort = 10000) {
        return this.request('/proxies', {
            method: 'POST',
            body: JSON.stringify({ node_ids: nodeIds, start_port: startPort }),
        });
    }

    /**
     * Remove a proxy by port
     * @param {number} port - Port number
     * @returns {Promise<object>}
     */
    async removeProxy(port) {
        return this.request(`/proxies/${port}`, {
            method: 'DELETE',
        });
    }

    /**
     * Clear all proxies
     * @returns {Promise<object>}
     */
    async clearProxies() {
        return this.request('/proxies', {
            method: 'DELETE',
        });
    }

    /**
     * Preview duplicate proxies by exit IP
     * @returns {Promise<{groups: Array, duplicate_group_count: number, duplicate_proxy_count: number}>}
     */
    async previewProxyExitIpDuplicates() {
        return this.request('/proxies/duplicates/exit-ip');
    }

    /**
     * Disable duplicate proxies by exit IP after user confirmation
     * @param {number[]} disablePorts - Duplicate proxy ports selected for disabling
     * @returns {Promise<{disabled_count: number, disabled_ports: number[], kept_ports: number[]}>}
     */
    async dedupeProxiesByExitIp(disablePorts) {
        return this.request('/proxies/dedupe/exit-ip', {
            method: 'POST',
            body: JSON.stringify({ disable_ports: disablePorts }),
        });
    }

    /**
     * Test all proxies
     * @param {number} timeout - Timeout in seconds
     * @param {number} workers - Number of concurrent workers
     * @param {number} attempts - Number of retry attempts per proxy
     * @returns {Promise<{results: Array, success_count: number, failed_count: number}>}
     */
    async testAllProxies(timeout = 5, workers = 20, attempts = 1) {
        return this.request(`/proxies/test-all?timeout=${timeout}&workers=${workers}&attempts=${attempts}`, {
            method: 'POST',
        });
    }

    /**
     * Test a single proxy
     * @param {number} port - Port number
     * @param {number} timeout - Timeout in seconds
     * @returns {Promise<object>}
     */
    async testProxy(port, timeout = 5) {
        return this.request(`/proxies/${port}/test?timeout=${timeout}`, {
            method: 'POST',
        });
    }

    // ==================== System ====================

    /**
     * Get system status
     * @returns {Promise<object>}
     */
    async getSystemStatus() {
        return this.request('/system/status');
    }

    /**
     * Start Xray
     * @returns {Promise<object>}
     */
    async startXray() {
        return this.request('/system/start', {
            method: 'POST',
        });
    }

    /**
     * Stop Xray
     * @returns {Promise<object>}
     */
    async stopXray() {
        return this.request('/system/stop', {
            method: 'POST',
        });
    }

    /**
     * Restart Xray
     * @returns {Promise<object>}
     */
    async restartXray() {
        return this.request('/system/restart', {
            method: 'POST',
        });
    }

    // ==================== Health Monitoring ====================

    /**
     * Get health status for all proxies
     * @returns {Promise<{states: Array, total: number, healthy_count: number, degraded_count: number, disabled_count: number}>}
     */
    async getHealthStatus() {
        return this.request('/health/status');
    }

    /**
     * Get health status for a specific proxy
     * @param {number} port - Port number
     * @returns {Promise<object>}
     */
    async getProxyHealthStatus(port) {
        return this.request(`/health/status/${port}`);
    }

    /**
     * Get health monitoring configuration
     * @returns {Promise<object>}
     */
    async getHealthConfig() {
        return this.request('/health/config');
    }

    /**
     * Update health monitoring configuration
     * @param {object} config - Configuration updates
     * @returns {Promise<object>}
     */
    async updateHealthConfig(config) {
        return this.request('/health/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }

    /**
     * Reset health state for a specific proxy
     * @param {number} port - Port number
     * @returns {Promise<object>}
     */
    async resetProxyHealth(port) {
        return this.request(`/health/reset/${port}`, {
            method: 'POST',
        });
    }

    /**
     * Reset health states for all proxies
     * @returns {Promise<object>}
     */
    async resetAllHealth() {
        return this.request('/health/reset-all', {
            method: 'POST',
        });
    }

    /**
     * Manually run a health check
     * @returns {Promise<object>}
     */
    async runHealthCheck() {
        return this.request('/health/check', {
            method: 'POST',
        });
    }

    /**
     * Start background health monitoring
     * @returns {Promise<object>}
     */
    async startHealthMonitoring() {
        return this.request('/health/monitoring/start', {
            method: 'POST',
        });
    }

    /**
     * Stop background health monitoring
     * @returns {Promise<object>}
     */
    async stopHealthMonitoring() {
        return this.request('/health/monitoring/stop', {
            method: 'POST',
        });
    }

    // ==================== Lease API ====================

    /**
     * Get lease statistics
     * @returns {Promise<{total_available_proxies: number, total_active_leases: number, total_cooldowns: number, workspaces: object, proxies_by_usage: Array}>}
     */
    async getLeaseStats() {
        return this.request('/lease/stats');
    }

    /**
     * Get lease status (active leases and cooldowns)
     * @param {string|null} workspaceId - Optional workspace filter
     * @returns {Promise<{active_leases: Array, cooldowns: Array, total_active: number, total_cooldowns: number}>}
     */
    async getLeaseStatus(workspaceId = null) {
        const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
        return this.request(`/lease/status${query}`);
    }

    /**
     * Create a manual cooldown for a workspace and proxy port
     * @param {string} workspaceId - Workspace identifier
     * @param {number} proxyPort - Proxy port
     * @returns {Promise<{success: boolean, workspace_id: string, proxy_port: number, source: string|null}>}
     */
    async setManualLeaseCooldown(workspaceId, proxyPort, result = null) {
        return this.request('/lease/cooldown/manual', {
            method: 'POST',
            body: JSON.stringify({
                workspace_id: workspaceId,
                proxy_port: proxyPort,
                result,
            }),
        });
    }

    /**
     * Recall a cooldown for a workspace and proxy port
     * @param {string} workspaceId - Workspace identifier
     * @param {number} proxyPort - Proxy port
     * @returns {Promise<{success: boolean, workspace_id: string, proxy_port: number, source: string|null}>}
     */
    async recallLeaseCooldown(workspaceId, proxyPort) {
        return this.request('/lease/cooldown/recall', {
            method: 'POST',
            body: JSON.stringify({ workspace_id: workspaceId, proxy_port: proxyPort }),
        });
    }

    /**
     * Apply timed cooldowns to multiple proxy ports within a workspace
     * @param {string} workspaceId - Workspace identifier
     * @param {number[]} proxyPorts - Proxy ports to cool down
     * @param {number} cooldownSeconds - Timed cooldown duration in seconds
     * @returns {Promise<{success: boolean, workspace_id: string, cooldown_seconds: number, applied_ports: number[], skipped_ports: number[]}>}
     */
    async applyTimedLeaseCooldownBatch(workspaceId, proxyPorts, cooldownSeconds = 300, result = null) {
        return this.request('/lease/cooldown/timed/batch', {
            method: 'POST',
            body: JSON.stringify({
                workspace_id: workspaceId,
                proxy_ports: proxyPorts,
                cooldown_seconds: cooldownSeconds,
                result,
            }),
        });
    }

    /**
     * Reset all lease state for a workspace
     * @param {string} workspaceId - Workspace identifier
     * @returns {Promise<{success: boolean, workspace_id: string, released_count: number, recalled_count: number}>}
     */
    async resetWorkspaceLeaseState(workspaceId, clearMetrics = false) {
        return this.request('/lease/workspace/reset', {
            method: 'POST',
            body: JSON.stringify({
                workspace_id: workspaceId,
                clear_metrics: clearMetrics,
            }),
        });
    }

    /**
     * Acquire a proxy lease
     * @param {string} workspaceId - Workspace identifier
     * @param {number} ttl - Time to live in seconds
     * @returns {Promise<{success: boolean, lease_id: string, proxy_address: string, expires_at: string}>}
     */
    async acquireLease(workspaceId, ttl = 60) {
        return this.request('/lease/acquire', {
            method: 'POST',
            body: JSON.stringify({ workspace_id: workspaceId, ttl }),
        });
    }

    /**
     * Release a proxy lease
     * @param {string} workspaceId - Workspace identifier
     * @param {string} proxyAddress - Proxy address to release (e.g. "127.0.0.1:10000")
     * @param {number} cooldownSeconds - Cooldown period in seconds
     * @returns {Promise<{success: boolean, cooldown_until: string|null}>}
     */
    async releaseLease(workspaceId, proxyAddress, cooldownSeconds = 300, result = null) {
        return this.request('/lease/release', {
            method: 'POST',
            body: JSON.stringify({
                workspace_id: workspaceId,
                proxy_address: proxyAddress,
                cooldown_seconds: cooldownSeconds,
                result,
            }),
        });
    }
}

// Export singleton instance
const api = new ApiClient();

