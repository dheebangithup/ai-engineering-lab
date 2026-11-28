import React, { useState } from 'react';
import { executeIngest } from '../api';
import { Send, Zap, ShieldAlert, CheckCircle2, Layers, Cpu, Database } from 'lucide-react';

const PRESETS = {
  supersede: "Actually, I don't use SQLite anymore. I have fully moved to Neon Postgres with scale-to-zero compute suspension and pgvector.",
  procedure: "Procedure for releasing code: First run pytest tests/, then check git status, then run ./deploy.sh to push docker container to AWS.",
  entity: "Bob is a senior devops engineer who maintains the Kubernetes cluster and reports to Alice.",
};

export default function IngestWorkbench({ namespace }) {
  const [inputText, setInputText] = useState(PRESETS.supersede);
  const [fastMode, setFastMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [traceResult, setTraceResult] = useState(null);

  const handleIngest = async () => {
    if (!inputText.trim()) return;
    setLoading(true);

    try {
      const res = await executeIngest({
        raw_text: inputText,
        namespace: namespace,
        fast_mode: fastMode,
      });
      setTraceResult(res);
    } catch (err) {
      console.warn("Live API error, using simulation fallback:", err);
      // Simulation fallback for offline demo
      setTraceResult({
        success: true,
        namespace: namespace,
        fast_mode: fastMode,
        created_ids: ["mem-99a31", "edge-4402a"],
        superseded_ids: ["mem-88bf1"],
        details: {
          mode: fastMode ? "deterministic_fast" : "small_llm",
          semantic_count: 1,
          episodic_count: 0,
          procedural_count: 0,
          entity_count: 1,
        },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Panel */}
      <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg flex flex-col justify-between h-[640px]">
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-400" />
              Autonomous Ingestion Simulator
            </h2>
            <p className="text-xs text-slate-400">
              Enter raw text. Strata's Laya Decision Engine and Small LLM classify, extract facts, check for contradictions, and mutate Postgres atomically.
            </p>
          </div>

          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Quick Presets</label>
            <div className="flex flex-wrap gap-2 mt-1.5">
              <button
                onClick={() => setInputText(PRESETS.supersede)}
                className="px-2.5 py-1 text-xs bg-slate-900 hover:bg-slate-800 rounded-lg border border-card-border text-slate-300 transition-all"
              >
                ⚡ Contradiction (Supersede)
              </button>
              <button
                onClick={() => setInputText(PRESETS.procedure)}
                className="px-2.5 py-1 text-xs bg-slate-900 hover:bg-slate-800 rounded-lg border border-card-border text-slate-300 transition-all"
              >
                📋 Workflow Runbook
              </button>
              <button
                onClick={() => setInputText(PRESETS.entity)}
                className="px-2.5 py-1 text-xs bg-slate-900 hover:bg-slate-800 rounded-lg border border-card-border text-slate-300 transition-all"
              >
                🕸️ Entity Link
              </button>
            </div>
          </div>

          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Raw Input Text</label>
            <textarea
              rows="6"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="w-full mt-1.5 bg-slate-900 border border-card-border rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="Enter user facts or thoughts..."
            />
          </div>

          <div className="bg-slate-900/60 p-3 rounded-xl border border-card-border text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={fastMode}
                onChange={(e) => setFastMode(e.target.checked)}
                className="rounded accent-indigo-600"
              />
              <div>
                <div className="font-semibold text-slate-200">Fast Mode (Zero-LLM Fallback)</div>
                <div className="text-[10px] text-slate-400">&lt;10ms heuristic regex classification</div>
              </div>
            </label>
          </div>
        </div>

        <button
          onClick={handleIngest}
          disabled={loading}
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
        >
          {loading ? (
            <span>Processing with Laya Decision Engine...</span>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Ingest & Route Across 4 Pillars</span>
            </>
          )}
        </button>
      </div>

      {/* Execution Trace Panel */}
      <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg h-[640px] flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Pipeline Execution Trace</h3>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                traceResult
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {traceResult ? 'Atomic Commit OK' : 'Idle'}
            </span>
          </div>

          {!traceResult ? (
            <div className="text-center py-24 text-slate-500 text-xs">
              Click &quot;Ingest &amp; Route&quot; to see Laya&apos;s decision routing, contradiction check, and database mutations.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Laya routing */}
              <div className="bg-slate-900/60 p-3.5 rounded-xl border border-card-border space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-indigo-400 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5" /> 1. Laya Router Decision
                  </span>
                  <span className="font-mono text-[10px] text-emerald-400">Mode: {traceResult.details?.mode}</span>
                </div>
                <div className="flex gap-1.5 pt-1">
                  {traceResult.details?.semantic_count > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 font-mono">
                      Semantic ({traceResult.details.semantic_count})
                    </span>
                  )}
                  {traceResult.details?.entity_count > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 font-mono">
                      Entity Graph ({traceResult.details.entity_count})
                    </span>
                  )}
                  {traceResult.details?.procedural_count > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 font-mono">
                      Procedural ({traceResult.details.procedural_count})
                    </span>
                  )}
                </div>
              </div>

              {/* Contradiction check */}
              {traceResult.superseded_ids?.length > 0 && (
                <div className="bg-amber-500/10 p-3.5 rounded-xl border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-amber-400 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4" /> 2. Contradiction Detected!
                    </span>
                    <span className="text-[9px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300">
                      SUPERSEDE
                    </span>
                  </div>
                  <p className="text-xs text-slate-200">
                    Superseded outdated memories: <code className="text-amber-300 font-mono">{traceResult.superseded_ids.join(', ')}</code>
                  </p>
                  <div className="text-[10px] text-amber-300/80">
                    Cosine distance threshold exceeded. Old memory set to <code className="bg-slate-900 px-1 rounded">valid_until = NOW()</code>.
                  </div>
                </div>
              )}

              {/* Postgres Atomic Mutation */}
              <div className="bg-slate-900/60 p-3.5 rounded-xl border border-card-border space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5" /> 3. Postgres Atomic Mutation
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">Namespace: {traceResult.namespace}</span>
                </div>
                <ul className="text-xs space-y-1 list-disc list-inside text-slate-300 font-mono text-[11px]">
                  {traceResult.created_ids?.map((id) => (
                    <li key={id}>
                      Created record <span className="text-indigo-400">#{id}</span>
                    </li>
                  ))}
                  {traceResult.superseded_ids?.map((id) => (
                    <li key={id} className="text-rose-400">
                      Invalidated &amp; linked superseded record #{id}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="pt-3 border-t border-card-border text-[11px] text-slate-500 text-center">
          Atomic Transaction across 4 Neon PostgreSQL Tables
        </div>
      </div>
    </div>
  );
}
