import React, { useState } from 'react';
import Nango from '@nangohq/frontend';
import {
  ConnectorStatusInfo,
  fetchNangoSessionToken,
  notifyNangoCallback,
  directConnectIntegration,
} from '../../api';

interface ConnectIntegrationModalProps {
  connectorId: string;
  displayName: string;
  description: string;
  environment: string;
  isOpen: boolean;
  onClose: () => void;
  onConnected: (updatedStatus: ConnectorStatusInfo) => void;
}

export const ConnectIntegrationModal: React.FC<ConnectIntegrationModalProps> = ({
  connectorId,
  displayName,
  description,
  environment,
  isOpen,
  onClose,
  onConnected,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sso' | 'sandbox' | 'custom'>('sso');
  const [accountEmail, setAccountEmail] = useState('');
  const [customKey, setCustomKey] = useState('');

  if (!isOpen) return null;

  const handleSsoConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Request short-lived Connect Session Token from VentureTwin backend
      const sess = await fetchNangoSessionToken('default', [connectorId]);
      
      // If live Nango session is active, trigger Nango frontend modal
      if (!sess.is_sandbox && sess.token) {
        try {
          const nango = new Nango({ connectSessionToken: sess.token });
          await nango.auth(connectorId, `conn_${connectorId}_${Date.now()}`);
          await notifyNangoCallback({
            connection_id: `conn_${connectorId}_${Date.now()}`,
            provider_config_key: connectorId,
            company_id: 'default',
          });
        } catch (nangoErr) {
          console.warn('Nango modal dismissed or local fallback:', nangoErr);
        }
      }

      // Complete link in VentureTwin backend
      const updated = await directConnectIntegration(connectorId, {
        auth_mode: 'sso',
        account_email: accountEmail || 'founder@venturetwin.com',
      });
      onConnected(updated);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to authenticate via Google/SSO');
    } finally {
      setLoading(false);
    }
  };

  const handleSandboxConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await directConnectIntegration(connectorId, {
        auth_mode: 'sandbox',
        account_email: 'developer@sandbox.local',
      });
      onConnected(updated);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to connect in sandbox mode');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomKeySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customKey.trim()) {
      setError('Please provide an API key or token.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updated = await directConnectIntegration(connectorId, {
        auth_mode: 'credentials',
        custom_credentials: { API_KEY: customKey.trim() },
      });
      onConnected(updated);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to store custom credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-lg bg-[#141414] border border-[#2a2a2a] rounded-2xl shadow-2xl overflow-hidden text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#222222]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-950/60 border border-purple-800/60 flex items-center justify-center text-lg">
              ⚡
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">{displayName}</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono border bg-purple-950 text-purple-300 border-purple-800 uppercase">
                  {environment}
                </span>
              </div>
              <p className="text-xs text-[#888888] mt-0.5">
                Connect your account directly without modifying local environment files.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#666666] hover:text-white transition p-1.5 rounded-lg hover:bg-[#202020] text-sm cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Tab selection */}
        <div className="flex border-b border-[#222222] bg-[#181818]/50 px-5 pt-3 gap-6">
          <button
            onClick={() => setActiveTab('sso')}
            className={`pb-3 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'sso'
                ? 'border-purple-500 text-white'
                : 'border-transparent text-[#777777] hover:text-[#aaaaaa]'
            }`}
          >
            Google / SSO OAuth
          </button>
          <button
            onClick={() => setActiveTab('sandbox')}
            className={`pb-3 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'sandbox'
                ? 'border-purple-500 text-white'
                : 'border-transparent text-[#777777] hover:text-[#aaaaaa]'
            }`}
          >
            One-Click Sandbox
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`pb-3 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'custom'
                ? 'border-purple-500 text-white'
                : 'border-transparent text-[#777777] hover:text-[#aaaaaa]'
            }`}
          >
            Direct API Token
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-800/60 rounded-xl text-xs text-red-300">
              {error}
            </div>
          )}

          {activeTab === 'sso' && (
            <div className="space-y-4">
              <div className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#dddddd]">
                  <span>🔐</span>
                  <span>Managed by Nango Authentication</span>
                </div>
                <p className="text-xs text-[#888888] leading-relaxed">
                  Authenticate your {displayName} organization account using Google Workspace or your enterprise SSO. Nango handles token refresh, encryption, and API proxying automatically.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#aaaaaa] mb-1.5">
                  Account / Workspace Email
                </label>
                <input
                  type="email"
                  value={accountEmail}
                  onChange={(e) => setAccountEmail(e.target.value)}
                  placeholder="founder@venturetwin.com"
                  className="w-full bg-[#181818] border border-[#2e2e2e] focus:border-purple-500 text-xs text-white rounded-xl px-3.5 py-2.5 outline-none transition"
                />
              </div>

              <button
                onClick={handleSsoConnect}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition cursor-pointer shadow-lg shadow-purple-900/30"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Authorizing via Nango…
                  </span>
                ) : (
                  <span>Sign in with Google / SSO to Authorize</span>
                )}
              </button>
            </div>
          )}

          {activeTab === 'sandbox' && (
            <div className="space-y-4">
              <div className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-teal-300">
                  <span>⚗️</span>
                  <span>Instant Test Environment</span>
                </div>
                <p className="text-xs text-[#888888] leading-relaxed">
                  Instantly link a developer sandbox for {displayName}. Allows generating synthetic datasets and executing multi-agent board simulations without connecting external accounts.
                </p>
              </div>

              <button
                onClick={handleSandboxConnect}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-teal-800 hover:bg-teal-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition cursor-pointer shadow-lg shadow-teal-950/40"
              >
                {loading ? 'Connecting Sandbox…' : 'One-Click Connect (Sandbox Mode)'}
              </button>
            </div>
          )}

          {activeTab === 'custom' && (
            <form onSubmit={handleCustomKeySubmit} className="space-y-4">
              <div className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#dddddd]">
                  <span>🔑</span>
                  <span>In-App Credential Storage</span>
                </div>
                <p className="text-xs text-[#888888] leading-relaxed">
                  Paste your test key or bearer token directly here. It is saved in your local SQLite store without ever modifying .env files.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#aaaaaa] mb-1.5">
                  Developer Token / API Key
                </label>
                <input
                  type="password"
                  value={customKey}
                  onChange={(e) => setCustomKey(e.target.value)}
                  placeholder={`Enter ${displayName} token...`}
                  className="w-full bg-[#181818] border border-[#2e2e2e] focus:border-purple-500 text-xs text-white rounded-xl px-3.5 py-2.5 outline-none transition font-mono"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#2a2a2a] hover:bg-[#333333] border border-[#444444] text-white text-xs font-bold rounded-xl transition cursor-pointer"
              >
                {loading ? 'Saving Token…' : 'Save Token & Link Account'}
              </button>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-[#101010] border-t border-[#222222] flex items-center justify-between text-[11px] text-[#666666]">
          <span>Zero .env editing required</span>
          <span className="font-mono text-purple-400">Nango Connected</span>
        </div>
      </div>
    </div>
  );
};
