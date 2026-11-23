import React, { useState, useEffect } from 'react';
import { CompanyContextCard } from './CompanyContextCard';
import {
  CompanyContextRecord,
  fetchActiveCompanyContext,
  fetchCompanyContexts,
  deleteCompanyContext
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

  // Load saved context on mount
  useEffect(() => {
    loadContexts();
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

      {/* SECTION 2: Integration Page Expansion (Future Executive Agent Connectors) */}
      <section className="space-y-4 pt-6 border-t border-[#242424]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#cccccc]">
              Executive Agent Operational Connectors
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#222222] text-[#888888] border border-[#333333]">
              Upcoming Architecture
            </span>
          </div>
          <p className="text-xs text-[#666666] mt-1">
            Once Company Context is established, individual executive agents can be paired with domain-specific live data connectors.
          </p>
        </div>

        {/* 6 Reserved Integration Slots */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <FutureConnectorSlot
            agentKey="cfo"
            agentName="CFO"
            title="Financial Data"
            domainDescription="Cash reserves, net burn, runway months, gross margins, accounting ledgers, and expense structures."
            requiredTelemetry={['cash_balance', 'runway_months', 'mrr', 'gross_margin']}
          />

          <FutureConnectorSlot
            agentKey="growth"
            agentName="Growth"
            title="Marketing & Sales Data"
            domainDescription="Acquisition funnels, visitor-to-paid conversion rates, blended CAC, and marketing channel telemetry."
            requiredTelemetry={['monthly_visitors', 'trial_signups', 'trial_to_paid_conversion']}
          />

          <FutureConnectorSlot
            agentKey="cto"
            agentName="CTO"
            title="Engineering & Infrastructure Data"
            domainDescription="Cloud compute expenses, server hosting bills, infrastructure cost per active user, and uptime SLAs."
            requiredTelemetry={['monthly_cloud_cost', 'infra_cost_per_paid_user']}
          />

          <FutureConnectorSlot
            agentKey="customer"
            agentName="Customer Success"
            title="Customer & Support Data"
            domainDescription="Monthly customer churn rate, retention cohorts, support ticket volume, and agent resolution load."
            requiredTelemetry={['paying_customers', 'monthly_churn_rate', 'support_headcount']}
          />

          <FutureConnectorSlot
            agentKey="product"
            agentName="Product"
            title="Product Analytics Data"
            domainDescription="Feature engagement frequency, plan tier usage matrices, and self-serve upgrade velocities."
            requiredTelemetry={['tier_distribution', 'feature_utilization']}
          />

          <FutureConnectorSlot
            agentKey="skeptic"
            agentName="Skeptic"
            title="External Market Intelligence"
            domainDescription="Competitor pricing benchmarks, macroeconomic volatility indices, and market saturation data."
            requiredTelemetry={['competitor_pricing_matrix', 'macro_volatility_index']}
          />
        </div>
      </section>
    </div>
  );
};

// Reserved slot component for upcoming executive agent integrations
const FutureConnectorSlot: React.FC<{
  agentKey: string;
  agentName: string;
  title: string;
  domainDescription: string;
  requiredTelemetry: string[];
}> = ({ agentName, title, domainDescription, requiredTelemetry }) => {
  return (
    <div className="bg-[#161616] border border-dashed border-[#2d2d2d] rounded-2xl p-4 space-y-3 opacity-80 hover:opacity-100 transition">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-[#222222] border border-[#333333] flex items-center justify-center text-[10px] font-mono font-bold text-purple-300">
            {agentName}
          </span>
          <span className="text-xs font-bold text-[#e0e0e0]">{title}</span>
        </div>
        <span className="text-[10px] font-mono text-[#666666] bg-[#1a1a1a] px-2 py-0.5 rounded border border-[#2a2a2a]">
          Pending
        </span>
      </div>

      <p className="text-[11px] text-[#888888] leading-relaxed">
        {domainDescription}
      </p>

      <div className="pt-2 border-t border-[#222222] flex flex-wrap gap-1">
        {requiredTelemetry.map((item) => (
          <span
            key={item}
            className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#1c1c1c] text-[#777777] border border-[#262626]"
          >
            {item}
          </span>
        ))}
      </div>

      <div className="pt-1 flex items-center justify-between text-[10px] text-[#555555] font-mono">
        <span>Slot Reserved</span>
        <span>Awaiting Configuration</span>
      </div>
    </div>
  );
};
