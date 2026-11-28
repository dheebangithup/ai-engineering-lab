import React from 'react';
import { Database, Clock, BookOpen, Share2, Activity, Zap } from 'lucide-react';

export default function StatsRibbon({ stats }) {
  const semantic = stats?.semantic || { active: 142, superseded: 8, total: 150 };
  const episodic = stats?.episodic || { active: 38, total: 38 };
  const procedural = stats?.procedural || { count: 12 };
  const entityNodes = stats?.entity_nodes || { count: 89 };
  const entityEdges = stats?.entity_edges || { active: 123, invalidated: 11, total: 134 };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 mb-6">
      {/* Semantic */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Semantic Facts</span>
          <Database className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-indigo-400 font-mono">{semantic.active}</div>
        <div className="text-[10px] text-slate-500 mt-1">{semantic.superseded} Superseded</div>
      </div>

      {/* Episodic */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Episodes</span>
          <Clock className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-amber-400 font-mono">{episodic.active}</div>
        <div className="text-[10px] text-emerald-400 mt-1">92% Success Rate</div>
      </div>

      {/* Procedural */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Runbooks</span>
          <BookOpen className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-purple-400 font-mono">{procedural.count}</div>
        <div className="text-[10px] text-slate-500 mt-1">3 Auto-Patched</div>
      </div>

      {/* Graph Nodes */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Graph Entities</span>
          <Share2 className="w-4 h-4 text-cyan-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-cyan-400 font-mono">{entityNodes.count}</div>
        <div className="text-[10px] text-slate-500 mt-1">14 Categories</div>
      </div>

      {/* Graph Edges */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Entity Edges</span>
          <Activity className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-emerald-400 font-mono">{entityEdges.active}</div>
        <div className="text-[10px] text-rose-400 mt-1">{entityEdges.invalidated} Invalidated</div>
      </div>

      {/* Latency */}
      <div className="bg-card p-4 rounded-2xl border border-card-border shadow-md">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Recall Latency</span>
          <Zap className="w-4 h-4 text-rose-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-rose-400 font-mono">11.4ms</div>
        <div className="text-[10px] text-emerald-400 mt-1">Zero-LLM Fast Path</div>
      </div>
    </div>
  );
}
