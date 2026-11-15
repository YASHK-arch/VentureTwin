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

export async function submitDecision(query: string, constraints?: Record<string, any>, injectedFailure?: any) {
  const res = await fetch(`${API_BASE}/decisions`, {
    method: 'POST',
    credentials: 'include',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ query, constraints, injected_failure: injectedFailure })
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

