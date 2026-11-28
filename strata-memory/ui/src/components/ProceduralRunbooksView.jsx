import React, { useState, useEffect } from 'react';
import { fetchProcedures, submitFeedback } from '../api';
import { BookOpen, GitBranch, ShieldCheck, AlertTriangle, Play, RefreshCw, CheckCircle2 } from 'lucide-react';

export default function ProceduralRunbooksView({ namespace }) {
  const [procedures, setProcedures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProc, setSelectedProc] = useState(null);
  const [failReason, setFailReason] = useState(
    'asyncpg prepared statement collision on -pooler endpoint. statement_cache_size must be 0.'
  );
  const [patching, setPatching] = useState(false);
  const [patchSuccessMsg, setPatchSuccessMsg] = useState(null);

  useEffect(() => {
    loadProcedures();
  }, [namespace]);

  const loadProcedures = async () => {
    setLoading(true);
    const data = await fetchProcedures(namespace);
    setProcedures(data);
    if (data.length > 0) {
      setSelectedProc(data[0]);
    }
    setLoading(false);
  };

  const handleSimulateFailureAndPatch = async () => {
    if (!selectedProc) return;
    setPatching(true);
    setPatchSuccessMsg(null);

    try {
      const res = await submitFeedback({
        procedure_name: selectedProc.name,
        success: false,
        failure_reason: failReason,
        namespace: namespace,
      });

      if (res.procedure_updated && res.patched_steps) {
        setSelectedProc((prev) => ({
          ...prev,
          version: prev.version + 1,
          steps: res.patched_steps,
          fail_count: prev.fail_count + 1,
          changelog: [
            ...(prev.changelog || []),
            {
              version: prev.version + 1,
              timestamp: new Date().toISOString(),
              reason: `Auto-patched after failure: ${failReason}`,
            },
          ],
        }));
        setPatchSuccessMsg(`Procedure successfully healed to v${selectedProc.version + 1} with patched steps!`);
      } else {
        // Mock fallback patch for local testing
        const newSteps = [
          ...selectedProc.steps.slice(0, 1),
          "Configure asyncpg connection pool with statement_cache_size=0 for Neon pooler",
          ...selectedProc.steps.slice(1),
        ];
        setSelectedProc((prev) => ({
          ...prev,
          version: prev.version + 1,
          steps: newSteps,
          fail_count: prev.fail_count + 1,
          changelog: [
            ...(prev.changelog || []),
            {
              version: prev.version + 1,
              timestamp: new Date().toISOString(),
              reason: `Auto-patched after failure: ${failReason}`,
            },
          ],
        }));
        setPatchSuccessMsg(`Procedure simulated self-patch to v${selectedProc.version + 1}!`);
      }
    } catch (err) {
      console.warn("Feedback API failed, applying local simulation:", err);
      const newSteps = [
        ...selectedProc.steps.slice(0, 1),
        "Configure asyncpg connection pool with statement_cache_size=0 for Neon pooler",
        ...selectedProc.steps.slice(1),
      ];
      setSelectedProc((prev) => ({
        ...prev,
        version: prev.version + 1,
        steps: newSteps,
        fail_count: prev.fail_count + 1,
        changelog: [
          ...(prev.changelog || []),
          {
            version: prev.version + 1,
            timestamp: new Date().toISOString(),
            reason: `Auto-patched after failure: ${failReason}`,
          },
        ],
      }));
      setPatchSuccessMsg(`Procedure simulated self-patch to v${selectedProc.version + 1}!`);
    } finally {
      setPatching(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Procedure List */}
      <div className="bg-card rounded-2xl border border-card-border p-5 space-y-4 shadow-lg h-[640px] flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-card-border">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Runbooks & Procedures</h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">{procedures.length} Active</span>
        </div>

        <div className="space-y-2 overflow-y-auto flex-1 pr-1">
          {procedures.map((proc) => {
            const isSelected = selectedProc && selectedProc.name === proc.name;
            return (
              <div
                key={proc.procedure_id}
                onClick={() => setSelectedProc(proc)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  isSelected ? 'bg-purple-950/20 border-purple-500/50 shadow-md' : 'bg-slate-900/60 border-card-border hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono font-bold text-xs text-white">{proc.name}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    v{proc.version}.0
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">{proc.description}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-card-border text-[10px] text-slate-500 font-mono">
                  <span>Success Rate: {(proc.success_rate * 100).toFixed(1)}%</span>
                  <span>{proc.success_count}S / {proc.fail_count}F</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Procedure Deep-Dive & Self-Healing Panel */}
      <div className="lg:col-span-2 bg-card rounded-2xl border border-card-border p-6 space-y-6 shadow-lg h-[640px] overflow-y-auto">
        {!selectedProc ? (
          <div className="text-center py-20 text-slate-500 text-xs">Select a procedure to view steps and testing tools.</div>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-card-border gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white font-mono">{selectedProc.name}</h2>
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30">
                    Version {selectedProc.version}.0
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{selectedProc.description}</p>
              </div>

              {/* Bayesian Success Rate Metric */}
              <div className="bg-slate-900/60 p-2.5 rounded-xl border border-card-border text-right min-w-[140px]">
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Bayesian Score</div>
                <div className="text-base font-bold text-emerald-400 font-mono">
                  {(selectedProc.success_rate * 100).toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-500 font-mono">{selectedProc.success_count} Pass • {selectedProc.fail_count} Fail</div>
              </div>
            </div>

            {/* Execution Steps */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">
                Current Execution Steps ({selectedProc.steps?.length || 0})
              </h3>
              <ol className="space-y-2">
                {selectedProc.steps?.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-3 bg-slate-900/60 p-3 rounded-xl border border-card-border text-xs">
                    <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center font-mono font-bold text-[11px] text-purple-400 shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-slate-200 font-mono leading-relaxed mt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Changelog & Evolution History */}
            {selectedProc.changelog?.length > 0 && (
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Evolution Changelog</h3>
                <div className="space-y-1.5">
                  {selectedProc.changelog.map((entry, i) => (
                    <div key={i} className="text-[11px] bg-slate-950/60 p-2.5 rounded-lg border border-card-border flex items-center justify-between font-mono">
                      <span className="text-purple-400 font-bold">v{entry.version}.0:</span>
                      <span className="text-slate-300 mx-2 flex-1">{entry.reason}</span>
                      <span className="text-slate-500 text-[10px]">{new Date(entry.timestamp).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Interactive Self-Healing Sandbox */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-rose-500/20 space-y-3">
              <div className="flex items-center gap-2 text-rose-400 text-xs font-bold uppercase tracking-wider">
                <AlertTriangle className="w-4 h-4" />
                Test Procedure Failure & Auto-Repair
              </div>
              <p className="text-xs text-slate-400">
                Simulate a terminal error or execution failure. Strata's Small LLM will analyze the error and patch the procedure steps automatically.
              </p>

              <div>
                <label className="text-[10px] font-semibold text-slate-400 uppercase">Simulated Failure Trace</label>
                <input
                  type="text"
                  value={failReason}
                  onChange={(e) => setFailReason(e.target.value)}
                  className="w-full mt-1 bg-slate-900 border border-card-border rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-rose-500"
                />
              </div>

              {patchSuccessMsg && (
                <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{patchSuccessMsg}</span>
                </div>
              )}

              <button
                onClick={handleSimulateFailureAndPatch}
                disabled={patching}
                className="w-full py-2.5 px-4 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                {patching ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing Error & Patching Steps with LLM...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Report Execution Failure & Trigger Auto-Repair</span>
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
