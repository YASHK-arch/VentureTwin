import React, { useState, useEffect } from 'react';
import {
  fetchCompany,
  fetchHealth,
  submitDecision,
  fetchDecisionStatus,
  fetchDecisionReport,
  injectFailure,
  fetchAuthMe,
  logout,
  UserProfile,
  CompanySnapshot,
  TaskItem,
  FindingItem,
  EventItem,
  CompanyContextRecord
} from './api';
import { CompanySnapshotCard } from './components/CompanySnapshotCard';
import { MissionControl } from './components/mission/MissionControl';
import { BoardroomPanel } from './components/mission/BoardroomPanel';
import { EmptyWorkspace } from './components/EmptyWorkspace';
import { ConnectCompanyDataPage } from './components/connect/ConnectCompanyDataPage';
import { StagedFault } from './components/FailureInjectorModal';
import { DecisionReportView } from './components/DecisionReportView';
import { CalibrationView } from './components/CalibrationView';
import { CompanyGraphView } from './components/CompanyGraphView';
import { ErrorBoundary } from './components/ErrorBoundary';
import { useEventChoreographer } from './orchestration/useEventChoreographer';
import { useOrchestrationModel } from './orchestration/useOrchestrationModel';
import {
  CompanyConnectionState,
  INITIAL_AGENT_SLOTS
} from './orchestration/integrationTypes';
import { AuthScreen } from './components/auth/AuthScreen';
import { ExecutiveProfilePill } from './components/auth/ExecutiveProfilePill';
import { VentureTwinLogo } from './components/auth/VentureTwinLogo';

export const App: React.FC = () => {
  // Authentication state
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  const [activeTab, setActiveTab] = useState<'console' | 'connect' | 'report' | 'calibration' | 'graph'>('console');
  const [company, setCompany] = useState<CompanySnapshot | null>(null);
  const [connectionState, setConnectionState] = useState<CompanyConnectionState>({
    isDataConnected: false,
    connectedAt: null,
    company: null,
    agentSlots: INITIAL_AGENT_SLOTS
  });
  const [health, setHealth] = useState<{ llm_mode: string; provider: string; model: string } | null>(null);
  
  // Workflow state
  const [decisionQuery, setDecisionQuery] = useState('Should we launch a free plan?');
  const [currentDecisionId, setCurrentDecisionId] = useState<string | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<string>('idle');
  const [tasks, setTasks] = useState<Record<string, TaskItem>>({});
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [report, setReport] = useState<any>(null);
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null);
  const [stagedFault, setStagedFault] = useState<StagedFault | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = useState<'cinematic' | 'instant'>('cinematic');
  const [isBoardroomOpen, setIsBoardroomOpen] = useState(true);

  const isDataConnected = Boolean(company && connectionState.isDataConnected);
  const hasGivenPrompt = Boolean(currentDecisionId);
  const isRunMode = Boolean(currentDecisionId && workflowStatus !== 'idle');
  const isRealMode = (health?.llm_mode || '').trim() === 'real';

  // Event Choreographer for pacing live events
  const {
    choreographedEvents,
    skipToReport,
    reset: resetChoreographer
  } = useEventChoreographer(events, {
    speed: playbackSpeed,
    isRealMode
  });

  // Orchestration Model (shared between Main Stage and Boardroom Panel)
  const model = useOrchestrationModel(choreographedEvents, tasks, findings, workflowStatus);

  // Check active executive session on mount
  useEffect(() => {
    fetchAuthMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setCurrentUser(res.user);
        }
      })
      .catch(() => {
        setCurrentUser(null);
      })
      .finally(() => {
        setIsCheckingAuth(false);
      });
  }, []);

  // Guard tabs: if user has not given a prompt, restrict to console (allow connect tab anytime)
  useEffect(() => {
    if (!hasGivenPrompt && activeTab !== 'console' && activeTab !== 'connect') {
      setActiveTab('console');
    }
  }, [hasGivenPrompt, activeTab]);

  // Data-first onboarding: only fetch health status on login.
  // DO NOT automatically fetch or initialize synthetic company data.
  useEffect(() => {
    if (currentUser) {
      fetchHealth().then(setHealth).catch(console.error);
    }
  }, [currentUser]);

  // Poll workflow status when a decision is active
  useEffect(() => {
    if (!currentDecisionId || report) return;

    const interval = setInterval(async () => {
      try {
        const data = await fetchDecisionStatus(currentDecisionId);
        setWorkflowStatus(data.status);
        if (data.tasks) setTasks(data.tasks);
        if (data.findings) setFindings(data.findings);

        if (data.has_report || data.status === 'completed' || data.status === 'degraded') {
          try {
            const rep = await fetchDecisionReport(currentDecisionId);
            if (rep) {
              setReport(rep);
              clearInterval(interval);
            }
          } catch (e) {
            // Report is still generating in background, keep polling
          }
        } else if (data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [currentDecisionId, report]);

  // Connect to SSE stream
  useEffect(() => {
    if (!currentDecisionId) return;

    const eventSource = new EventSource(`/api/decisions/${currentDecisionId}/stream`);
    eventSource.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        setEvents((prev) => [...prev, parsed]);

        if (parsed.type === 'report_ready' || parsed.type === 'workflow_completed' || parsed.type === 'workflow_degraded') {
          fetchDecisionStatus(currentDecisionId).then((data) => {
            setWorkflowStatus(data.status);
            if (data.tasks) setTasks(data.tasks);
            if (data.findings) setFindings(data.findings);
          }).catch(console.error);

          fetchDecisionReport(currentDecisionId).then((rep) => {
            if (rep) setReport(rep);
          }).catch(console.error);
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };
    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [currentDecisionId]);

  // Connect company data (prepared for future integration & onboarding panel)
  const handleConnectCompanyData = async (sourceData?: CompanySnapshot) => {
    try {
      const data = sourceData || (await fetchCompany());
      setCompany(data);
      setConnectionState({
        isDataConnected: true,
        connectedAt: new Date().toISOString(),
        company: data,
        agentSlots: {
          cfo: { ...INITIAL_AGENT_SLOTS.cfo, status: 'connected', connectedSourceId: 'company_financials', lastSyncAt: new Date().toISOString() },
          growth: { ...INITIAL_AGENT_SLOTS.growth, status: 'connected', connectedSourceId: 'funnel_telemetry', lastSyncAt: new Date().toISOString() },
          cto: { ...INITIAL_AGENT_SLOTS.cto, status: 'connected', connectedSourceId: 'cloud_infrastructure', lastSyncAt: new Date().toISOString() },
          customer: { ...INITIAL_AGENT_SLOTS.customer, status: 'connected', connectedSourceId: 'customer_metrics', lastSyncAt: new Date().toISOString() },
          product: { ...INITIAL_AGENT_SLOTS.product, status: 'connected', connectedSourceId: 'tier_matrix', lastSyncAt: new Date().toISOString() }
        }
      });
    } catch (err) {
      console.error('Failed to connect company data:', err);
    }
  };

  const handleCompanyContextSaved = async (context: CompanyContextRecord) => {
    try {
      const baseSnapshot = await fetchCompany();
      const enrichedSnapshot: CompanySnapshot = {
        ...baseSnapshot,
        company_name: context.company_name || baseSnapshot.company_name,
        stage: context.stage || baseSnapshot.stage
      };
      await handleConnectCompanyData(enrichedSnapshot);
    } catch {
      await handleConnectCompanyData();
    }
  };

  const handleDisconnectCompanyData = () => {
    setCompany(null);
    setConnectionState({
      isDataConnected: false,
      connectedAt: null,
      company: null,
      agentSlots: INITIAL_AGENT_SLOTS
    });
    handleResetToNewQuestion();
  };

  const handleLaunchDecision = async (queryToUse?: string) => {
    const q = queryToUse || decisionQuery;
    try {
      // If company data is not yet connected, connect it to enable the simulation engine
      if (!isDataConnected || !company) {
        await handleConnectCompanyData();
      }
      setWorkflowStatus('running');
      setTasks({});
      setFindings([]);
      setEvents([]);
      setReport(null);
      resetChoreographer();

      const res = await submitDecision(q, undefined, stagedFault || undefined);
      if (res.status === 'needs_clarification') {
        setWorkflowStatus('idle');
        const opts = (res.options || []).join(', ');
        alert(`${res.clarification_prompt}\n\nSuggested: ${opts}`);
        return;
      }
      setCurrentDecisionId(res.decision_id);
      setStagedFault(null);
      setActiveTab('console');
    } catch (err: any) {
      alert(`Launch error: ${err.message}`);
      setWorkflowStatus('idle');
    }
  };

  const handleResetToNewQuestion = () => {
    setCurrentDecisionId(null);
    setWorkflowStatus('idle');
    setTasks({});
    setFindings([]);
    setEvents([]);
    setReport(null);
    setSelectedFinding(null);
    resetChoreographer();
  };

  const handleInjectFault = async (agent: string, mode: string, persist: boolean = false, failAttempts: number = 1) => {
    if (!currentDecisionId) {
      throw new Error('No active decision running. Please submit a question first.');
    }
    await injectFailure(currentDecisionId, agent, mode, persist, failAttempts);
  };

  const handleOpenReport = async () => {
    setActiveTab('report');
    if (!report && currentDecisionId) {
      try {
        const rep = await fetchDecisionReport(currentDecisionId);
        if (rep) setReport(rep);
      } catch (e) {
        console.warn('Report fetch notice:', e);
      }
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (e) {
      console.warn('Logout notice:', e);
    } finally {
      setCurrentUser(null);
      setCompany(null);
      setConnectionState({
        isDataConnected: false,
        connectedAt: null,
        company: null,
        agentSlots: INITIAL_AGENT_SLOTS
      });
      handleResetToNewQuestion();
    }
  };

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center text-[#d4d4d4] select-none">
        <VentureTwinLogo size="hero" pulsing={true} glow={true} showSubtitle={true} />
        <div className="mt-8 flex items-center gap-2.5 text-xs font-mono text-purple-400 uppercase tracking-widest">
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
          <span>Verifying Executive Session...</span>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <AuthScreen
        onAuthenticated={(user) => {
          setCurrentUser(user);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#121212] text-[#d4d4d4] flex flex-col font-sans select-none overflow-hidden h-screen">
      {/* 1. VentureTwin Navigation Bar */}
      <header className="border-b border-[#282828] bg-[#141414] select-none sticky top-0 z-40 shrink-0 h-14">
        <div className="w-full px-4 sm:px-6 h-full flex items-center justify-between gap-4">
          {/* Left: VentureTwin Logo & Flat Menu Navigation Items */}
          <div className="flex items-center gap-4">
            <VentureTwinLogo size="nav" showText={true} badgeText="SwarmFlow Engine" />

            <div className="h-5 w-[1px] bg-[#2e2e2e] hidden sm:block" />

            {/* Flat Menu Navigation Items */}
            <nav className="flex items-center gap-1">
              <button
                onClick={() => setActiveTab('console')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer font-sans ${
                  activeTab === 'console'
                    ? 'text-white font-bold bg-[#262626] shadow-sm'
                    : 'text-[#888888] hover:text-[#e0e0e0] hover:bg-[#1e1e1e]'
                }`}
              >
                Decision Console
              </button>
              <button
                disabled={!isDataConnected || !hasGivenPrompt || (workflowStatus === 'running' && !report)}
                onClick={handleOpenReport}
                title={
                  !isDataConnected
                    ? 'Connect company data to unlock decision reports'
                    : !hasGivenPrompt
                    ? 'Please submit a prompt in the Decision Console first'
                    : !report && workflowStatus === 'running'
                    ? 'Report will be available once the simulation completes'
                    : 'View verified decision report'
                }
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer font-sans ${
                  !isDataConnected || !hasGivenPrompt || (workflowStatus === 'running' && !report)
                    ? 'opacity-40 cursor-not-allowed text-[#555555]'
                    : activeTab === 'report'
                    ? 'text-white font-bold bg-[#262626] shadow-sm'
                    : 'text-[#888888] hover:text-[#e0e0e0] hover:bg-[#1e1e1e]'
                }`}
              >
                Decision Report {report ? '✓' : workflowStatus === 'running' ? '⏳' : ''}
              </button>
              <button
                disabled={!isDataConnected || !hasGivenPrompt}
                onClick={() => {
                  if (!isDataConnected || !hasGivenPrompt) return;
                  setActiveTab('calibration');
                }}
                title={
                  !isDataConnected
                    ? 'Connect company data to unlock calibration memory'
                    : !hasGivenPrompt
                    ? 'Please submit a prompt in the Decision Console first'
                    : 'View decision calibration & outcome memory'
                }
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer font-sans ${
                  !isDataConnected || !hasGivenPrompt
                    ? 'opacity-40 cursor-not-allowed text-[#555555]'
                    : activeTab === 'calibration'
                    ? 'text-white font-bold bg-[#262626] shadow-sm'
                    : 'text-[#888888] hover:text-[#e0e0e0] hover:bg-[#1e1e1e]'
                }`}
              >
                Calibration &amp; Memory
              </button>
              <button
                disabled={!isDataConnected || !hasGivenPrompt}
                onClick={() => {
                  if (!isDataConnected || !hasGivenPrompt) return;
                  setActiveTab('graph');
                }}
                title={
                  !isDataConnected
                    ? 'Connect company data to unlock company graph'
                    : !hasGivenPrompt
                    ? 'Please submit a prompt in the Decision Console first'
                    : 'View company dependency graph'
                }
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer font-sans ${
                  !isDataConnected || !hasGivenPrompt
                    ? 'opacity-40 cursor-not-allowed text-[#555555]'
                    : activeTab === 'graph'
                    ? 'text-white font-bold bg-[#262626] shadow-sm'
                    : 'text-[#888888] hover:text-[#e0e0e0] hover:bg-[#1e1e1e]'
                }`}
              >
                Company Graph
              </button>
            </nav>
          </div>

          {/* Right: Boardroom Dock Toggle & Executive User Profile */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsBoardroomOpen(!isBoardroomOpen)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-mono transition flex items-center gap-1.5 cursor-pointer ${
                isBoardroomOpen
                  ? 'bg-purple-950/40 text-purple-300 border border-purple-800/50 font-semibold shadow-sm'
                  : 'bg-[#202020] text-[#888888] border border-[#2e2e2e] hover:text-[#cccccc]'
              }`}
              title="Toggle Right Boardroom Panel"
            >
              <span>💬</span>
              <span>Boardroom</span>
            </button>

            <ExecutiveProfilePill user={currentUser} onLogout={handleLogout} />
          </div>
        </div>
      </header>

      {/* 2. Main Workspace Layout Area (Flex Row) */}
      <div className="flex-1 flex overflow-hidden min-h-0 relative">
        {/* Left / Center Main Canvas (flex-1) */}
        <main className="flex-1 min-w-0 overflow-y-auto px-4 sm:px-6 py-4 space-y-4 scrollbar-thin scrollbar-thumb-[#282828] scrollbar-track-transparent bg-[#121212]">
          <ErrorBoundary onReset={() => setActiveTab('console')}>
            {activeTab === 'connect' ? (
              <ConnectCompanyDataPage
                onCompanyConnected={handleCompanyContextSaved}
                onNavigateToConsole={() => setActiveTab('console')}
              />
            ) : !isDataConnected || !company ? (
              <EmptyWorkspace onConnectData={() => setActiveTab('connect')} />
            ) : (
              <>
                {/* Mode & Health Banners */}
                {((health?.llm_mode || '').trim() === 'real') && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-2.5 flex items-center justify-between text-xs text-emerald-300">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold uppercase tracking-wider text-[10px]">
                        Live LLM Mode
                      </span>
                      <span>
                        Connected to {health?.provider} ({health?.model}) with live multi-agent orchestration.
                      </span>
                    </div>
                    <span className="text-[11px] text-emerald-400/80 font-mono">LLM_MODE=real</span>
                  </div>
                )}

                {((health?.llm_mode || '').trim() === 'mock') && (
                  <div className="bg-[#1c1c1c] border border-[#2e2e2e] rounded-xl p-2.5 flex items-center justify-between text-xs text-[#cccccc]">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold uppercase tracking-wider text-[10px] font-mono">
                        Deterministic Mock Mode
                      </span>
                      <span className="text-[#888888]">
                        Specialist agents compute structured assumptions from tool telemetry. Use the right Boardroom panel to run strategic questions.
                      </span>
                    </div>
                    <span className="text-[11px] text-purple-400/80 font-mono">LLM_MODE=mock</span>
                  </div>
                )}

                {workflowStatus === 'degraded' && (
                  <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-2.5 flex items-center justify-between text-xs text-orange-200">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 font-bold uppercase tracking-wider text-[10px]">
                        Degraded Execution
                      </span>
                      <span>
                        One or more agent processes encountered unrecoverable runtime faults. Backup Analyst estimates applied.
                      </span>
                    </div>
                    <span className="text-[11px] text-orange-400/80 font-mono">Workflow Degraded</span>
                  </div>
                )}

                {/* Company Snapshot Card: Compact ticker in run mode, full card in idle */}
                <CompanySnapshotCard snapshot={company} compact={isRunMode} />

                {/* Tab 1: Decision Console (Mission Control Canvas) */}
                {activeTab === 'console' && (
                  <MissionControl
                    choreographedEvents={choreographedEvents}
                    rawEvents={events}
                    tasks={tasks}
                    findings={findings}
                    workflowStatus={workflowStatus}
                    playbackSpeed={playbackSpeed}
                    onTogglePlaybackSpeed={setPlaybackSpeed}
                    onSkipToReport={skipToReport}
                    onOpenReport={handleOpenReport}
                    onInspectFinding={setSelectedFinding}
                    onInjectFault={handleInjectFault}
                    stagedFault={stagedFault}
                    onSetStagedFault={setStagedFault}
                    model={model}
                  />
                )}

                {/* Tab 2: Decision Report */}
                {activeTab === 'report' && (
                  hasGivenPrompt && report ? (
                    <DecisionReportView
                      report={report}
                      decisionId={currentDecisionId || ''}
                      onApprovalDone={() => setActiveTab('calibration')}
                    />
                  ) : (
                    <div className="bg-[#181818] border border-[#282828] rounded-2xl p-12 text-center shadow-xl space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-[#222222] border border-[#333333] flex items-center justify-center text-[#aaaaaa] text-xl font-bold">
                        🔒
                      </div>
                      <h3 className="text-lg font-bold text-white">Decision Report Unavailable</h3>
                      <p className="text-sm text-[#888888] max-w-md mx-auto">
                        {!hasGivenPrompt
                          ? 'Please submit a strategic question prompt in the Boardroom panel on the right first to generate a decision report.'
                          : 'Simulation is currently running. The verified decision report will be available once all agent analysis waves complete.'}
                      </p>
                      <button
                        onClick={() => setActiveTab('console')}
                        className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl shadow-lg transition cursor-pointer"
                      >
                        Go to Decision Console
                      </button>
                    </div>
                  )
                )}

                {/* Tab 3: Calibration & Outcome Memory */}
                {activeTab === 'calibration' && (
                  hasGivenPrompt ? (
                    <CalibrationView />
                  ) : (
                    <div className="bg-[#181818] border border-[#282828] rounded-2xl p-12 text-center shadow-xl space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-[#222222] border border-[#333333] flex items-center justify-center text-[#aaaaaa] text-xl font-bold">
                        🔒
                      </div>
                      <h3 className="text-lg font-bold text-white">Calibration &amp; Memory Locked</h3>
                      <p className="text-sm text-[#888888] max-w-md mx-auto">
                        Please submit a strategic question prompt in the Boardroom panel on the right first to initialize simulation telemetry and calibration memory.
                      </p>
                      <button
                        onClick={() => setActiveTab('console')}
                        className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl shadow-lg transition cursor-pointer"
                      >
                        Go to Decision Console
                      </button>
                    </div>
                  )
                )}

                {/* Tab 4: Company Graph */}
                {activeTab === 'graph' && (
                  hasGivenPrompt ? (
                    <CompanyGraphView />
                  ) : (
                    <div className="bg-[#181818] border border-[#282828] rounded-2xl p-12 text-center shadow-xl space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-[#222222] border border-[#333333] flex items-center justify-center text-[#aaaaaa] text-xl font-bold">
                        🔒
                      </div>
                      <h3 className="text-lg font-bold text-white">Company Graph Locked</h3>
                      <p className="text-sm text-[#888888] max-w-md mx-auto">
                        Please submit a strategic question prompt in the Boardroom panel on the right first to inspect the company dependency graph for your scenario.
                      </p>
                      <button
                        onClick={() => setActiveTab('console')}
                        className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl shadow-lg transition cursor-pointer"
                      >
                        Go to Decision Console
                      </button>
                    </div>
                  )
                )}
              </>
            )}
          </ErrorBoundary>
        </main>

        {/* Right Fixed Panel: The Cursor Boardroom Agent */}
        <BoardroomPanel
          decisionQuery={decisionQuery}
          setDecisionQuery={setDecisionQuery}
          onLaunchDecision={handleLaunchDecision}
          onReset={handleResetToNewQuestion}
          workflowStatus={workflowStatus}
          playbackSpeed={playbackSpeed}
          onTogglePlaybackSpeed={setPlaybackSpeed}
          onSkipToReport={skipToReport}
          onOpenReport={handleOpenReport}
          onInspectFinding={setSelectedFinding}
          stagedFault={stagedFault}
          messages={model.messages}
          simMatrix={model.simMatrix}
          completedSimCount={model.completedSimCount}
          hasGivenPrompt={hasGivenPrompt}
          llmMode={health?.llm_mode}
          llmModel={health?.model}
          isOpen={isBoardroomOpen}
          onToggleOpen={() => setIsBoardroomOpen(!isBoardroomOpen)}
          isDataConnected={isDataConnected}
          onConnectData={() => setActiveTab('connect')}
        />
      </div>

      {/* 3. Bottom Status Bar */}
      <footer className="h-7 bg-[#141414] border-t border-[#242424] px-3 flex items-center justify-between text-[11px] font-mono text-[#777777] select-none shrink-0 z-30">
        <div className="flex items-center gap-3">
          <span>
            Boardroom: {isDataConnected ? `${model.activeAgentsCount}/7 Active` : 'Awaiting Data'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {isDataConnected && company ? (
            <span className="hidden md:inline text-[#999999]">
              {company.company_name} ({company.stage}) · {company.runway_months.toFixed(1)}mo Runway
            </span>
          ) : (
            <span className="hidden md:inline text-[#666666] font-mono text-[10px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80" />
              <span>No company data connected</span>
            </span>
          )}
          <span className="text-[#333333] hidden md:inline">|</span>
          <span className="text-purple-400/90 font-medium">
            LLM_MODE={health?.llm_mode || 'mock'}
          </span>
        </div>
      </footer>

      {/* Finding Inspector Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#181818] border border-[#2e2e2e] rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#282828]">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-white uppercase">{selectedFinding.agent || 'Agent'} Finding</span>
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-[#222222] text-[#cccccc] border border-[#333333]">
                  {selectedFinding.task_id || ''}
                </span>
                {selectedFinding.recovered_via_backup && (
                  <span className="text-xs px-2 py-0.5 rounded font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    🛡️ Recovered by Backup Analyst
                  </span>
                )}
                {selectedFinding.degraded && (
                  <span className="text-xs px-2 py-0.5 rounded font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    ⚠️ Degraded Prior
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                className="text-[#888888] hover:text-white text-lg font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div>
              <div className="text-xs font-semibold text-[#888888] uppercase tracking-wider mb-1">Core Claim</div>
              <div className="text-sm text-[#e0e0e0] bg-[#141414] p-3 rounded-xl border border-[#282828]">
                {selectedFinding.claim || 'No claim recorded'}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <div>
                <span className="text-[#888888]">Recommendation:</span>{' '}
                <span className="font-bold text-white capitalize">{String(selectedFinding.recommendation || 'proceed').replace(/_/g, ' ')}</span>
              </div>
              <div>
                <span className="text-[#888888]">Confidence:</span>{' '}
                <span className="font-bold text-purple-400">{(Number(selectedFinding.confidence ?? 0.5) * 100).toFixed(0)}%</span>
              </div>
            </div>

            {selectedFinding.assumptions?.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-[#888888] uppercase tracking-wider mb-1">Proposed Assumptions</div>
                <div className="space-y-2">
                  {selectedFinding.assumptions.map((asm: any, idx: number) => (
                    <div key={idx} className="p-2.5 bg-[#141414] rounded-lg border border-[#282828] text-xs font-mono">
                      <div className="flex justify-between text-[#cccccc] font-semibold font-sans">
                        <span>{asm.name}</span>
                        <span className="text-[#888888] font-mono">[{asm.low} - {asm.base} - {asm.high}] {asm.unit}</span>
                      </div>
                      <div className="text-[10px] text-[#666666] mt-1">
                        Provenance: <span className="text-purple-400 font-sans">{asm.provenance}</span> | Source: {asm.source_ref || 'None'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 flex items-center justify-between">
              {(selectedFinding.recovered_via_backup || selectedFinding.degraded) ? (
                <button
                  onClick={async () => {
                    try {
                      await handleInjectFault(selectedFinding.agent, 'heal');
                      setSelectedFinding(null);
                    } catch (e: any) {
                      console.error(e);
                    }
                  }}
                  className="px-4 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                >
                  <span>🛡️</span>
                  <span>Re-inject & Restore Primary {selectedFinding.agent}</span>
                </button>
              ) : <div />}
              <button
                onClick={() => setSelectedFinding(null)}
                className="px-4 py-1.5 bg-[#282828] hover:bg-[#333333] text-xs font-semibold text-white rounded-lg transition cursor-pointer"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
