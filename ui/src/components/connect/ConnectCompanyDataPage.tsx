import React, { useState, useEffect } from 'react';
import { CompanyContextCard } from './CompanyContextCard';
import { AgentIntegrationCard } from './AgentIntegrationCard';
import {
  CompanyContextRecord,
  ConnectorStatusInfo,
  fetchActiveCompanyContext,
  fetchCompanyContexts,
  deleteCompanyContext,
  fetchAllConnectorStatuses,
} from '../../api';

interface ConnectCompanyDataPageProps {
  onCompanyConnected: (context: CompanyContextRecord) => void;
  onNavigateToConsole: () => void;
}

export const ConnectCompanyDataPage: React.FC<ConnectCompanyDataPageProps> = ({
  onCompanyConnected,
  onNavigateToConsole
}) => {
  const [activeContext, setActiveContext] = useState<CompanyContextRecord | null>(null);
  const [allContexts, setAllContexts] = useState<CompanyContextRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [connectorStatuses, setConnectorStatuses] = useState<ConnectorStatusInfo[]>([]);
  const [statusLoading, setStatusLoading] = useState(false);

  // Load saved context on mount
  useEffect(() => {
    loadContexts();
    loadConnectorStatuses();
  }, []);

  const loadContexts = async () => {
    setIsLoading(true);
    try {
      const activeRes = await fetchActiveCompanyContext();
      if (activeRes.active && activeRes.context) {
        setActiveContext(activeRes.context);
      }
      const allRes = await fetchCompanyContexts();
      if (allRes.contexts) {
        setAllContexts(allRes.contexts);
      }
    } catch (err) {
      console.error('Failed loading saved company context:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadConnectorStatuses = async () => {
    setStatusLoading(true);
    try {
      const statuses = await fetchAllConnectorStatuses();
      setConnectorStatuses(statuses);
    } catch (err) {
      // Backend may be unavailable; leave statuses empty for graceful degradation
      console.warn('Integration status unavailable:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleContextSaved = (saved: CompanyContextRecord) => {
    setActiveContext(saved);
    setAllContexts((prev) => {
      const filtered = prev.filter((c) => c.id !== saved.id);
      return [saved, ...filtered];
    });
    onCompanyConnected(saved);
  };

  const handleSelectProfile = (ctx: CompanyContextRecord) => {
    setActiveContext(ctx);
    onCompanyConnected(ctx);
  };

  const handleNewProfile = () => {
    setActiveContext(null);
  };

  const handleDeleteProfile = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this company context profile?')) return;
    try {
      await deleteCompanyContext(id);
      setAllContexts((prev) => prev.filter((c) => c.id !== id));
      if (activeContext?.id === id) {
        setActiveContext(null);
      }
    } catch (err) {
      console.error('Failed to delete context:', err);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-purple-400 uppercase tracking-widest">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            <span>Data Onboarding & Connectors</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Connect Company Data
          </h1>
          <p className="text-xs text-[#888888] mt-1">
            Connect foundational business architecture and operational data pipelines to VentureTwin executive agents.
          </p>
        </div>

        {/* Profile Management / Saved Contexts Bar */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {allContexts.length > 0 && (
            <div className="relative">
              <select
                value={activeContext?.id || ''}
                onChange={(e) => {
                  const found = allContexts.find((c) => c.id === e.target.value);
                  if (found) handleSelectProfile(found);
                }}
                className="bg-[#1a1a1a] border border-[#2e2e2e] text-xs text-[#cccccc] px-3 py-1.5 rounded-lg outline-none cursor-pointer"
              >
                <option value="" disabled>
                  Select Saved Profile ({allContexts.length})...
                </option>
                {allContexts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || 'Untitled Company'} ({c.stage || 'Stage Unset'})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleNewProfile}
            className="px-3 py-1.5 bg-[#202020] hover:bg-[#282828] text-xs font-medium text-white border border-[#333333] rounded-lg transition cursor-pointer flex items-center gap-1.5"
            title="Create new profile"
          >
            <span>+</span>
            <span>New Profile</span>
          </button>

          <button
            onClick={onNavigateToConsole}
            className="px-3 py-1.5 bg-[#202020] hover:bg-[#282828] text-[#cccccc] hover:text-white border border-[#333333] text-xs font-semibold rounded-lg transition cursor-pointer flex items-center gap-1.5"
            title="Return to Decision Console"
          >
            <span>✕</span>
            <span>Close</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: Company Context (The Foundational Integration) */}
      <section className="space-y-3">
        <CompanyContextCard
          key={activeContext?.id || 'new_context'}
          initialContext={activeContext}
          onContextSaved={handleContextSaved}
        />
      </section>

      {/* SECTION 2: Executive Agent Integration Connectors */}
      <section className="space-y-4 pt-6 border-t border-[#242424]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#cccccc]">
              Executive Agent Operational Connectors
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-900/40 text-purple-300 border border-purple-700/50">
              Active Integration Connectors
            </span>
          </div>
          <p className="text-xs text-[#666666] mt-1">
            Connect live data sources to each executive agent to power real-time analysis.
          </p>
        </div>

        {statusLoading && (
          <div className="text-xs text-[#555555] font-mono flex items-center gap-2">
            <svg className="animate-spin h-3 w-3 text-purple-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading connector statuses…
          </div>
        )}

        {/* 6 Agent Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AgentIntegrationCard
            agentKey="cfo"
            agentName="CFO"
            agentIcon="💼"
            agentRole="Chief Financial Officer"
            agentColor="text-emerald-400"
            integrations={[
              { connectorId: 'stripe', displayName: 'Stripe', description: 'Payments, subscriptions, invoices & customer billing data' },
              { connectorId: 'quickbooks', displayName: 'QuickBooks', description: 'Accounting ledgers, P&L, balance sheet & expense structures' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />

          <AgentIntegrationCard
            agentKey="growth"
            agentName="Growth"
            agentIcon="📈"
            agentRole="VP Growth & CMO"
            agentColor="text-cyan-400"
            integrations={[
              { connectorId: 'hubspot', displayName: 'HubSpot', description: 'CRM contacts, deals, pipelines & marketing activity' },
              { connectorId: 'ga4', displayName: 'Google Analytics 4', description: 'Website sessions, conversions, acquisition & engagement' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />

          <AgentIntegrationCard
            agentKey="cto"
            agentName="CTO"
            agentIcon="⚡"
            agentRole="Chief Technology Officer"
            agentColor="text-amber-400"
            integrations={[
              { connectorId: 'github', displayName: 'GitHub', description: 'Commits, PRs, issues, releases & engineering velocity' },
              { connectorId: 'cloudwatch', displayName: 'AWS CloudWatch', description: 'Infrastructure metrics, uptime, latency & resource utilization' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />

          <AgentIntegrationCard
            agentKey="customer"
            agentName="Customer Success"
            agentIcon="🤝"
            agentRole="VP Customer Success"
            agentColor="text-indigo-400"
            integrations={[
              { connectorId: 'intercom', displayName: 'Intercom', description: 'Customer contacts, conversations & support interactions' },
              { connectorId: 'zendesk', displayName: 'Zendesk', description: 'Support tickets, resolution times & satisfaction scores' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />

          <AgentIntegrationCard
            agentKey="product"
            agentName="Product"
            agentIcon="📦"
            agentRole="Chief Product Officer"
            agentColor="text-pink-400"
            integrations={[
              { connectorId: 'posthog', displayName: 'PostHog', description: 'Product analytics, feature adoption & user retention' },
              { connectorId: 'linear', displayName: 'Linear', description: 'Issues, roadmap, cycles & product development velocity' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />

          <AgentIntegrationCard
            agentKey="skeptic"
            agentName="Skeptic"
            agentIcon="🛡️"
            agentRole="Independent Risk Auditor"
            agentColor="text-rose-400"
            integrations={[
              { connectorId: 'firecrawl', displayName: 'Firecrawl', description: 'Real-time competitor website scraping & public pricing data' },
              { connectorId: 'tavily', displayName: 'Tavily', description: 'Market intelligence, competitor developments & industry benchmarks' }
            ]}
            connectorStatuses={connectorStatuses}
            companyProfile={(activeContext ?? {}) as Record<string, unknown>}
          />
        </div>
      </section>
    </div>
  );
};

