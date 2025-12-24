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

    // ==================== Nodes ====================

    /**
     * Get a single node
     * @param {string} nodeId - Node ID
     * @returns {Promise<object>}
     */
    async getNode(nodeId) {
        return this.request(`/nodes/${nodeId}`);
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
     * Test all proxies
     * @param {number} timeout - Timeout in seconds
     * @param {number} workers - Number of concurrent workers
     * @returns {Promise<{results: Array, success_count: number, failed_count: number}>}
     */
    async testAllProxies(timeout = 5, workers = 20) {
        return this.request(`/proxies/test-all?timeout=${timeout}&workers=${workers}`, {
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
}

// Export singleton instance
const api = new ApiClient();
