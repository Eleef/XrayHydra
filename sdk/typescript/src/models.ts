/* eslint-disable */
// Typed API payloads generated from the OpenAPI schema.

export interface ActiveLeaseInfo {
  lease_id: string;
  workspace_id: string;
  proxy_port: number;
  node_name?: string | unknown;
  proxy_address: string;
  proxy_scheme: string;
  supported_proxy_protocols: Array<string>;
  http_proxy_url: string;
  socks5_proxy_url: string;
  socks5h_proxy_url: string;
  acquired_at: string;
  expires_at: string;
}

export interface CooldownInfo {
  workspace_id: string;
  proxy_port: number;
  node_name?: string | unknown;
  until: string | unknown;
  set_at: string;
  source: "manual" | "timed";
}

export interface CustomGroupCopyNodesRequest {
  source_node_ids: Array<string>;
}

export interface CustomGroupCopyNodesResponse {
  copied_count: number;
  skipped_duplicates: number;
  total_requested: number;
  missing_node_ids?: Array<string>;
}

export interface CustomGroupCreateRequest {
  name: string;
}

export interface CustomGroupImportRequest {
  content: string;
}

export interface CustomGroupImportResponse {
  imported_count: number;
  skipped_duplicates: number;
  total_parsed: number;
  ignored_unsupported_count?: number;
}

export interface CustomGroupListResponse {
  groups: Array<CustomGroupResponse>;
  total: number;
}

export interface CustomGroupRenameRequest {
  name: string;
}

export interface CustomGroupResponse {
  id: string;
  name: string;
  group_type?: GroupType;
  node_count?: number;
  created_at: string;
  updated_at: string;
}

export interface HealthConfigResponse {
  enabled: boolean;
  check_interval_seconds: number;
  test_target: string;
  test_timeout_seconds: number;
  test_targets_presets: Array<TestTargetPreset>;
  penalty_levels_minutes: Array<number>;
  is_monitoring: boolean;
}

export interface HealthConfigUpdate {
  enabled?: boolean | unknown;
  check_interval_seconds?: number | unknown;
  test_target?: string | unknown;
  test_timeout_seconds?: number | unknown;
}

export interface HealthStatusListResponse {
  states: Array<ProxyHealthResponse>;
  total: number;
  healthy_count: number;
  degraded_count: number;
  disabled_count: number;
}

export interface LeaseAcquireRequest {
  workspace_id: string;
  ttl?: number;
  initial_port_ordering?: 'random' | 'port_asc';
}

export interface LeaseAcquireResponse {
  success?: boolean;
  lease_id: string;
  proxy_address: string;
  proxy_scheme: string;
  supported_proxy_protocols: Array<string>;
  http_proxy_url: string;
  socks5_proxy_url: string;
  socks5h_proxy_url: string;
  expires_at: string;
}

export interface LeaseCooldownActionResponse {
  success?: boolean;
  workspace_id: string;
  proxy_port: number;
  source?: "manual" | "timed" | unknown;
}

export interface LeaseCooldownRequest {
  workspace_id: string;
  proxy_port: number;
}

export interface LeaseReleaseRequest {
  workspace_id: string;
  proxy_address: string;
  cooldown_seconds?: number;
}

export interface LeaseReleaseResponse {
  success?: boolean;
  cooldown_until?: string | unknown;
}

export interface LeaseStatsResponse {
  total_available_proxies: number;
  total_active_leases: number;
  total_cooldowns: number;
  workspaces: Array<string>;
  proxies_by_usage: Array<Record<string, unknown>>;
}

export interface LeaseStatusResponse {
  workspace_id?: string | unknown;
  active_leases: Array<ActiveLeaseInfo>;
  cooldowns: Array<CooldownInfo>;
  total_active: number;
  total_cooldowns: number;
  workspaces: Array<WorkspaceLeaseSummary>;
}

export interface LeaseTimedCooldownBatchRequest {
  workspace_id: string;
  proxy_ports: Array<number>;
  cooldown_seconds?: number;
}

export interface LeaseTimedCooldownBatchResponse {
  success?: boolean;
  workspace_id: string;
  cooldown_seconds: number;
  applied_ports: Array<number>;
  skipped_ports: Array<number>;
}

export interface NodeBatchTestResponse {
  results: Array<NodeTestResult>;
  success_count: number;
  failed_count: number;
  test_profile?: string;
}

export interface NodeListResponse {
  nodes: Array<NodeResponse>;
  total: number;
}

export interface NodeResponse {
  id: string;
  group_id: string;
  group_type: GroupType;
  subscription_id?: string | unknown;
  name: string;
  protocol: ProtocolType;
  address: string;
  port: number;
  test_status?: TestStatus;
  latency_ms?: number | unknown;
  exit_ip?: string | unknown;
  exit_country?: string | unknown;
  in_proxy_pool?: boolean;
  proxy_port?: number | unknown;
}

export interface NodeTestJobResponse {
  job_id: string;
  status: NodeTestJobStatus;
  total: number;
  completed_count?: number;
  success_count?: number;
  failed_count?: number;
  progress_percent?: number;
  active_target?: string | unknown;
  target_index?: number | unknown;
  target_total?: number | unknown;
  current_target_completed?: number;
  current_target_total?: number;
  note?: string | unknown;
  test_profile?: string;
  results?: Array<NodeTestResult>;
  error?: string | unknown;
}

export interface NodeTestRequest {
  node_ids: Array<string>;
  timeout?: number;
  test_profile?: string;
}

export interface NodeTestResult {
  node_id: string;
  name: string;
  proxy_port?: number | unknown;
  status: TestStatus;
  latency_ms?: number | unknown;
  exit_ip?: string | unknown;
  exit_country?: string | unknown;
  error?: string | unknown;
  test_profile?: string | unknown;
  tested_target?: string | unknown;
  successful_target?: string | unknown;
}

export interface ProxyAddRequest {
  node_ids: Array<string>;
  start_port?: number;
}

export interface ProxyCooldownCandidate {
  node_id: string;
  name: string;
  proxy_port: number;
  failed_attempts: number;
  error?: string | unknown;
}

export interface ProxyExitIpDedupeRequest {
  disable_ports: Array<number>;
}

export interface ProxyExitIpDedupeResponse {
  disabled_count: number;
  disabled_ports: Array<number>;
  kept_ports: Array<number>;
}

export interface ProxyExitIpDuplicateGroup {
  exit_ip: string;
  keep_proxy: ProxyExitIpDuplicateProxy;
  remove_proxies: Array<ProxyExitIpDuplicateProxy>;
}

export interface ProxyExitIpDuplicatePreviewResponse {
  groups: Array<ProxyExitIpDuplicateGroup>;
  duplicate_group_count: number;
  duplicate_proxy_count: number;
}

export interface ProxyExitIpDuplicateProxy {
  port: number;
  node_id: string;
  node_name: string;
  exit_ip: string;
  test_status?: TestStatus;
  latency_ms?: number | unknown;
}

export interface ProxyHealthResponse {
  proxy_port: number;
  status: HealthStatusEnum;
  failure_count?: number;
  penalty_level?: number;
  penalty_remaining_seconds?: number | unknown;
  last_check?: string | unknown;
  last_success?: string | unknown;
  last_latency_ms?: number | unknown;
}

export interface ProxyListResponse {
  proxies: Array<ProxyResponse>;
  total: number;
  xray_status: XrayStatus;
}

export interface ProxyResponse {
  port: number;
  proxy_address: string;
  proxy_scheme: string;
  supported_proxy_protocols: Array<string>;
  http_proxy_url: string;
  socks5_proxy_url: string;
  socks5h_proxy_url: string;
  node_id: string;
  node_name: string;
  protocol: ProtocolType;
  address: string;
  server_port: number;
  test_status?: TestStatus;
  latency_ms?: number | unknown;
  exit_ip?: string | unknown;
  pool_status?: ProxyPoolStatus;
  disabled_reason?: string | unknown;
}

export interface ProxyTestAllResponse {
  results: Array<NodeTestResult>;
  success_count: number;
  failed_count: number;
  attempts?: number;
  cooldown_candidates?: Array<ProxyCooldownCandidate>;
}

export interface SubscriptionCreate {
  name: string;
  url: string;
}

export interface SubscriptionListResponse {
  subscriptions: Array<SubscriptionResponse>;
  total: number;
}

export interface SubscriptionResponse {
  id: string;
  name: string;
  url: string;
  node_count?: number;
  last_updated?: string | unknown;
  created_at: string;
}

export interface SuccessResponse {
  success?: boolean;
  message: string;
}

export interface SystemActionResponse {
  success: boolean;
  message: string;
  xray_status: XrayStatus;
}

export interface SystemStatusResponse {
  xray_status: XrayStatus;
  xray_version?: string | unknown;
  active_proxy_count: number;
  subscription_count: number;
  uptime_seconds?: number | unknown;
}

export interface TestTargetPreset {
  name: string;
  url: string;
}

export interface WorkspaceLeaseSummary {
  workspace_id: string;
  active_count: number;
  cooldown_count: number;
  last_activity_at: string;
}

export interface WorkspaceResetRequest {
  workspace_id: string;
}

export interface WorkspaceResetResponse {
  success?: boolean;
  workspace_id: string;
  released_count: number;
  recalled_count: number;
}
