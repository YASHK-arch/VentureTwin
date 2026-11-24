import React, { useState } from 'react';
import {
  ConnectorStatusInfo,
  connectIntegration,
  disconnectIntegration,
  syncIntegration,
  generateSyntheticData,
} from '../../api';
import { IntegrationConnectorCard } from './IntegrationConnectorCard';
import { ConnectIntegrationModal } from './ConnectIntegrationModal';

interface IntegrationDef {
  connectorId: string;
  displayName: string;
  description: string;
}

interface AgentIntegrationCardProps {
  agentKey: 'cfo' | 'growth' | 'cto' | 'customer' | 'product' | 'skeptic';
  agentName: string;
  agentIcon: string;
  agentRole: string;
  agentColor: string; // tailwind text color like 'text-emerald-400'
  integrations: IntegrationDef[];
  connectorStatuses: ConnectorStatusInfo[];
  companyProfile: Record<string, unknown>;
}

type LoadingKey = string; // connectorId + ':' + action

export const AgentIntegrationCard: React.FC<AgentIntegrationCardProps> = ({
  agentKey: _agentKey,
  agentName,
  agentIcon,
  agentRole,
  agentColor,
  integrations,
  connectorStatuses,
  companyProfile,
}) => {
  const [loadingKeys, setLoadingKeys] = useState<Set<LoadingKey>>(new Set());
  const [localStatuses, setLocalStatuses] = useState<ConnectorStatusInfo[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [activeModalConnector, setActiveModalConnector] = useState<IntegrationDef | null>(null);
  const [showAllIntegrations, setShowAllIntegrations] = useState(false);

  // Merge prop statuses with any locally-updated ones
  const mergedStatuses = (cid: string): ConnectorStatusInfo | null => {
    const local = localStatuses.find((s) => s.connector_id === cid);
    if (local) return local;
    return connectorStatuses.find((s) => s.connector_id === cid) ?? null;
  };

  const isConnectedStatus = (st: ConnectorStatusInfo | null): boolean => {
    if (!st) return false;
    return st.status === 'connected' || st.status === 'sandbox_connected' || st.status === 'syncing';
  };

  // Connected integrations for this agent
  const connectedIntegrations = integrations.filter((integ) => {
    const st = mergedStatuses(integ.connectorId);
    return isConnectedStatus(st);
  });

  const isAgentConnected = connectedIntegrations.length > 0;
  // If at least one connection is connected, display ONLY the connected ones and auto-hide others
  const visibleIntegrations = isAgentConnected && !showAllIntegrations ? connectedIntegrations : integrations;

  const setLoading = (key: LoadingKey, val: boolean) => {
    setLoadingKeys((prev) => {
      const next = new Set(prev);
      val ? next.add(key) : next.delete(key);
      return next;
    });
  };

  const updateLocalStatus = (updated: ConnectorStatusInfo) => {
    setLocalStatuses((prev) => {
      const filtered = prev.filter((s) => s.connector_id !== updated.connector_id);
      return [...filtered, updated];
    });
  };

  const handleConnect = (integ: IntegrationDef) => {
    setActiveModalConnector(integ);
  };

  const handleDisconnect = async (connectorId: string) => {
    const key: LoadingKey = `${connectorId}:disconnect`;
    setLoading(key, true);
    setErrors((e) => ({ ...e, [connectorId]: '' }));
    try {
      await disconnectIntegration(connectorId);
      // Reset local status to not_connected
      const existing = mergedStatuses(connectorId);
      if (existing) {
        updateLocalStatus({ ...existing, status: 'not_connected', last_sync: null });
      }
    } catch (err) {
      setErrors((e) => ({ ...e, [connectorId]: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading(key, false);
    }
  };

  const handleSync = async (connectorId: string) => {
    const key: LoadingKey = `${connectorId}:sync`;
    setLoading(key, true);
    setErrors((e) => ({ ...e, [connectorId]: '' }));
    try {
      // Optimistically set syncing
      const existing = mergedStatuses(connectorId);
      if (existing) updateLocalStatus({ ...existing, status: 'syncing' });
      await syncIntegration(connectorId);
      // After sync, revert to connected
      if (existing) {
        updateLocalStatus({ ...existing, status: 'connected', last_sync: new Date().toISOString() });
      }
    } catch (err) {
      setErrors((e) => ({ ...e, [connectorId]: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading(key, false);
    }
  };

  const handleGenerate = async (connectorId: string) => {
    const key: LoadingKey = `${connectorId}:generate`;
    setLoading(key, true);
    setErrors((e) => ({ ...e, [connectorId]: '' }));
    try {
      await generateSyntheticData(connectorId, companyProfile);
    } catch (err) {
      setErrors((e) => ({ ...e, [connectorId]: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading(key, false);
    }
  };

  const isConnectorLoading = (connectorId: string): boolean => {
    return Array.from(loadingKeys).some((k) => k.startsWith(`${connectorId}:`));
  };

  // Accent color strip mapping by agentColor
  const stripColor: Record<string, string> = {
    'text-emerald-400': 'bg-emerald-500',
    'text-cyan-400':    'bg-cyan-500',
    'text-amber-400':   'bg-amber-500',
    'text-indigo-400':  'bg-indigo-500',
    'text-pink-400':    'bg-pink-500',
    'text-rose-400':    'bg-rose-500',
  };
  const accentStrip = stripColor[agentColor] ?? 'bg-purple-500';

  return (
    <div className={`bg-[#141414] rounded-2xl overflow-hidden transition-all duration-300 ${isAgentConnected ? 'border border-emerald-500/35 shadow-[0_0_20px_rgba(16,185,129,0.08)]' : 'border border-[#222222] hover:border-[#2d2d2d]'}`}>
      {/* Top accent line */}
      <div className={`h-1 w-full transition-all duration-300 ${isAgentConnected ? 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]' : `${accentStrip} opacity-70`}`} />

      {/* Card Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-xl leading-none">{agentIcon}</span>
          <div>
            <span className={`text-sm font-bold ${isAgentConnected ? 'text-white' : agentColor}`}>{agentName}</span>
            <p className="text-[10px] text-[#666666] font-mono mt-0.5">{agentRole}</p>
          </div>
        </div>

        {/* Agent Level Connected Badge */}
        {isAgentConnected ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/35 text-emerald-400 text-xs font-semibold shadow-[0_0_12px_rgba(16,185,129,0.2)]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Agent Connected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
            <span>Awaiting Connection</span>
          </div>
        )}
      </div>

      {/* Integration cards — displays only connected ones when agent is connected, auto-hiding redundant sources */}
      <div className="p-3.5 space-y-2.5">
        {visibleIntegrations.map((integ) => {
          const st = mergedStatuses(integ.connectorId);
          const err = errors[integ.connectorId];
          // Surface error into status object so the card can show it
          const statusWithErr: ConnectorStatusInfo | null = st
            ? { ...st, error: err || st.error }
            : null;

          return (
            <IntegrationConnectorCard
              key={integ.connectorId}
              connectorId={integ.connectorId}
              displayName={integ.displayName}
              description={integ.description}
              status={statusWithErr}
              onConnect={() => handleConnect(integ)}
              onDisconnect={() => handleDisconnect(integ.connectorId)}
              onSync={() => handleSync(integ.connectorId)}
              onGenerate={() => handleGenerate(integ.connectorId)}
              isLoading={isConnectorLoading(integ.connectorId)}
            />
          );
        })}

        {/* Optional expand toggle for power users wanting to add secondary connections */}
        {isAgentConnected && integrations.length > connectedIntegrations.length && (
          <div className="pt-1 flex justify-end">
            <button
              onClick={() => setShowAllIntegrations(!showAllIntegrations)}
              className="text-[10px] text-zinc-500 hover:text-zinc-300 transition cursor-pointer flex items-center gap-1"
            >
              {showAllIntegrations ? 'Hide other sources' : `+ Add alternative source (${integrations.length - connectedIntegrations.length})`}
            </button>
          </div>
        )}
      </div>

      {/* Connect Integration Modal (Google / SSO / Sandbox) */}
      {activeModalConnector && (
        <ConnectIntegrationModal
          connectorId={activeModalConnector.connectorId}
          displayName={activeModalConnector.displayName}
          description={activeModalConnector.description}
          environment={mergedStatuses(activeModalConnector.connectorId)?.environment || 'test'}
          isOpen={true}
          onClose={() => setActiveModalConnector(null)}
          onConnected={(updated) => updateLocalStatus(updated)}
        />
      )}
    </div>
  );
};
