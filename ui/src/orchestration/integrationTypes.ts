import { CompanySnapshot } from '../api';

export type ExecutiveAgentKey = 'cfo' | 'growth' | 'cto' | 'customer' | 'product';

export interface AgentIntegrationSlot {
  agentKey: ExecutiveAgentKey;
  agentName: string;
  role: string;
  targetDomain: string;
  requiredTelemetry: string[];
  status: 'unconnected' | 'connected';
  connectedSourceId: string | null;
  lastSyncAt: string | null;
}

export interface CompanyConnectionState {
  isDataConnected: boolean;
  connectedAt: string | null;
  company: CompanySnapshot | null;
  agentSlots: Record<ExecutiveAgentKey, AgentIntegrationSlot>;
}

export const INITIAL_AGENT_SLOTS: Record<ExecutiveAgentKey, AgentIntegrationSlot> = {
  cfo: {
    agentKey: 'cfo',
    agentName: 'CFO Agent',
    role: 'Chief Financial Officer',
    targetDomain: 'Cash Reserves, Runway & Margin Floors',
    requiredTelemetry: ['cash_balance', 'runway_months', 'mrr', 'gross_margin'],
    status: 'unconnected',
    connectedSourceId: null,
    lastSyncAt: null
  },
  growth: {
    agentKey: 'growth',
    agentName: 'Growth Agent',
    role: 'VP Growth & CMO',
    targetDomain: 'Acquisition Funnel, Traffic & Conversion',
    requiredTelemetry: ['monthly_visitors', 'trial_signups', 'trial_to_paid_conversion'],
    status: 'unconnected',
    connectedSourceId: null,
    lastSyncAt: null
  },
  cto: {
    agentKey: 'cto',
    agentName: 'CTO Agent',
    role: 'Chief Technology Officer',
    targetDomain: 'Cloud Infrastructure & Per-User Compute',
    requiredTelemetry: ['monthly_cloud_cost', 'infra_cost_per_paid_user'],
    status: 'unconnected',
    connectedSourceId: null,
    lastSyncAt: null
  },
  customer: {
    agentKey: 'customer',
    agentName: 'Customer Success Agent',
    role: 'VP Customer Success',
    targetDomain: 'Customer Churn, Retention & Support Tickets',
    requiredTelemetry: ['paying_customers', 'monthly_churn_rate', 'support_headcount'],
    status: 'unconnected',
    connectedSourceId: null,
    lastSyncAt: null
  },
  product: {
    agentKey: 'product',
    agentName: 'Product Agent',
    role: 'VP Product & Packaging',
    targetDomain: 'Tier Boundaries, Pricing Matrix & Feature Gating',
    requiredTelemetry: ['plans', 'starter_price', 'pro_price'],
    status: 'unconnected',
    connectedSourceId: null,
    lastSyncAt: null
  }
};
