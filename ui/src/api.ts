export interface CompanySnapshot {
  company_name: string;
  stage: string;
  currency: string;
  synthetic_data_badge: boolean;
  mrr: number;
  arr: number;
  cash_balance: number;
  runway_months: number;
  monthly_burn_net: number;
  gross_margin: number;
  paying_customers: number;
  monthly_churn_rate: number;
  cac: number;
  ltv: number;
  monthly_visitors: number;
  trial_to_paid_conversion: number;
  infra_cost_monthly: number;
  support_headcount: number;
  support_cost_monthly: number;
}

export interface TaskItem {
  id: string;
  owner_agent: string;
  depends_on: string[];
  status: 'pending' | 'running' | 'done' | 'failed' | 'retrying' | 'blocked';
  attempts: number;
  error?: string;
}

export interface FindingItem {
  agent: string;
  task_id: string;
  claim: string;
  recommendation: string;
  assumptions: any[];
  evidence: any[];
  confidence: number;
  limitations: string[];
  recovered_via_backup?: boolean;
  degraded?: boolean;
  status?: string;
}

export interface EventItem {
  ts: string;
  type: string;
  agent: string;
  payload: any;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

let _authToken: string | null = null;

export function setAuthToken(token: string | null) {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

function getHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (_authToken) {
    headers['Authorization'] = `Bearer ${_authToken}`;
  }
  return headers;
}

export const API_BASE = '/api';

export async function fetchAuthMe(): Promise<{ authenticated: boolean; user: UserProfile }> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) {
    throw new Error('Not authenticated');
  }
  return res.json();
}

export async function login(payload: { email: string; password: string; remember_me?: boolean }): Promise<{ user: UserProfile; token: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = 'Invalid credentials';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  const data = await res.json();
  if (data.token) {
    setAuthToken(data.token);
  }
  return data;
}

export async function register(payload: { full_name: string; email: string; password: string }): Promise<{ user: UserProfile; token: string }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = 'Registration failed';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  const data = await res.json();
  if (data.token) {
    setAuthToken(data.token);
  }
  return data;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders()
    });
  } finally {
    setAuthToken(null);
  }
}

export async function forgotPassword(email: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ email })
  });
  if (!res.ok) {
    throw new Error('Unable to process password reset request');
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchCompany(): Promise<CompanySnapshot> {
  const res = await fetch(`${API_BASE}/company`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch company snapshot');
  return res.json();
}

export interface SupervisorRoutingDecision {
  context_summary: string;
  selected_specialists: string[];
  specialist_directives: Record<string, string>;
  reasoning: string;
  source: string;
}

export async function fetchRoutingDecision(query: string, companyId?: string): Promise<SupervisorRoutingDecision> {
  const res = await fetch(`${API_BASE}/orchestration/route`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ query, company_id: companyId })
  });
  if (!res.ok) {
    throw new Error('Failed to fetch routing decision');
  }
  return res.json();
}

export async function submitDecision(
  query: string,
  constraints?: Record<string, any>,
  injectedFailure?: any,
  selectedSpecialists?: string[]
) {
  const res = await fetch(`${API_BASE}/decisions`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query,
      constraints,
      injected_failure: injectedFailure,
      selected_specialists: selectedSpecialists
    })
  });
  if (!res.ok) {
    let msg = 'Failed to submit decision';
    try {
      const err = await res.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function fetchDecisionStatus(decisionId: string) {
  const res = await fetch(`${API_BASE}/decisions/${decisionId}`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchDecisionReport(decisionId: string) {
  const res = await fetch(`${API_BASE}/decisions/${decisionId}/report`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch report');
  return res.json();
}

export async function injectFailure(
  decisionId: string,
  agent: string,
  mode: string,
  persist: boolean = false,
  failAttempts: number = 1
) {
  const res = await fetch(`${API_BASE}/decisions/${decisionId}/inject-failure`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ agent, mode, persist, fail_attempts: failAttempts })
  });
  if (!res.ok) {
    let msg = `Failed to inject failure (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) {
        msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      }
    } catch {
      try {
        const text = await res.text();
        if (text) msg = text;
      } catch {}
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function approveDecision(decisionId: string, action: string, notes?: string) {
  const res = await fetch(`${API_BASE}/decisions/${decisionId}/approve`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action, notes })
  });
  if (!res.ok) throw new Error('Failed to record approval');
  return res.json();
}

export async function fetchHistory() {
  const res = await fetch(`${API_BASE}/history`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}

export async function fetchCompanyGraph() {
  const res = await fetch(`${API_BASE}/graph`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch graph');
  return res.json();
}

export interface FieldProvenance {
  source: 'uploaded_markdown' | 'website_scraper' | 'manual';
  source_detail?: string;
  confidence?: number;
  extracted: boolean;
}

export interface CompanyContextFields {
  company_name: string;
  industry: string;
  business_model: string;
  description: string;
  products_services: string;
  target_customers: string;
  revenue_model: string;
  geographic_presence?: string;
  stage: string;
  strategic_goals: string;
  major_challenges?: string;
  key_competitors?: string;
  website_url?: string;
}

export interface CompanyContextRecord extends CompanyContextFields {
  id?: string;
  provenance: Record<string, FieldProvenance>;
  uploaded_documents?: { filename: string; size?: number; uploaded_at?: string }[];
  is_active?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ExtractionResult {
  fields: Record<string, string>;
  provenance: Record<string, FieldProvenance>;
  missing_fields: string[];
  document_names: string[];
  warnings: string[];
}

export async function extractCompanyContext(files: { filename: string; content: string }[]): Promise<ExtractionResult> {
  const res = await fetch(`${API_BASE}/company/extract`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ files })
  });
  if (!res.ok) {
    let msg = 'Failed to extract company context';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function scrapeCompanyWebsite(url: string): Promise<ExtractionResult> {
  const res = await fetch(`${API_BASE}/company/scrape-website`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ url })
  });
  if (!res.ok) {
    let msg = 'Failed to scrape corporate website';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function saveCompanyContext(payload: Partial<CompanyContextRecord>): Promise<{ status: string; context: CompanyContextRecord }> {
  const res = await fetch(`${API_BASE}/company/context`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = 'Failed to save company context';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function fetchActiveCompanyContext(): Promise<{ active: boolean; context: CompanyContextRecord | null }> {
  const res = await fetch(`${API_BASE}/company/context`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch active company context');
  return res.json();
}

export async function fetchCompanyContexts(): Promise<{ contexts: CompanyContextRecord[] }> {
  const res = await fetch(`${API_BASE}/company/contexts`, { credentials: 'include', headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch company contexts');
  return res.json();
}

export async function deleteCompanyContext(id: string): Promise<{ status: string; id: string }> {
  const res = await fetch(`${API_BASE}/company/context/${id}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to delete company context');
  return res.json();
}

export interface AgentChatResponse {
  agent_key: string;
  agent_name: string;
  role: string;
  avatar: string;
  response: string;
  key_metrics: Record<string, any>;
  recommendation: string;
  confidence: number;
  timestamp: string;
}

export async function chatWithAgent(
  agentKey: string,
  message: string,
  history?: { role: string; content: string }[]
): Promise<AgentChatResponse> {
  const res = await fetch(`${API_BASE}/agents/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ agent_key: agentKey, message, history })
  });
  if (!res.ok) {
    let msg = 'Failed to communicate with agent';
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// ---- Integration Connectors ----

export type ConnectorStatus =
  | 'not_connected'
  | 'connecting'
  | 'connected'
  | 'syncing'
  | 'error'
  | 'sandbox_connected'
  | 'awaiting_credentials';

export interface ConnectorStatusInfo {
  connector_id: string;
  display_name: string;
  status: ConnectorStatus;
  environment: string; // sandbox | test | developer | production
  last_sync: string | null;
  error: string | null;
  agent_domain: string;
  supports_write: boolean;
  supports_synthetic_generation: boolean;
  awaiting_credentials: boolean;
  missing_env_vars: string[];
}

export interface IntegrationSyncResult {
  connector_id: string;
  sync_start: string;
  sync_end: string | null;
  records_fetched: number;
  records_created: number;
  status: string;
  error_message: string | null;
}

export async function fetchAllConnectorStatuses(): Promise<ConnectorStatusInfo[]> {
  const res = await fetch(`${API_BASE}/integrations/status`, {
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch integration statuses');
  return res.json();
}

export async function fetchConnectorStatus(connectorId: string): Promise<ConnectorStatusInfo> {
  const res = await fetch(`${API_BASE}/integrations/status/${connectorId}`, {
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch status for ${connectorId}`);
  return res.json();
}

export async function connectIntegration(connectorId: string): Promise<ConnectorStatusInfo> {
  const res = await fetch(`${API_BASE}/integrations/connect/${connectorId}`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error(`Failed to connect ${connectorId}`);
  return res.json();
}

export async function disconnectIntegration(connectorId: string): Promise<void> {
  await fetch(`${API_BASE}/integrations/disconnect/${connectorId}`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders()
  });
}

export async function syncIntegration(connectorId: string): Promise<IntegrationSyncResult> {
  const res = await fetch(`${API_BASE}/integrations/sync/${connectorId}`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders()
  });
  if (!res.ok) throw new Error(`Failed to sync ${connectorId}`);
  return res.json();
}

export async function generateSyntheticData(
  connectorId: string,
  companyProfile: Record<string, unknown>
): Promise<{ records_created: number; message: string }> {
  const res = await fetch(`${API_BASE}/integrations/generate/${connectorId}`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ company_profile: companyProfile })
  });
  if (!res.ok) throw new Error(`Failed to generate synthetic data for ${connectorId}`);
  return res.json();
}

export interface NangoSessionResponse {
  token: string;
  expires_at?: string | null;
  is_sandbox?: boolean;
  message?: string;
  error?: string;
}

export async function fetchNangoSessionToken(
  companyId: string = 'default',
  allowedIntegrations?: string[]
): Promise<NangoSessionResponse> {
  const res = await fetch(`${API_BASE}/integrations/nango/session-token`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ company_id: companyId, allowed_integrations: allowedIntegrations })
  });
  if (!res.ok) throw new Error('Failed to generate Nango Connect session token');
  return res.json();
}

export async function notifyNangoCallback(payload: {
  connection_id: string;
  provider_config_key: string;
  company_id?: string;
}): Promise<{ status: string; connection: any; connector_id: string }> {
  const res = await fetch(`${API_BASE}/integrations/nango/callback`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to save Nango connection');
  return res.json();
}

export async function directConnectIntegration(
  connectorId: string,
  payload: {
    company_id?: string;
    auth_mode?: string;
    account_email?: string;
    custom_credentials?: Record<string, string>;
  } = {}
): Promise<ConnectorStatusInfo> {
  const res = await fetch(`${API_BASE}/integrations/direct-connect/${connectorId}`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to direct connect ${connectorId}`);
  const data = await res.json();
  return data.connector_status;
}

