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
    awaiting_credentials: { label: 'Not Connected',         icon: '○', cls: 'bg-[#222222] text-[#888888] border-[#333333]' },
  };

  const cfg = configs[status];
  const hasTooltip = status === 'error';
  const tooltipContent = errorMsg ?? '';

  return (
    <div className="relative inline-flex flex-shrink-0">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono border select-none whitespace-nowrap ${cfg.cls} ${hasTooltip ? 'cursor-help' : ''}`}
        onMouseEnter={() => hasTooltip && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span>{cfg.icon}</span>
        <span>{cfg.label}</span>
      </span>
      {showTooltip && tooltipContent && (
        <div className="absolute bottom-full right-0 mb-2 z-50 w-max max-w-xs bg-[#1a1a1a] border border-[#333333] rounded-lg px-3 py-2 text-[10px] font-mono text-[#cccccc] shadow-xl whitespace-pre-wrap">
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
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border whitespace-nowrap ${cls[upper] ?? 'text-[#888888] border-[#333333] bg-[#1a1a1a]'}`}>
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
    <div className="bg-[#181818] border border-[#242424] rounded-xl p-3 space-y-2 hover:border-[#333333] transition-colors">
      {/* Header Row: Title & Environment Chip on Left, Status Badge on Right */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-wrap">
          <span className="text-xs font-bold text-[#e5e5e5] whitespace-nowrap">{displayName}</span>
          {status?.environment && <EnvChip env={status.environment} />}
        </div>
        <StatusBadge
          status={st}
          errorMsg={status?.error ?? null}
          missingVars={status?.missing_env_vars ?? []}
        />
      </div>

      {/* Description */}
      <p className="text-[11px] text-[#888888] leading-snug line-clamp-2">
        {description}
      </p>

      {/* Last Sync */}
      {isConnected && status?.last_sync !== undefined && (
        <div className="text-[10px] text-[#555555] font-mono">
          Last sync: {formatRelativeTime(status.last_sync)}
        </div>
      )}

      {/* Backend unavailable fallback */}
      {!status && !isLoading && (
        <div className="text-[10px] text-[#555555] italic">Backend unavailable — status unknown</div>
      )}

      {/* Action buttons row */}
      <div className="flex items-center gap-1.5 pt-0.5 flex-wrap">
        {/* Connect */}
        {!isConnected && st !== 'connecting' && (
          <button
            onClick={onConnect}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold rounded-lg bg-purple-700 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white transition cursor-pointer shadow-sm"
          >
            {isLoading ? <Spinner /> : null}
            Connect
          </button>
        )}

        {/* Connecting indicator */}
        {st === 'connecting' && (
          <span className="flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold rounded-lg bg-blue-900/50 text-blue-300 border border-blue-800">
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
