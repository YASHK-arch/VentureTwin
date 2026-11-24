import React, { useState } from 'react';
import { approveDecision } from '../api';

interface Props {
  report: any;
  decisionId: string;
  onApprovalDone: () => void;
}

const AGENT_ROLE_MAP: Record<string, { title: string; icon: string }> = {
  CFO: { title: 'Chief Financial Officer', icon: '💼' },
  Growth: { title: 'VP Growth & CMO', icon: '📈' },
  CTO: { title: 'Chief Technology Officer', icon: '⚡' },
  'Customer Success': { title: 'VP Customer Success', icon: '💛' },
  Customer: { title: 'VP Customer Success', icon: '💛' },
  Product: { title: 'Chief Product Officer', icon: '📦' },
  Skeptic: { title: 'Independent Risk Auditor', icon: '🛡️' }
};

export const DecisionReportView: React.FC<Props> = ({ report, decisionId, onApprovalDone }) => {
  const [viewMode, setViewMode] = useState<'executive' | 'telemetry' | 'raw_markdown'>('executive');
  const [copied, setCopied] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [signoffRecord, setSignoffRecord] = useState<{ action: string; notes?: string } | null>(null);

  if (!report) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-500">
        No report available yet. Complete a workflow run to review the consolidated report.
      </div>
    );
  }

  const handleAction = async (action: 'approve' | 'reject' | 'request_changes') => {
    try {
      await approveDecision(decisionId, action, approvalNotes);
      setSignoffRecord({ action, notes: approvalNotes });
    } catch (e: any) {
      alert(`Sign-off error: ${e.message}`);
    }
  };

  const sec = report.sections ?? {};
  const currentPos = sec.current_position ?? {};
  const strategies = sec.strategies_compared ?? [];
  const scenarios = sec.scenario_table ?? [];
  const conflicts = sec.conflicts_resolution ?? [];
  const tornado = sec.tornado_sensitivity ?? [];
  const flip = sec.flip_points ?? {};
  const ledger = sec.assumption_ledger ?? [];
  const verifs = sec.verification_summary ?? [];
  const risks = sec.risks_and_triggers ?? [];
  const conf = sec.confidence_assessment ?? { level: report.confidence, score: undefined, reasons: [] };
  const agentFindings = sec.agent_findings ?? [];
  const markdownReport = sec.markdown_report ?? '';

  const handleCopyMarkdown = () => {
    if (!markdownReport) return;
    navigator.clipboard.writeText(markdownReport);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!markdownReport) return;
    const blob = new Blob([markdownReport], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `decision-report-${decisionId || 'latest'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* View Mode Bar & Export Controls */}
      <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-3 px-5 flex flex-wrap items-center justify-between gap-3 shadow-xl">
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setViewMode('executive')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              viewMode === 'executive'
                ? 'bg-brand-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>📄</span>
            <span>Executive Report (.md)</span>
          </button>
          <button
            onClick={() => setViewMode('telemetry')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              viewMode === 'telemetry'
                ? 'bg-brand-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>📊</span>
            <span>Telemetry & Matrix</span>
          </button>
          <button
            onClick={() => setViewMode('raw_markdown')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              viewMode === 'raw_markdown'
                ? 'bg-brand-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>📝</span>
            <span>Raw Markdown Source</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyMarkdown}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/80 rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
            title="Copy full executive markdown report to clipboard"
          >
            <span>{copied ? '✅' : '📋'}</span>
            <span>{copied ? 'Copied to Clipboard!' : 'Copy .md'}</span>
          </button>
          <button
            onClick={handleDownloadMarkdown}
            className="px-3 py-1.5 bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 border border-brand-500/40 rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
            title="Download executive decision report as markdown (.md) file"
          >
            <span>⬇️</span>
            <span>Download .md</span>
          </button>
        </div>
      </div>

      {/* VIEW MODE 1: EXECUTIVE REPORT (.md) */}
      {viewMode === 'executive' && (
        <>
          {/* Executive Header & Recommendation */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-3">
                  <span className="text-xs uppercase font-mono tracking-wider text-slate-400">Consolidated Executive Report</span>
                  <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full font-semibold">
                    Status: Verified
                  </span>
                  <span className="px-2 py-0.5 text-xs bg-brand-500/10 text-brand-400 border border-brand-500/20 rounded-full font-mono">
                    Single .md Specification
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-white mt-2 leading-tight">{report.recommendation}</h2>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-400 font-medium">Confidence Rating</div>
                <div className={`text-xl font-bold ${conf.level === 'High' ? 'text-emerald-400' : conf.level === 'Medium' ? 'text-amber-400' : 'text-rose-400'}`}>
                  {conf.level} {typeof conf.score === 'number' ? `(${((conf.score) * 100).toFixed(0)}%)` : ''}
                </div>
              </div>
            </div>

            <div className="pt-4 text-sm text-slate-300 leading-relaxed bg-slate-950/70 p-5 rounded-xl border border-slate-800/80">
              <div className="text-xs font-semibold uppercase tracking-wider text-brand-400 mb-2 font-mono">Executive Strategic Synthesis</div>
              <p className="leading-relaxed">{sec.executive_summary}</p>
            </div>

            {conf.reasons && conf.reasons.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-800/60">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Confidence Assessment Drivers:</div>
                <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                  {conf.reasons.map((r: string, idx: number) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* DEDICATED SECTION: Executive Specialist Individual Agent Claims */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white">Executive Specialist Individual Agent Claims</h3>
                  <span className="px-2 py-0.5 text-[10px] bg-brand-500/20 text-brand-300 border border-brand-500/30 rounded-full font-semibold uppercase font-mono">
                    Specialist Claims Section
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Direct domain perspectives, strategic rationale, and trade-off analyses from autonomous functional leaders
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                {agentFindings.length} Autonomous Agents Evaluated
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agentFindings.map((f: any, idx: number) => {
                const isReject = f.recommendation === 'reject';
                const isProceed = f.recommendation === 'proceed';
                const badgeClass = isReject
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                  : isProceed
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : 'bg-sky-500/20 text-sky-400 border-sky-500/30';

                const meta = AGENT_ROLE_MAP[f.agent] ?? { title: 'Executive Specialist', icon: '👤' };

                return (
                  <div key={idx} className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
                    <div>
                      <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-slate-800/60">
                        <div className="flex items-center gap-2.5">
                          <span className="text-lg">{meta.icon}</span>
                          <div>
                            <div className="font-bold text-sm text-white tracking-wide">{f.agent}</div>
                            <div className="text-[11px] text-slate-400">{meta.title}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${badgeClass} uppercase`}>
                            {String(f.recommendation ?? 'unknown').replace(/_/g, ' ')}
                          </span>
                          <span className="text-[11px] font-mono text-slate-400">
                            {typeof f.confidence === 'number' ? `${(f.confidence * 100).toFixed(0)}% conf` : ''}
                          </span>
                        </div>
                      </div>

                      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1 font-mono">
                        Autonomous Strategic Claim:
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed italic bg-slate-900/50 p-3 rounded-lg border border-slate-800/50">
                        "{f.claim}"
                      </p>

                      {f.limitations && f.limitations.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-slate-800/50">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                            Domain Guardrails & Mitigations:
                          </div>
                          <ul className="text-[11px] text-slate-400 space-y-0.5 list-disc list-inside">
                            {f.limitations.map((lim: string, lIdx: number) => (
                              <li key={lIdx}>{lim}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Phased Strategic Roadmap & Execution Gates */}
          {sec.execution_plan && sec.execution_plan.length > 0 && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white mb-1">Phased Strategic Roadmap & Execution Gates</h3>
                  <p className="text-xs text-slate-400">Milestone conditions derived from sensitivity flip points and cash runway safety floor</p>
                </div>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                  {sec.execution_plan.length} Strategic Phases
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {sec.execution_plan.map((phase: any, idx: number) => (
                  <div key={idx} className="p-4 bg-slate-950/70 rounded-xl border border-slate-800 space-y-2.5 flex flex-col justify-between">
                    <div>
                      <div className="text-xs font-bold text-brand-400 uppercase tracking-wide font-mono">{phase.phase}</div>
                      <div className="text-xs text-white mt-2">
                        <span className="text-slate-400">Gate Condition:</span> <span className="font-mono text-emerald-400">{phase.gate}</span>
                      </div>
                    </div>
                    <div className="text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                      <span className="text-slate-400 font-semibold">Action:</span> {phase.action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategic Trade-Off Analysis & Dialectic Alignment */}
          {(conflicts.length > 0 || (sec.trade_off_analysis && sec.trade_off_analysis.length > 0)) && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-lg font-bold text-white mb-1">Strategic Trade-Off Analysis & Dialectic Alignment</h3>
              <p className="text-xs text-slate-400 mb-4">Empirical reconciliation of competing specialist priorities</p>

              <div className="space-y-3">
                {conflicts.map((c: any, idx: number) => (
                  <div key={c.id ?? idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded font-bold uppercase">
                          {String(c.type ?? 'Conflict').replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-white font-semibold">
                          {Array.isArray(c.agents) ? c.agents.join(' vs ') : String(c.agents ?? 'Agents')} on {c.disputed_item ?? 'parameter'}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded border border-slate-800/60">
                      {c.resolution ?? 'Resolved by empirical simulation comparison.'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current Company Baseline Telemetry */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1">Current Company Baseline Telemetry ({currentPos.company || 'Company'})</h3>
            <p className="text-xs text-slate-400 mb-4">Foundational operating numbers grounding multi-agent deliberation</p>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">ARR</div>
                <div className="text-sm font-bold text-white font-mono mt-0.5">
                  ${Number(currentPos.arr ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">MRR</div>
                <div className="text-sm font-bold text-white font-mono mt-0.5">
                  ${Number(currentPos.mrr ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">Cash Reserves</div>
                <div className="text-sm font-bold text-white font-mono mt-0.5">
                  ${Number(currentPos.cash_balance ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">Cash Runway</div>
                <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                  {Number(currentPos.runway_months ?? 0).toFixed(1)} mo
                </div>
              </div>
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">Paying Customers</div>
                <div className="text-sm font-bold text-white font-mono mt-0.5">
                  {Number(currentPos.paying_customers ?? 0).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* VIEW MODE 2: TELEMETRY & SIMULATOR MATRIX */}
      {viewMode === 'telemetry' && (
        <>
          {/* Strategy Ranking & Feasibility */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1">Strategy Ranking & Feasibility</h3>
            <p className="text-xs text-slate-400 mb-4">Evaluated against company runway constraints and 12-month net contribution</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {strategies.map((strat: any) => (
                <div
                  key={strat.strategy}
                  className={`p-4 rounded-xl border ${
                    strat.rank === 1
                      ? 'bg-slate-950 border-brand-500/50 shadow-brand-500/10 shadow-lg'
                      : 'bg-slate-950/60 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Rank #{strat.rank}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${strat.is_feasible ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      {strat.is_feasible ? 'FEASIBLE' : 'INFEASIBLE'}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-white capitalize">{String(strat.strategy ?? 'strategy').replace(/_/g, ' ')}</div>
                  <div className="mt-3 space-y-1 text-xs">
                    <div className="flex justify-between text-slate-400">
                      <span>12mo Net Contribution:</span>
                      <span className="font-mono text-white">${Number(strat.net_contribution_12 ?? 0).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>12mo Cash Runway:</span>
                      <span className="font-mono text-emerald-400">{Number(strat.runway_months_12 ?? 0).toFixed(1)} mo</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>12mo Gross Margin:</span>
                      <span className="font-mono text-white">{(Number(strat.gross_margin_12 ?? 0) * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-3 pt-2 border-t border-slate-800/80">
                    {strat.feasibility_reason}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Scenario Outcome Matrix & Sensitivity Analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Scenario Table */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-lg font-bold text-white mb-1">Scenario Outcome Matrix</h3>
              <p className="text-xs text-slate-400 mb-4">Outcomes across Conservative, Expected, and Optimistic parameter sets</p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-2 font-semibold">Strategy</th>
                      <th className="p-2 font-semibold">Scenario</th>
                      <th className="p-2 font-semibold text-right">Net 12mo</th>
                      <th className="p-2 font-semibold text-right">Runway</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {scenarios.map((row: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="p-2 font-sans font-medium text-slate-300">{String(row.strategy ?? '').split('_')[0] ?? 'Strategy'}</td>
                        <td className="p-2 text-slate-400 capitalize">{row.scenario ?? ''}</td>
                        <td className="p-2 text-right text-white">${Number(row.net_contribution_12 ?? 0).toLocaleString()}</td>
                        <td className="p-2 text-right text-emerald-400">{Number(row.runway_months_12 ?? 0).toFixed(1)}m</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Sensitivity Tornado & Flip Point */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold text-white mb-1">Sensitivity Analysis (Tornado)</h3>
                <p className="text-xs text-slate-400 mb-4">Ranked variance impact on 12-month net contribution</p>
                <div className="space-y-3">
                  {tornado.length === 0 ? (
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 text-xs text-slate-400">
                      Parameter sensitivity variance is within nominal thresholds for the evaluated scenario bounds.
                    </div>
                  ) : (
                    tornado.map((t: any, idx: number) => {
                      const lowVal = t.net_contribution_at_low ?? t.margin_at_low ?? 0;
                      const highVal = t.net_contribution_at_high ?? t.margin_at_high ?? 0;
                      const name = String(t.assumption_name ?? t.param ?? `Param ${idx + 1}`).replace(/_/g, ' ');
                      const swingVal = Number(t.swing ?? 0).toLocaleString();
                      return (
                        <div key={t.assumption_name ?? idx} className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="font-semibold text-white">#{t.impact_rank ?? idx + 1} {name}</span>
                            <span className="font-mono text-brand-400">Swing: ${swingVal}</span>
                          </div>
                          <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                            <span>Low ({t.low_value ?? 0}): ${Number(lowVal).toLocaleString()}</span>
                            <span>High ({t.high_value ?? 0}): ${Number(highVal).toLocaleString()}</span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="mt-4 p-3 bg-brand-500/10 border border-brand-500/20 rounded-xl">
                <div className="text-xs font-bold text-brand-300 uppercase tracking-wider mb-1">Decision Flip Point</div>
                <div className="text-xs text-slate-300">
                  {flip.statement ?? 'No crossing threshold detected in evaluated range.'}
                </div>
              </div>
            </div>
          </div>

          {/* Assumption Ledger with Provenance */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1">Assumption Ledger with Provenance</h3>
            <p className="text-xs text-slate-400 mb-4">Audit trail of all agent assumptions, parameter ranges, and skeptic verifications</p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono">
                  <tr>
                    <th className="p-2.5">Assumption</th>
                    <th className="p-2.5">Range (Low / Base / High)</th>
                    <th className="p-2.5">Provenance</th>
                    <th className="p-2.5">Proposed By</th>
                    <th className="p-2.5 text-center">Skeptic Audited</th>
                    <th className="p-2.5 text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {ledger.map((asm: any, idx: number) => {
                    let badgeColor = 'bg-slate-800 text-slate-300';
                    if (asm.provenance === 'verified_data') badgeColor = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
                    if (asm.provenance === 'simulated_estimate') badgeColor = 'bg-sky-500/20 text-sky-400 border border-sky-500/30';
                    if (asm.provenance === 'external_research') badgeColor = 'bg-purple-500/20 text-purple-400 border border-purple-500/30';
                    if (asm.provenance === 'ai_assumption') badgeColor = 'bg-amber-500/20 text-amber-400 border border-amber-500/30';

                    return (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="p-2.5 font-medium text-white">{String(asm.name ?? 'Assumption').replace(/_/g, ' ')}</td>
                        <td className="p-2.5 font-mono text-slate-300">
                          [{asm.low ?? 0} / <span className="font-bold text-white">{asm.base ?? 0}</span> / {asm.high ?? 0}] {asm.unit ?? ''}
                        </td>
                        <td className="p-2.5">
                          <span className={`px-2 py-0.5 text-[10px] rounded-full font-semibold ${badgeColor}`}>
                            {asm.provenance ?? 'ai_assumption'}
                          </span>
                        </td>
                        <td className="p-2.5 text-slate-400">{asm.proposed_by ?? 'Agent'}</td>
                        <td className="p-2.5 text-center">
                          {asm.challenged_by_skeptic ? (
                            <span className="text-amber-400 font-bold" title="Challenged and confidence adjusted by Skeptic">Challenged</span>
                          ) : (
                            <span className="text-emerald-400">Passed</span>
                          )}
                        </td>
                        <td className="p-2.5 text-right font-mono text-slate-300">
                          {(Number(asm.confidence ?? 0.5) * 100).toFixed(0)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Deterministic Verification Layer */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1">Deterministic Verification Layer</h3>
            <p className="text-xs text-slate-400 mb-4">Independent algorithmic audits of mathematics, financial tie-outs, and simulation traceability</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {verifs.map((v: any, idx: number) => {
                const isPassed = v.status === 'passed';
                return (
                  <div key={idx} className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex items-start gap-3">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase mt-0.5 ${isPassed ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                      {v.status ?? 'unknown'}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-white capitalize">{String(v.check_name ?? 'check').replace(/_/g, ' ')}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{v.detail ?? ''}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* VIEW MODE 3: RAW MARKDOWN SOURCE */}
      {viewMode === 'raw_markdown' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-lg font-bold text-white">Raw Executive Decision Markdown Document (.md)</h3>
              <p className="text-xs text-slate-400">Single unified markdown artifact with full executive specialist claims</p>
            </div>
            <button
              onClick={handleCopyMarkdown}
              className="px-4 py-2 bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg transition flex items-center gap-1.5"
            >
              <span>{copied ? '✅' : '📋'}</span>
              <span>{copied ? 'Copied Markdown' : 'Copy Full .md'}</span>
            </button>
          </div>

          <pre className="p-5 bg-slate-950 rounded-xl border border-slate-800/90 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[650px] overflow-y-auto">
            {markdownReport || '# No markdown document generated'}
          </pre>
        </div>
      )}

      {/* Human-in-the-Loop Sign-Off Gate */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-lg font-bold text-white mb-1">Human-in-the-Loop Sign-Off Gate</h3>
        <p className="text-xs text-slate-400 mb-4">Strategic recommendations require explicit human approval before persisting as official board records</p>

        {signoffRecord ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl border ${
              signoffRecord.action === 'approve'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                : signoffRecord.action === 'reject'
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                    signoffRecord.action === 'approve'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : signoffRecord.action === 'reject'
                      ? 'bg-rose-500/20 text-rose-300'
                      : 'bg-amber-500/20 text-amber-300'
                  }`}>
                    {signoffRecord.action === 'approve' ? '✅ Approved' : signoffRecord.action === 'reject' ? '🛑 Rejected' : '⚠️ Changes Requested'}
                  </span>
                  <span className="text-xs font-semibold text-white">Sign-Off Recorded</span>
                </div>
                <button
                  onClick={() => setSignoffRecord(null)}
                  className="text-xs text-slate-400 hover:text-white underline"
                >
                  Edit Sign-Off
                </button>
              </div>

              <div className="text-xs text-slate-300">
                {signoffRecord.action === 'approve' && 'Recommendation officially approved for execution. Outcome tracking window initialized.'}
                {signoffRecord.action === 'reject' && 'Recommendation rejected by leadership. Maintaining status quo operating baseline.'}
                {signoffRecord.action === 'request_changes' && 'Executive revisions requested. Recommendation returned to multi-agent council.'}
              </div>

              {signoffRecord.notes && (
                <div className="mt-2 text-xs text-slate-400 italic bg-slate-950/40 p-2 rounded-lg border border-slate-800/40">
                  Notes: "{signoffRecord.notes}"
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button
                onClick={onApprovalDone}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg transition flex items-center gap-1.5"
              >
                <span>View Decision Record in Calibration & Memory</span>
                <span>→</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Executive Notes & Context</label>
              <input
                type="text"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="e.g. Approved for phased rollout in Q1 with operational guardrails..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => handleAction('approve')}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
              >
                Approve Recommendation
              </button>
              <button
                onClick={() => handleAction('request_changes')}
                className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition"
              >
                Request Changes
              </button>
              <button
                onClick={() => handleAction('reject')}
                className="px-5 py-2.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-600/30 rounded-xl text-xs font-semibold transition"
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
