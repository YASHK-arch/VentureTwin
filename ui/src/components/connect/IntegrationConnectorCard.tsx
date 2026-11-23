import React, { useState } from 'react';
import { ConnectorStatusInfo, ConnectorStatus } from '../../api';

interface IntegrationConnectorCardProps {
  connectorId: string;
  displayName: string;
  description: string;
  status: ConnectorStatusInfo | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onSync: () => void;
  onGenerate: () => void;
  isLoading: boolean;
}

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return 'Never';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface StatusBadgeProps {
  status: ConnectorStatus;
  errorMsg: string | null;
  missingVars: string[];
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, errorMsg, missingVars }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const configs: Record<ConnectorStatus, { label: string; icon: string; cls: string }> = {
    not_connected:        { label: 'Not Connected',         icon: '○', cls: 'bg-[#222222] text-[#888888] border-[#333333]' },
    connecting:           { label: 'Connecting...',          icon: '◌', cls: 'bg-blue-950 text-blue-300 border-blue-800 animate-pulse' },
    connected:            { label: 'Connected',              icon: '●', cls: 'bg-emerald-950 text-emerald-300 border-emerald-800' },
    sandbox_connected:    { label: 'Sandbox',                icon: '◑', cls: 'bg-teal-950 text-teal-300 border-teal-800' },
    syncing:              { label: 'Syncing',                icon: '↻', cls: 'bg-purple-950 text-purple-300 border-purple-800 animate-pulse' },
    error:                { label: 'Error',                  icon: '✕', cls: 'bg-red-950 text-red-300 border-red-800' },
    awaiting_credentials: { label: 'Awaiting Credentials',  icon: '⚠', cls: 'bg-amber-950 text-amber-300 border-amber-700' },
  };

  const cfg = configs[status];
  const hasTooltip = status === 'awaiting_credentials' || status === 'error';
  const tooltipContent = status === 'awaiting_credentials'
    ? missingVars.join(', ')
    : errorMsg ?? '';

  return (
    <div className="relative inline-flex">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono border select-none ${cfg.cls} ${hasTooltip ? 'cursor-help' : ''}`}
        onMouseEnter={() => hasTooltip && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span>{cfg.icon}</span>
        <span>{cfg.label}</span>
      </span>
      {showTooltip && tooltipContent && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-max max-w-xs bg-[#1a1a1a] border border-[#333333] rounded-lg px-3 py-2 text-[10px] font-mono text-[#cccccc] shadow-xl whitespace-pre-wrap">
          {tooltipContent}
        </div>
      )}
    </div>
  );
};

const EnvChip: React.FC<{ env: string }> = ({ env }) => {
  const upper = env.toUpperCase();
  const cls: Record<string, string> = {
    PRODUCTION: 'text-emerald-400 border-emerald-800 bg-emerald-950',
    SANDBOX:    'text-teal-400 border-teal-800 bg-teal-950',
    TEST:       'text-amber-400 border-amber-800 bg-amber-950',
    DEVELOPER:  'text-blue-400 border-blue-800 bg-blue-950',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${cls[upper] ?? 'text-[#888888] border-[#333333] bg-[#1a1a1a]'}`}>
      {upper}
    </span>
  );
};

const Spinner: React.FC = () => (
  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);

export const IntegrationConnectorCard: React.FC<IntegrationConnectorCardProps> = ({
  connectorId: _connectorId,
  displayName,
  description,
  status,
  onConnect,
  onDisconnect,
  onSync,
  onGenerate,
  isLoading,
}) => {
  const st: ConnectorStatus = status?.status ?? 'not_connected';
  const isConnected = st === 'connected' || st === 'sandbox_connected';
  const isSyncing = st === 'syncing';
  const awaitingCreds = st === 'awaiting_credentials';

  return (
    <div className="bg-[#181818] border border-[#242424] rounded-xl p-3.5 space-y-3 hover:border-[#333333] transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span className="text-xs font-semibold text-[#e0e0e0] block truncate">{displayName}</span>
          <p className="text-[10px] text-[#777777] mt-0.5 leading-relaxed line-clamp-2">{description}</p>
        </div>
        <div className="flex-shrink-0 flex flex-col items-end gap-1.5">
          <StatusBadge
            status={st}
            errorMsg={status?.error ?? null}
            missingVars={status?.missing_env_vars ?? []}
          />
          {status?.environment && <EnvChip env={status.environment} />}
        </div>
      </div>

      {/* Last Sync */}
      {isConnected && status?.last_sync !== undefined && (
        <div className="text-[10px] text-[#555555] font-mono">
          Last sync: {formatRelativeTime(status.last_sync)}
        </div>
      )}

      {/* Awaiting credentials callout */}
      {awaitingCreds && status && status.missing_env_vars.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-800/50 rounded-lg p-2.5 space-y-1">
          <p className="text-[10px] text-amber-400 font-semibold">Missing environment variables:</p>
          <div className="flex flex-wrap gap-1">
            {status.missing_env_vars.map((v) => (
              <span key={v} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-900/40 text-amber-300 border border-amber-800/60">
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Backend unavailable fallback */}
      {!status && !isLoading && (
        <div className="text-[10px] text-[#555555] italic">Backend unavailable — status unknown</div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {/* Connect */}
        {!isConnected && !awaitingCreds && st !== 'connecting' && (
          <button
            onClick={onConnect}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-purple-700 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white transition cursor-pointer"
          >
            {isLoading ? <Spinner /> : null}
            Connect
          </button>
        )}

        {/* Connecting indicator */}
        {st === 'connecting' && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-blue-900/50 text-blue-300 border border-blue-800">
            <Spinner /> Connecting…
          </span>
        )}

        {/* Sync Now */}
        {isConnected && (
          <button
            onClick={onSync}
            disabled={isLoading || isSyncing}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-[#222222] hover:bg-[#2a2a2a] border border-[#333333] disabled:opacity-50 disabled:cursor-not-allowed text-[#aaaaaa] hover:text-white transition cursor-pointer"
          >
            {isLoading && isSyncing ? <Spinner /> : null}
            ↻ Sync Now
          </button>
        )}

        {/* Generate Synthetic */}
        {isConnected && status?.supports_synthetic_generation && (
          <button
            onClick={onGenerate}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-teal-900/50 hover:bg-teal-800/60 border border-teal-800/70 disabled:opacity-50 disabled:cursor-not-allowed text-teal-300 transition cursor-pointer"
          >
            {isLoading ? <Spinner /> : null}
            ⚗ Generate Synthetic
          </button>
        )}

        {/* Disconnect */}
        {isConnected && (
          <button
            onClick={onDisconnect}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-red-950/50 hover:bg-red-900/60 border border-red-900/70 disabled:opacity-50 disabled:cursor-not-allowed text-red-400 transition cursor-pointer ml-auto"
          >
            Disconnect
          </button>
        )}
      </div>
    </div>
  );
};
