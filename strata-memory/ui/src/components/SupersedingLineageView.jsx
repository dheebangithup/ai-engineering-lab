import React, { useState } from 'react';
import { GitCommit, ArrowRight, ShieldAlert, Sparkles, CheckCircle2, History } from 'lucide-react';

const SAMPLE_CHAINS = {
  database_architecture: [
    {
      id: "mem-001a",
      version: "v1.0",
      summary: "User prefers Local SQLite for vector storage and rapid prototyping.",
      tags: ["database", "sqlite", "prototype"],
      created: "Nov 12, 2026",
      status: "superseded",
      superseded_by: "mem-002b",
      valid_until: "Nov 20, 2026",
      confidence: 0.95,
      utility: 2,
    },
    {
      id: "mem-002b",
      version: "v2.0",
      summary: "User migrated from SQLite to Neon Serverless Postgres with pgvector extension.",
      tags: ["database", "postgres", "neon", "pgvector"],
      created: "Nov 20, 2026",
      status: "superseded",
      superseded_by: "mem-003c",
      valid_until: "Nov 26, 2026",
      confidence: 0.98,
      utility: 5,
    },
    {
      id: "mem-003c",
      version: "v3.0 (CURRENT)",
      summary: "User architecture uses Neon Serverless Postgres with scale-to-zero suspend and HNSW 768-dim embeddings.",
      tags: ["database", "neon", "scale-to-zero", "hnsw"],
      created: "Nov 26, 2026",
      status: "active",
      superseded_by: null,
      valid_until: null,
      confidence: 1.0,
      utility: 8,
    },
  ],
  python_framework: [
    {
      id: "mem-101",
      version: "v1.0",
      summary: "API backend built with Flask on Python 3.10.",
      tags: ["python", "flask", "backend"],
      created: "Oct 15, 2026",
      status: "superseded",
      superseded_by: "mem-102",
      valid_until: "Nov 05, 2026",
      confidence: 0.92,
      utility: 1,
    },
    {
      id: "mem-102",
      version: "v2.0 (CURRENT)",
      summary: "API backend refactored to high-performance FastAPI on Python 3.12 with asyncpg connection pooling.",
      tags: ["python", "fastapi", "asyncpg"],
      created: "Nov 05, 2026",
      status: "active",
      superseded_by: null,
      valid_until: null,
      confidence: 1.0,
      utility: 6,
    },
  ],
};

export default function SupersedingLineageView() {
  const [selectedChainKey, setSelectedChainKey] = useState('database_architecture');
  const chain = SAMPLE_CHAINS[selectedChainKey] || SAMPLE_CHAINS.database_architecture;

  return (
    <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-card-border gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            Memory Superseding & Temporal Lineage
          </h2>
          <p className="text-xs text-slate-400">
            Bi-temporal tracking: when facts contradict or evolve, Strata invalidates outdated facts and links them via <code className="text-indigo-300">superseded_by</code>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Select Fact Lineage:</span>
          <select
            value={selectedChainKey}
            onChange={(e) => setSelectedChainKey(e.target.value)}
            className="bg-slate-900 border border-card-border rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="database_architecture">Database & Vector Storage Evolution</option>
            <option value="python_framework">Python Runtime & Framework Migration</option>
          </select>
        </div>
      </div>

      {/* Visual Chain Timeline */}
      <div className="relative pl-6 border-l-2 border-indigo-500/40 ml-4 py-2 space-y-6">
        {chain.map((item, index) => {
          const isActive = item.status === 'active';

          return (
            <div key={item.id} className="relative group">
              {/* Timeline dot */}
              <div
                className={`absolute -left-[31px] top-4 w-4 h-4 rounded-full border-2 border-card flex items-center justify-center ${
                  isActive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                }`}
              ></div>

              <div
                className={`p-5 rounded-xl border transition-all ${
                  isActive
                    ? 'bg-indigo-950/20 border-indigo-500/40 shadow-lg shadow-indigo-500/5'
                    : 'bg-slate-900/60 border-card-border opacity-75'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2.5 border-b border-card-border gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs font-mono text-indigo-400">{item.version}</span>
                    <span className="font-mono text-[10px] text-slate-500">ID: #{item.id}</span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px]">
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        isActive
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                      }`}
                    >
                      {isActive ? 'CURRENT ACTIVE FACT' : 'SUPERSEDED'}
                    </span>
                    <span className="text-slate-400">
                      Utility: <strong className="text-white font-mono">{item.utility}</strong>
                    </span>
                  </div>
                </div>

                <div className="py-3">
                  <p className={`text-xs leading-relaxed ${isActive ? 'text-white font-medium' : 'text-slate-400 line-through'}`}>
                    {item.summary}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 pt-2.5 border-t border-card-border gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400">Tags:</span>
                    {item.tags.map((t) => (
                      <span key={t} className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                        #{t}
                      </span>
                    ))}
                  </div>

                  <div className="font-mono">
                    {isActive ? (
                      <span className="text-emerald-400">Valid: {item.created} &rarr; Forever (Until superseded)</span>
                    ) : (
                      <span className="text-slate-400">
                        Valid: {item.created} &rarr; Expired: {item.valid_until}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
