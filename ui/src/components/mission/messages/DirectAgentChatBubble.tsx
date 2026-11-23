import React from 'react';

interface DirectChatProps {
  chatItem: {
    role: 'user' | 'agent';
    agent_key?: string;
    agent_name?: string;
    avatar?: string;
    text: string;
    recommendation?: string;
    confidence?: number;
    key_metrics?: Record<string, any>;
  };
  timestamp: string;
}

export const DirectAgentChatBubble: React.FC<DirectChatProps> = ({ chatItem, timestamp }) => {
  const isUser = chatItem.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end animate-in fade-in slide-in-from-bottom-1 duration-200">
        <div className="max-w-[85%] bg-[#222222] border border-[#333333] rounded-2xl rounded-tr-sm p-3 space-y-1 shadow-md">
          <div className="flex items-center justify-between gap-3 text-[10px] text-[#888888] pb-1 border-b border-[#2a2a2a]">
            <span className="font-semibold text-purple-300 flex items-center gap-1">
              <span>👤</span>
              <span>Elena Rostova (CEO)</span>
            </span>
            <span className="font-mono text-[#666666]">{timestamp}</span>
          </div>
          <div className="text-xs text-[#e8e8e8] leading-relaxed whitespace-pre-wrap font-sans">
            {chatItem.text}
          </div>
        </div>
      </div>
    );
  }

  // Agent Direct Response
  const formattedMetrics = chatItem.key_metrics
    ? Object.entries(chatItem.key_metrics).filter(([_, v]) => typeof v === 'number' || typeof v === 'string')
    : [];

  return (
    <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="max-w-[95%] w-full bg-[#181818] border border-[#2e2e2e] hover:border-[#383838] rounded-2xl rounded-tl-sm p-3.5 space-y-2.5 shadow-lg transition">
        {/* Header */}
        <div className="flex items-center justify-between text-xs pb-2 border-b border-[#262626]">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-[#222222] border border-[#333333] flex items-center justify-center text-xs shadow-sm">
              {chatItem.avatar || '🤖'}
            </span>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-white tracking-tight">
                  {chatItem.agent_name || 'Executive Agent'}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                  1-on-1 Dialogue
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[10px] font-mono text-[#777777]">
            {chatItem.confidence !== undefined && (
              <span className="text-purple-400 font-semibold">
                {(chatItem.confidence * 100).toFixed(0)}% conf
              </span>
            )}
            <span>{timestamp}</span>
          </div>
        </div>

        {/* Direct Agent Answer Text */}
        <div className="text-xs text-[#d8d8d8] leading-relaxed whitespace-pre-wrap font-sans">
          {chatItem.text}
        </div>

        {/* Telemetry metrics chip bar */}
        {formattedMetrics.length > 0 && (
          <div className="pt-2 border-t border-[#242424] flex flex-wrap gap-1.5">
            {formattedMetrics.map(([k, v]) => {
              const displayVal = typeof v === 'number'
                ? v > 1000
                  ? v.toLocaleString()
                  : v.toString()
                : String(v);

              return (
                <div
                  key={k}
                  className="px-2 py-0.5 rounded-md bg-[#141414] border border-[#282828] text-[10px] font-mono text-[#888888] flex items-center gap-1"
                >
                  <span className="text-[#666666] capitalize">{k.replace(/_/g, ' ')}:</span>
                  <span className="text-[#cccccc] font-semibold">{displayVal}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Recommendation footer */}
        {chatItem.recommendation && (
          <div className="flex items-center justify-between text-[10px] pt-1 text-[#666666]">
            <span className="capitalize flex items-center gap-1">
              <span>Guidance:</span>
              <span className="text-white font-medium">
                {chatItem.recommendation.replace(/_/g, ' ')}
              </span>
            </span>
            <span className="font-mono text-[#555555]">Grounded from live telemetry</span>
          </div>
        )}
      </div>
    </div>
  );
};
