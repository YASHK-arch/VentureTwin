import React, { useState } from 'react';
import { EventItem, FindingItem, TaskItem } from '../../api';
import { useOrchestrationModel } from '../../orchestration/useOrchestrationModel';
import { PhaseStepper } from './PhaseStepper';
import { AgentRoster } from './AgentRoster';
import { OrchestrationGraph } from './OrchestrationGraph';
import { EventFeed } from '../EventFeed';
import { FailureInjector, StagedFault } from '../FailureInjectorModal';

export interface MissionControlProps {
  choreographedEvents: EventItem[];
  rawEvents: EventItem[];
  tasks: Record<string, TaskItem>;
  findings: FindingItem[];
  workflowStatus: string;
  playbackSpeed: 'cinematic' | 'instant';
  onTogglePlaybackSpeed: (speed: 'cinematic' | 'instant') => void;
  onSkipToReport: () => void;
  onOpenReport: () => void;
  onInspectFinding: (finding: FindingItem) => void;
  onInjectFault: (agent: string, mode: string, persist?: boolean, failAttempts?: number) => Promise<void> | void;
  stagedFault: StagedFault | null;
  onSetStagedFault: (fault: StagedFault | null) => void;
  model?: ReturnType<typeof useOrchestrationModel>;
}

export const MissionControl: React.FC<MissionControlProps> = ({
  choreographedEvents,
  rawEvents,
  tasks,
  findings,
  workflowStatus,
  playbackSpeed,
  onTogglePlaybackSpeed,
  onSkipToReport,
  onOpenReport,
  onInspectFinding,
  onInjectFault,
  stagedFault,
  onSetStagedFault,
  model: externalModel
}) => {
  const [controlTab, setControlTab] = useState<'chaos' | 'telemetry'>('chaos');
  const [isSplitView, setIsSplitView] = useState(false);

  // Derive model state if not provided externally
  const internalModel = useOrchestrationModel(choreographedEvents, tasks, findings, workflowStatus);
  const model = externalModel || internalModel;

  const isIdle = workflowStatus === 'idle';
  const isComplete = workflowStatus === 'completed' || workflowStatus === 'degraded';

  const handleInspectAgent = (agentId: string) => {
    const finding = findings.find((f) => (f.agent || '').toLowerCase() === agentId.toLowerCase());
    if (finding) {
      onInspectFinding(finding);
    }
  };

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* 1. Top Phase Stepper & Live Narration Ticker */}
      <PhaseStepper
        currentPhase={model.phase}
        narration={model.narration}
        activeAgentsCount={model.activeAgentsCount}
        playbackSpeed={playbackSpeed}
        onTogglePlaybackSpeed={onTogglePlaybackSpeed}
        onSkipToReport={onSkipToReport}
        isComplete={isComplete}
      />

      {/* 2. Primary Canvas: 11-Node Orchestration DAG Execution Blueprint */}
      <div className="w-full h-[380px] xl:h-[400px]">
        <OrchestrationGraph
          tasks={tasks}
          findings={findings}
          nodeStatusOverrides={model.nodeStatusOverrides}
          completedNodeIds={model.completedNodeIds}
          activePackets={model.activePackets}
          onSelectFinding={onInspectFinding}
          isIdleStandby={isIdle}
        />
      </div>

      {/* 3. Bottom Row: Agent Roster (Left) + Chaos Fault Injector & Event Telemetry (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[420px]">
        {/* Left Column: Agent Roster */}
        <div className="lg:col-span-5 xl:col-span-4 h-[420px]">
          <AgentRoster
            agentStates={model.agentStates}
            showBackup={model.showBackup}
            backupState={model.backupState}
            onInspectAgent={handleInspectAgent}
          />
        </div>

        {/* Right Column: Chaos Engine & Live Telemetry Stream */}
        <div className="lg:col-span-7 xl:col-span-8 h-[420px] flex flex-col bg-[#181818] border border-[#282828] rounded-2xl overflow-hidden shadow-xl">
          {/* Header Bar with Mode Switcher & Armed Status */}
          <div className="px-4 py-2.5 bg-[#141414] border-b border-[#282828] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setControlTab('chaos')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition cursor-pointer ${
                  controlTab === 'chaos' && !isSplitView
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold'
                    : 'text-[#888888] hover:text-white'
                }`}
              >
                <span>⚡ Live Fault Injection</span>
                {stagedFault && (
                  <span className="w-2 h-2 rounded-full bg-rose-400 animate-ping" />
                )}
              </button>

              <button
                onClick={() => setControlTab('telemetry')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition cursor-pointer ${
                  controlTab === 'telemetry' && !isSplitView
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold'
                    : 'text-[#888888] hover:text-white'
                }`}
              >
                <span>📟 Live Event Stream</span>
                <span className="text-[10px] bg-[#222222] px-1.5 py-0.2 rounded text-[#aaaaaa] font-bold">
                  {rawEvents.length}
                </span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              {stagedFault && (
                <span className="text-[9px] font-mono text-rose-300 bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 rounded-full font-bold uppercase animate-pulse">
                  Armed: {stagedFault.agent}
                </span>
              )}
              <button
                onClick={() => setIsSplitView(!isSplitView)}
                className={`text-[10px] font-mono px-2 py-1 rounded border transition cursor-pointer ${
                  isSplitView
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 font-bold'
                    : 'bg-[#1e1e1e] text-[#888888] border-[#2e2e2e] hover:text-[#cccccc]'
                }`}
                title="Toggle split view to show Fault Injection and Event Telemetry simultaneously"
              >
                {isSplitView ? 'Tab View' : 'Split View'}
              </button>
            </div>
          </div>

          {/* Content Pane: Split view (both stacked) or Tabbed view */}
          {isSplitView ? (
            <div className="flex-1 flex flex-col overflow-y-auto divide-y divide-[#282828] scrollbar-thin scrollbar-thumb-[#2c2c2c]">
              <div className="p-3 bg-[#181818]">
                <FailureInjector
                  onInject={onInjectFault}
                  stagedFault={stagedFault}
                  onSetStagedFault={onSetStagedFault}
                  workflowStatus={workflowStatus}
                />
              </div>
              <div className="p-3 bg-[#141414] flex-1 min-h-[220px]">
                <EventFeed events={rawEvents} />
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-[#2c2c2c] bg-[#161616]">
              {controlTab === 'chaos' ? (
                <FailureInjector
                  onInject={onInjectFault}
                  stagedFault={stagedFault}
                  onSetStagedFault={onSetStagedFault}
                  workflowStatus={workflowStatus}
                />
              ) : (
                <EventFeed events={rawEvents} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
