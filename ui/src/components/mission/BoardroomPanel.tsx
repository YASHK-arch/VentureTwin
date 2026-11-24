import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { WarRoomMessage, SimulationCell } from '../../orchestration/useOrchestrationModel';
import { FindingItem, chatWithAgent, AgentChatResponse, fetchRoutingDecision, SupervisorRoutingDecision } from '../../api';
import { StagedFault } from '../FailureInjectorModal';
import { FindingBubble } from './messages/FindingBubble';
import { SkepticChallenge } from './messages/SkepticChallenge';
import { RebuttalBubble } from './messages/RebuttalBubble';
import { ConflictCard } from './messages/ConflictCard';
import { SimulationMatrix } from './messages/SimulationMatrix';
import { VerificationChecklist } from './messages/VerificationChecklist';
import { SystemNotice } from './messages/SystemNotice';
import { SealedCard } from './messages/SealedCard';
import { DirectAgentChatBubble } from './messages/DirectAgentChatBubble';

export interface BoardroomPanelProps {
  decisionQuery: string;
  setDecisionQuery: (q: string) => void;
  onLaunchDecision?: (queryToUse?: string) => void;
  onReset: () => void;
  workflowStatus: string;
  playbackSpeed?: 'cinematic' | 'instant';
  onTogglePlaybackSpeed?: (speed: 'cinematic' | 'instant') => void;
  onSkipToReport: () => void;
  onOpenReport: () => void;
  onInspectFinding?: (finding: FindingItem) => void;
  stagedFault: StagedFault | null;
  messages: WarRoomMessage[];
  simMatrix: SimulationCell[];
  completedSimCount: number;
  hasGivenPrompt: boolean;
  llmMode?: string;
  llmModel?: string;
  isOpen: boolean;
  onToggleOpen: () => void;
  isDataConnected?: boolean;
  onConnectData?: () => void;
}

export interface BoardroomOption {
  id: string;
  label: string;
  shortLabel: string;
  role: string;
  icon: string;
  color: string;
  description: string;
  placeholder: string;
  presets: string[];
}

export const BOARDROOM_OPTIONS: BoardroomOption[] = [
  {
    id: 'board',
    label: 'Whole Board (Consensus)',
    shortLabel: 'Whole Board',
    role: 'Multi-Agent Collective',
    icon: '🌐',
    color: 'text-purple-400',
    description: 'Executive consensus across all functional specialists',
    placeholder: 'Ask the Board any strategic SaaS question...',
    presets: [
      'Should we launch a free plan?',
      'Should we raise Starter price by 20%?',
      'Can we introduce an enterprise tier?',
      'How do we reduce customer churn?'
    ]
  },
  {
    id: 'supervisor',
    label: 'Supervisor',
    shortLabel: 'Supervisor',
    role: 'Executive Chief of Staff',
    icon: '🎯',
    color: 'text-blue-400',
    description: 'Strategic framing, cross-departmental scope & trade-off synthesis',
    placeholder: 'Ask Supervisor about strategic framing and departmental trade-offs...',
    presets: [
      'What is our highest-priority company objective?',
      'Where is the biggest conflict across executives?',
      'Synthesize our executive trade-offs for Q3'
    ]
  },
  {
    id: 'cfo',
    label: 'CFO Agent',
    shortLabel: 'CFO',
    role: 'Chief Financial Officer',
    icon: '💼',
    color: 'text-emerald-400',
    description: 'Cash reserves, burn rate, runway months, pricing floors & margin models',
    placeholder: 'Ask CFO about cash runway, burn rate, pricing floors, CAC:LTV...',
    presets: [
      'What is our verified runway and cash balance?',
      'Can we afford hiring 2 full-time engineers?',
      'What is our CAC payback period and margins?'
    ]
  },
  {
    id: 'growth',
    label: 'Growth Agent',
    shortLabel: 'Growth',
    role: 'VP Growth & CMO',
    icon: '📈',
    color: 'text-cyan-400',
    description: 'Visitor traffic, trial conversion, acquisition funnels & blended CAC',
    placeholder: 'Ask Growth about visitor traffic, trial conversion, CAC payback...',
    presets: [
      'How is our trial-to-paid conversion pacing?',
      'What is our blended CAC across channels?',
      'How do we scale monthly visitor traffic?'
    ]
  },
  {
    id: 'cto',
    label: 'CTO Agent',
    shortLabel: 'CTO',
    role: 'Chief Technology Officer',
    icon: '⚡',
    color: 'text-amber-400',
    description: 'Cloud compute expense, server hosting bills & scaling infrastructure',
    placeholder: 'Ask CTO about cloud infrastructure bills, compute costs, uptime...',
    presets: [
      'What is our monthly cloud compute spend?',
      'What is infra cost per active paid user?',
      'Can our infra handle a 10x traffic spike?'
    ]
  },
  {
    id: 'customer',
    label: 'Customer Success',
    shortLabel: 'Customer Success',
    role: 'VP Customer Success',
    icon: '🤝',
    color: 'text-indigo-400',
    description: 'Customer churn cohorts, retention dynamics & support ticket load',
    placeholder: 'Ask Customer Success about churn cohorts, retention, support load...',
    presets: [
      'What is our monthly logo churn rate?',
      'Are support tickets within FTE capacity?',
      'What are top reasons for customer cancellation?'
    ]
  },
  {
    id: 'product',
    label: 'Product Agent',
    shortLabel: 'Product',
    role: 'Chief Product Officer',
    icon: '📦',
    color: 'text-pink-400',
    description: 'Plan tier packaging, feature limit gating & self-serve upgrade velocity',
    placeholder: 'Ask Product about feature limits, plan tier packaging, self-serve...',
    presets: [
      'What are our current pricing tiers?',
      'Which features should be enterprise-gated?',
      'How do we accelerate self-serve upgrades?'
    ]
  },
  {
    id: 'skeptic',
    label: 'Skeptic Agent',
    shortLabel: 'Skeptic',
    role: 'Independent Risk Auditor',
    icon: '🛡️',
    color: 'text-rose-400',
    description: 'Devil\'s advocate stress-testing, downside vulnerabilities & market risks',
    placeholder: 'Ask Skeptic to challenge assumptions or stress-test downside risks...',
    presets: [
      'What is our single biggest point of vulnerability?',
      'What happens if macro churn spikes to 5%?',
      'How could competitors retaliate against our pricing?'
    ]
  }
];

export const BoardroomPanel: React.FC<BoardroomPanelProps> = ({
  decisionQuery,
  setDecisionQuery,
  onLaunchDecision,
  onReset,
  workflowStatus,
  playbackSpeed,
  onTogglePlaybackSpeed,
  onSkipToReport,
  onOpenReport,
  onInspectFinding,
  stagedFault,
  messages,
  simMatrix,
  completedSimCount,
  hasGivenPrompt,
  llmMode = 'mock',
  llmModel = 'gemini-3.5-flash-lite',
  isOpen,
  onToggleOpen,
  isDataConnected = false,
  onConnectData
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string>('board');
  const [showModeDropdown, setShowModeDropdown] = useState(false);

  // Local state for direct 1-on-1 dialogue with individual agents
  const [directChatMessages, setDirectChatMessages] = useState<WarRoomMessage[]>([]);
  const [isChatting, setIsChatting] = useState(false);
  const [routingPreview, setRoutingPreview] = useState<SupervisorRoutingDecision | null>(null);

  useEffect(() => {
    if (!decisionQuery || !decisionQuery.trim()) {
      setRoutingPreview(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const preview = await fetchRoutingDecision(decisionQuery.trim());
        setRoutingPreview(preview);
      } catch {
        // Silently handle preview errors
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [decisionQuery]);

  const isRunning = workflowStatus === 'running';
  const isComplete = workflowStatus === 'completed' || workflowStatus === 'degraded';
  const isInstant = false;

  const activeOption = useMemo(() => {
    return BOARDROOM_OPTIONS.find((o) => o.id === selectedAgent) || BOARDROOM_OPTIONS[0];
  }, [selectedAgent]);

  // Combined war room and direct chat stream
  const allMessages = useMemo(() => {
    return [...messages, ...directChatMessages];
  }, [messages, directChatMessages]);

  // Auto-scroll logic
  const scrollToBottom = useCallback(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: isInstant ? 'auto' : 'smooth'
      });
      setUserHasScrolledUp(false);
    }
  }, [isInstant]);

  useEffect(() => {
    if (!userHasScrolledUp) {
      scrollToBottom();
    }
  }, [allMessages.length, completedSimCount, userHasScrolledUp, scrollToBottom]);

  // Click outside listener for dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowModeDropdown(false);
      }
    };
    if (showModeDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showModeDropdown]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    if (distanceFromBottom > 80) {
      setUserHasScrolledUp(true);
    } else {
      setUserHasScrolledUp(false);
    }
  };

  // Direct Agent Chat Execution
  const handleDirectAgentChat = async (queryText?: string) => {
    const q = (queryText || decisionQuery).trim();
    if (!q || isChatting) return;

    if (!isDataConnected) {
      if (onConnectData) {
        onConnectData();
      }
      return;
    }

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Append user inquiry
    const userMsg: WarRoomMessage = {
      id: `chat_user_${Date.now()}`,
      type: 'chat',
      agent: 'CEO',
      timestamp: timeStr,
      chatItem: {
        role: 'user',
        text: q
      }
    };

    setDirectChatMessages((prev) => [...prev, userMsg]);
    setDecisionQuery('');
    setIsChatting(true);

    try {
      // 2. Call backend agent dialogue API (route 'board' to 'supervisor' as consensus voice)
      const targetAgentKey = selectedAgent === 'board' ? 'supervisor' : selectedAgent;
      const res: AgentChatResponse = await chatWithAgent(targetAgentKey, q);
      const agentMsg: WarRoomMessage = {
        id: `chat_agent_${Date.now()}`,
        type: 'chat',
        agent: selectedAgent === 'board' ? 'Whole Board' : res.agent_name,
        timestamp: new Date(res.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        chatItem: {
          role: 'agent',
          agent_key: selectedAgent === 'board' ? 'board' : res.agent_key,
          agent_name: selectedAgent === 'board' ? 'Whole Board (Consensus)' : res.agent_name,
          avatar: selectedAgent === 'board' ? '🌐' : res.avatar,
          text: res.response,
          recommendation: res.recommendation,
          confidence: res.confidence,
          key_metrics: res.key_metrics
        }
      };
      setDirectChatMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      console.error('Direct agent chat failed:', err);
      const errMsg: WarRoomMessage = {
        id: `chat_err_${Date.now()}`,
        type: 'system',
        agent: 'System',
        timestamp: timeStr,
        content: `Error communicating with ${selectedAgent.toUpperCase()}: ${err.message || 'Service unavailable'}`
      };
      setDirectChatMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsChatting(false);
    }
  };

  // Submit action dispatcher - chats inside Boardroom (does NOT trigger DAG simulation)
  const handleSubmit = (queryToRun?: string) => {
    if (!isDataConnected) {
      if (onConnectData) onConnectData();
      return;
    }
    const q = queryToRun || decisionQuery;
    if (!q.trim()) return;

    // Direct chat inside Boardroom for all selections
    handleDirectAgentChat(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isDataConnected && !isRunning && !isChatting && decisionQuery.trim()) {
        handleSubmit();
      }
    }
  };

  const handleClearSession = () => {
    setDirectChatMessages([]);
    onReset();
  };

  if (!isOpen) {
    return (
      <aside className="fixed right-0 top-14 bottom-7 z-30 flex flex-col justify-between py-4 px-1.5 bg-[#181818] border-l border-[#282828] select-none">
        <button
          onClick={onToggleOpen}
          className="p-2 rounded-lg bg-[#222222] hover:bg-[#2c2c2c] text-[#cccccc] hover:text-white border border-[#333333] transition-all flex flex-col items-center gap-1.5 shadow-md cursor-pointer"
          title="Open Boardroom Agent Panel"
        >
          <span className="text-sm">💬</span>
          <span className="text-[10px] font-mono [writing-mode:vertical-rl] tracking-wider uppercase text-purple-400 font-bold">
            Boardroom
          </span>
          {isRunning && (
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping mt-1" />
          )}
        </button>
      </aside>
    );
  }

  return (
    <aside className="w-full lg:w-[440px] xl:w-[480px] shrink-0 border-l border-[#282828] bg-[#181818] flex flex-col h-full overflow-hidden select-none shadow-2xl">
      {/* 1. Cursor Tab Bar Header */}
      <div className="px-3.5 py-2.5 bg-[#141414] border-b border-[#282828] flex items-center justify-between gap-2 shrink-0">
        {/* Active Tab Pill */}
        <div className="flex items-center gap-1.5 bg-[#1e1e1e] border border-[#2e2e2e] px-2.5 py-1 rounded-md text-xs font-sans text-[#e5e5e5]">
          <span className="text-purple-400 font-bold text-xs">{activeOption.icon}</span>
          <span className="font-semibold text-xs tracking-tight">Boardroom Agent</span>
          <span className="text-[10px] text-[#777777] font-mono">({activeOption.shortLabel})</span>
          <button
            onClick={handleClearSession}
            className="ml-1 text-[#888888] hover:text-[#ffffff] text-[11px] hover:bg-[#2a2a2a] rounded px-1 transition cursor-pointer"
            title="Reset Boardroom & Start New Agent Session"
          >
            ✕
          </button>
        </div>

        {/* Right Controls: New Session, Playback Speed, Skip to Report, Collapse */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleClearSession}
            className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#202020] text-[#888888] hover:text-[#cccccc] border border-[#2e2e2e] transition flex items-center gap-1 cursor-pointer"
            title="New Conversation Session"
          >
            <span>+</span>
            <span className="hidden sm:inline">New</span>
          </button>

          {isRunning && (
            <button
              onClick={onSkipToReport}
              className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-600/20 text-purple-300 border border-purple-500/30 hover:bg-purple-600/30 transition cursor-pointer"
              title="Fast-forward and skip straight to report"
            >
              Skip ➔
            </button>
          )}

          <button
            onClick={onToggleOpen}
            className="p-1 text-[#888888] hover:text-white hover:bg-[#252525] rounded transition text-xs cursor-pointer ml-1"
            title="Collapse Boardroom Panel"
          >
            ⇥
          </button>
        </div>
      </div>

      {/* 2. Cursor Prompt Input Container */}
      <div className="p-3 bg-[#181818] border-b border-[#242424] shrink-0 space-y-2">
        <div className="relative bg-[#1e1e1e] border border-[#2e2e2e] focus-within:border-[#444444] rounded-xl p-3 shadow-inner transition-colors">
          {/* Main Question Textarea */}
          <textarea
            ref={textareaRef}
            rows={2}
            value={decisionQuery}
            onChange={(e) => setDecisionQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isDataConnected || isRunning || isChatting}
            placeholder={
              !isDataConnected
                ? 'Connect company data to unlock Boardroom chat...'
                : activeOption.placeholder
            }
            className={`w-full bg-transparent text-xs sm:text-sm text-[#e5e5e5] placeholder-[#666666] outline-none resize-none font-sans leading-relaxed ${
              !isDataConnected ? 'cursor-not-allowed opacity-50' : ''
            }`}
          />

          {/* Bottom Bar Inside Input Box */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#262626] mt-1">
            {/* Left: Dynamic Mode Dropdown + Model Badge */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  disabled={!isDataConnected}
                  onClick={() => setShowModeDropdown(!showModeDropdown)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#242424] border border-[#383838] text-[11px] font-medium text-[#cccccc] transition ${
                    !isDataConnected
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:bg-[#2c2c2c] cursor-pointer'
                  }`}
                >
                  <span className={activeOption.color}>{activeOption.icon}</span>
                  <span className="font-semibold text-white">{activeOption.shortLabel}</span>
                  <span className="text-[9px] text-[#888888]">▾</span>
                </button>

                {/* Dropdown Menu - opens below the trigger button */}
                {showModeDropdown && (
                  <div className="absolute left-0 top-full mt-1.5 z-50 w-72 bg-[#1c1c1c] border border-[#383838] rounded-xl shadow-2xl py-1 text-xs divide-y divide-[#262626] backdrop-blur-md">
                    {/* Section 1: Whole Board (Default full workflow) */}
                    <div>
                      <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-[#777777]">
                        Orchestration Scope
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedAgent('board');
                          setShowModeDropdown(false);
                        }}
                        className={`w-full text-left px-3 py-2 flex items-start gap-2.5 hover:bg-[#262626] transition cursor-pointer ${
                          selectedAgent === 'board' ? 'bg-[#222222] text-purple-300' : 'text-[#d4d4d4]'
                        }`}
                      >
                        <span className="text-sm mt-0.5">🌐</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white">Whole Board</span>
                            {selectedAgent === 'board' && (
                              <span className="text-purple-400 text-xs">✓</span>
                            )}
                          </div>
                          <div className="text-[10px] text-[#888888] leading-tight mt-0.5">
                            Executive consensus across all functional specialists
                          </div>
                        </div>
                      </button>
                    </div>

                    {/* Section 2: Individual Executive Agents (1-on-1 Dialogue) */}
                    <div>
                      <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-[#777777]">
                        Individual Executive Agents
                      </div>
                      <div className="max-h-60 overflow-y-auto pr-1">
                        {BOARDROOM_OPTIONS.filter((o) => o.id !== 'board').map((opt) => (
                          <button
                            key={opt.id}
                            type="button"
                            onClick={() => {
                              setSelectedAgent(opt.id);
                              setShowModeDropdown(false);
                            }}
                            className={`w-full text-left px-3 py-2 flex items-start gap-2.5 hover:bg-[#262626] transition cursor-pointer ${
                              selectedAgent === opt.id ? 'bg-[#222222] text-purple-300' : 'text-[#d4d4d4]'
                            }`}
                          >
                            <span className="text-sm mt-0.5">{opt.icon}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-white">{opt.label}</span>
                                {selectedAgent === opt.id && (
                                  <span className="text-purple-400 text-xs">✓</span>
                                )}
                              </div>
                              <div className="text-[10px] text-[#888888] leading-tight truncate mt-0.5">
                                {opt.role} · {opt.description}
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Mic & Action Button */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                disabled={!isDataConnected}
                className={`p-1.5 rounded transition text-xs ${
                  !isDataConnected
                    ? 'text-[#555555] opacity-50 cursor-not-allowed'
                    : 'text-[#777777] hover:text-[#cccccc] hover:bg-[#282828] cursor-pointer'
                }`}
                title="Voice Dictation"
              >
                🎙️
              </button>
              <button
                onClick={() => handleSubmit()}
                disabled={!isDataConnected || isRunning || isChatting || !decisionQuery.trim()}
                className={`px-3 py-1.5 font-semibold text-xs rounded-lg transition shadow-md flex items-center gap-1.5 text-white ${
                  !isDataConnected
                    ? 'bg-[#262626] text-[#666666] cursor-not-allowed border border-[#333333]'
                    : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-purple-600/20 cursor-pointer'
                }`}
                title={
                  !isDataConnected
                    ? 'Connect company data to chat'
                    : selectedAgent === 'board'
                    ? 'Ask Whole Board directly'
                    : `Ask ${activeOption.shortLabel} directly`
                }
              >
                {isRunning || isChatting ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                    <span>Thinking...</span>
                  </>
                ) : (
                  <>
                    <span>Ask</span>
                    <span>➔</span>
                  </>
                )}
              </button>

              {selectedAgent === 'board' && onLaunchDecision && (
                <button
                  type="button"
                  onClick={() => onLaunchDecision(decisionQuery)}
                  disabled={!isDataConnected || isRunning || !decisionQuery.trim()}
                  className={`px-3 py-1.5 font-semibold text-xs rounded-lg transition shadow-md flex items-center gap-1.5 text-white ${
                    !isDataConnected
                      ? 'bg-[#262626] text-[#666666] cursor-not-allowed border border-[#333333]'
                      : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-teal-600/20 cursor-pointer'
                  }`}
                  title="Run multi-agent flight simulation DAG on this question"
                >
                  <span>Run DAG</span>
                  <span>➔</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Dynamic Groq Supervisor Routing Context Preview */}
        {routingPreview && (
          <div className="flex items-center justify-between text-[10px] font-mono px-2.5 py-1.5 bg-[#1a1625] border border-purple-500/30 text-purple-200 rounded-lg">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-purple-400 font-bold uppercase text-[9px] tracking-wider px-1.5 py-0.2 rounded bg-purple-500/20 border border-purple-500/40 shrink-0">
                Groq Supervisor
              </span>
              <span className="text-white font-semibold truncate">
                {routingPreview.selected_specialists.map((s) => s.toUpperCase()).join(' · ')}
              </span>
              <span className="text-slate-400 text-[9px] hidden sm:inline truncate">
                ({routingPreview.selected_specialists.length} Specialists Involved)
              </span>
            </div>
            <span className="text-[9px] text-purple-400/80 font-mono shrink-0 ml-2">
              {routingPreview.source === 'groq' ? 'Groq Llama 3.3' : 'Autonomous Router'}
            </span>
          </div>
        )}

        {/* Chaos Armed Alert if any */}
        {stagedFault && (
          <div className="flex items-center justify-between text-[10px] font-mono px-2.5 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-lg animate-pulse">
            <span className="flex items-center gap-1.5 font-bold">
              <span>⚡ Fault Armed:</span>
              <span className="uppercase">{stagedFault.agent}</span>
              <span>({stagedFault.mode})</span>
            </span>
          </div>
        )}

        {/* Quick Example Presets tailored to active selection */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] text-[#888888] scrollbar-none">
          {activeOption.presets.map((preset, idx) => (
            <button
              key={idx}
              disabled={!isDataConnected || isRunning || isChatting}
              onClick={() => {
                if (!isDataConnected) {
                  if (onConnectData) onConnectData();
                  return;
                }
                setDecisionQuery(preset);
                handleSubmit(preset);
              }}
              className={`px-2 py-0.5 rounded bg-[#222222] text-[#aaaaaa] border border-[#2e2e2e] transition whitespace-nowrap text-[10px] ${
                !isDataConnected
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:bg-[#2a2a2a] hover:text-white cursor-pointer'
              }`}
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Messages Stream (War Room Activity & 1-on-1 Dialogue) */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin scrollbar-thumb-[#2c2c2c] scrollbar-track-transparent bg-[#161616]"
      >
        {allMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#666666] space-y-3">
            {/* Custom Emblem */}
            <div className="w-12 h-12 rounded-xl bg-[#202020] border border-[#2e2e2e] flex items-center justify-center text-xl font-bold shadow-lg">
              {isDataConnected ? activeOption.icon : '🔒'}
            </div>
            <div className="space-y-1">
              <p className="text-xs font-mono text-[#cccccc] font-medium">
                {!isDataConnected
                  ? 'No Company Data Connected'
                  : selectedAgent === 'board'
                  ? 'Whole Board Ready'
                  : `${activeOption.label} Ready for Dialogue`}
              </p>
              <p className="text-[11px] text-[#777777] max-w-xs leading-relaxed">
                {!isDataConnected
                  ? 'Connect company data to unlock 1-on-1 executive dialogue and boardroom analysis.'
                  : selectedAgent === 'board'
                  ? 'Ask Whole Board a strategic question above. Executive consensus will be formulated based on your company context.'
                  : `Ask ${activeOption.shortLabel} specific questions about ${activeOption.description.toLowerCase()}.`}
              </p>
            </div>
            {!isDataConnected && onConnectData && (
              <button
                onClick={onConnectData}
                className="mt-1 px-3.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-lg shadow-md transition cursor-pointer font-sans flex items-center gap-1.5"
              >
                <span>+</span>
                <span>Connect Company Data</span>
              </button>
            )}
            <div className="pt-3 flex flex-col gap-1.5 text-[10px] font-mono text-[#555555]">
              <div className="flex items-center justify-between gap-4 px-2 py-1 bg-[#1a1a1a] rounded border border-[#252525]">
                <span>Ask Agent / Board</span>
                <span className="text-[#888888]">Enter</span>
              </div>
              <div className="flex items-center justify-between gap-4 px-2 py-1 bg-[#1a1a1a] rounded border border-[#252525]">
                <span>Multiline Input</span>
                <span className="text-[#888888]">Shift + Enter</span>
              </div>
            </div>
          </div>
        ) : (
          allMessages.map((msg) => {
            switch (msg.type) {
              case 'chat':
                if (!msg.chatItem) return null;
                return (
                  <DirectAgentChatBubble
                    key={msg.id}
                    chatItem={msg.chatItem}
                    timestamp={msg.timestamp}
                  />
                );

              case 'finding':
                if (!msg.finding) return null;
                return (
                  <FindingBubble
                    key={msg.id}
                    finding={msg.finding}
                    agent={msg.agent}
                    timestamp={msg.timestamp}
                    isInstant={isInstant}
                    onInspect={() => msg.finding && onInspectFinding && onInspectFinding(msg.finding)}
                  />
                );

              case 'challenge':
                return (
                  <SkepticChallenge
                    key={msg.id}
                    finding={msg.finding}
                    content={msg.content}
                    timestamp={msg.timestamp}
                  />
                );

              case 'rebuttal':
                if (!msg.rebuttal) return null;
                return (
                  <RebuttalBubble
                    key={msg.id}
                    rebuttal={msg.rebuttal}
                    timestamp={msg.timestamp}
                  />
                );

              case 'conflict':
                if (!msg.conflict) return null;
                return (
                  <ConflictCard
                    key={msg.id}
                    conflict={msg.conflict}
                    timestamp={msg.timestamp}
                  />
                );

              case 'simulation':
                return (
                  <SimulationMatrix
                    key={msg.id}
                    matrix={simMatrix}
                    completedCount={completedSimCount}
                  />
                );

              case 'verification':
                if (!msg.verification) return null;
                return (
                  <VerificationChecklist
                    key={msg.id}
                    verification={msg.verification}
                    timestamp={msg.timestamp}
                  />
                );

              case 'sealed':
                if (!msg.sealed) return null;
                return (
                  <SealedCard
                    key={msg.id}
                    sealed={msg.sealed}
                    timestamp={msg.timestamp}
                    onOpenReport={onOpenReport}
                  />
                );

              case 'system':
                return (
                  <SystemNotice
                    key={msg.id}
                    content={msg.content}
                    timestamp={msg.timestamp}
                  />
                );

              default:
                return null;
            }
          })
        )}
      </div>

      {/* 4. Bottom Footer Info Bar */}
      <div className="px-3.5 py-1.5 bg-[#141414] border-t border-[#242424] flex items-center justify-between text-[10px] font-mono text-[#777777] shrink-0">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${isRunning || isChatting ? 'bg-amber-400 animate-pulse' : 'bg-purple-400'}`} />
          <span>
            {allMessages.length} Boardroom items
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span>
            {selectedAgent === 'board' ? 'Orchestration Mode' : `Direct: ${activeOption.shortLabel}`}
          </span>
          <span className="text-[#333333]">|</span>
          <span>{isComplete ? 'Analysis Sealed' : isRunning ? 'Simulating' : isChatting ? 'Responding' : 'Standing by'}</span>
        </div>
      </div>
    </aside>
  );
};
