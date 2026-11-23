import React from 'react';
import { VentureTwinLogo } from './auth/VentureTwinLogo';

interface EmptyWorkspaceProps {
  onConnectData: () => void;
}

export const EmptyWorkspace: React.FC<EmptyWorkspaceProps> = ({ onConnectData }) => {
  return (
    <div className="h-[calc(100vh-140px)] w-full flex flex-col items-center justify-center p-6 select-none animate-in fade-in duration-300">
      <div className="flex flex-col items-center text-center max-w-lg mx-auto">
        {/* Prominent VentureTwin Logo */}
        <VentureTwinLogo size="hero" glow={true} pulsing={false} showText={false} />

        <h1 className="text-xl font-bold tracking-tight text-white mt-6 font-sans">
          VentureTwin
        </h1>
        <p className="text-xs text-[#888888] font-sans mt-1">
          Autonomous Executive Digital Twin &amp; Flight Simulator
        </p>

        {/* Cursor-Inspired Minimal Spec Grid */}
        <div className="w-full max-w-sm mt-8 space-y-2 text-xs font-mono text-[#666666]">
          <div className="flex items-center justify-between py-1.5 border-b border-[#222222]">
            <span>Telemetry Status</span>
            <span className="text-[#aaaaaa] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80" />
              <span>No Data Connected</span>
            </span>
          </div>
          <div className="flex items-center justify-between py-1.5 border-b border-[#222222]">
            <span>Executive Board</span>
            <span className="text-[#aaaaaa]">5 Specialists + 1 Skeptic</span>
          </div>
          <div className="flex items-center justify-between py-1.5 border-b border-[#222222]">
            <span>Simulation Engine</span>
            <span className="text-[#aaaaaa]">11-Node Multi-Agent DAG</span>
          </div>
          <div className="flex items-center justify-between py-1.5 border-b border-[#222222]">
            <span>Verification Gate</span>
            <span className="text-[#aaaaaa]">15 Algorithmic Invariant Audits</span>
          </div>
        </div>

        {/* Future Integration Support & Connection Action */}
        <div className="mt-8 flex flex-col items-center gap-2">
          <button
            onClick={onConnectData}
            className="px-4 py-2 bg-[#1c1c1c] hover:bg-[#262626] text-purple-300 hover:text-white border border-[#2e2e2e] hover:border-purple-500/40 rounded-xl text-xs font-medium transition-all shadow-md flex items-center gap-2 cursor-pointer font-sans"
            title="Connect company telemetry to populate executive digital twin"
          >
            <span className="text-purple-400 font-bold">+</span>
            <span>Connect Company Data</span>
          </button>
          <span className="text-[10px] text-[#555555] font-mono">
            Awaiting data source onboarding
          </span>
        </div>
      </div>
    </div>
  );
};
