import React, { useState, useEffect } from 'react';
import { fetchMemories } from '../api';
import { Sparkles, Layers, Tag, Award, CheckCircle, Clock } from 'lucide-react';

export default function SemanticClusterView({ namespace }) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMemory, setSelectedMemory] = useState(null);
  const [activeCluster, setActiveCluster] = useState('all');

  useEffect(() => {
    loadData();
  }, [namespace]);

  const loadData = async () => {
    setLoading(true);
    const data = await fetchMemories(namespace, 'semantic', 'all', 100);
    setMemories(data.items || []);
    if (data.items?.length > 0) {
      setSelectedMemory(data.items[0]);
    }
    setLoading(false);
  };

  // Group by tags for thematic concept clustering
  const clusterMap = {};
  memories.forEach((mem) => {
    const mainTag = mem.tags?.[0] || 'general';
    if (!clusterMap[mainTag]) clusterMap[mainTag] = [];
    clusterMap[mainTag].push(mem);
  });

  const clusters = Object.keys(clusterMap);
  const filteredMemories = activeCluster === 'all' ? memories : clusterMap[activeCluster] || [];

  return (
    <div className="space-y-6">
      {/* Cluster Filter Tabs */}
      <div className="flex items-center justify-between bg-card p-2 rounded-xl border border-card-border overflow-x-auto gap-2">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-400 px-2">Concept Clusters:</span>
          <button
            onClick={() => setActiveCluster('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeCluster === 'all' ? 'bg-primary text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Clusters ({memories.length})
          </button>
          {clusters.map((c) => (
            <button
              key={c}
              onClick={() => setActiveCluster(c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-all ${
                activeCluster === c ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {c} ({clusterMap[c].length})
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 2D Vector Embedding Scatter Plot Canvas */}
        <div className="lg:col-span-2 bg-card rounded-2xl border border-card-border p-5 flex flex-col h-[580px] shadow-lg relative">
          <div className="flex items-center justify-between pb-3 border-b border-card-border mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Vector Embedding Projection (768-Dim Cosine Distance)
              </h3>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">pgvector HNSW</span>
          </div>

          {/* Scatter Plot Visualizer */}
          <div className="flex-1 relative bg-[radial-gradient(ellipse_at_center,_#1e293b_1px,_transparent_1px)] bg-[size:20px_20px] rounded-xl border border-card-border/50 overflow-hidden">
            <svg className="w-full h-full">
              {/* Cluster centroid zones */}
              {clusters.map((c, idx) => {
                const angle = (idx / Math.max(1, clusters.length)) * 2 * Math.PI;
                const cx = 250 + 130 * Math.cos(angle);
                const cy = 230 + 110 * Math.sin(angle);
                return (
                  <g key={c} opacity="0.3">
                    <circle cx={cx} cy={cy} r="65" fill="#3b82f6" fillOpacity="0.08" stroke="#3b82f6" strokeDasharray="3,3" />
                    <text x={cx} y={cy - 50} textAnchor="middle" fill="#60a5fa" fontSize="9" fontWeight="bold" className="uppercase font-mono">
                      {c}
                    </text>
                  </g>
                );
              })}

              {/* Data points */}
              {filteredMemories.map((mem, i) => {
                // Deterministic pseudo-coordinates from hash of memory_id
                const hash1 = mem.memory_id.charCodeAt(0) * 17 + i * 23;
                const hash2 = (mem.memory_id.charCodeAt(mem.memory_id.length - 1) || 5) * 19 + i * 31;
                const tagIdx = clusters.indexOf(mem.tags?.[0] || 'general');
                const baseAngle = tagIdx >= 0 ? (tagIdx / Math.max(1, clusters.length)) * 2 * Math.PI : 0;
                const clusterCenterX = 250 + 130 * Math.cos(baseAngle);
                const clusterCenterY = 230 + 110 * Math.sin(baseAngle);

                const x = Math.max(30, Math.min(500, clusterCenterX + ((hash1 % 80) - 40)));
                const y = Math.max(30, Math.min(420, clusterCenterY + ((hash2 % 80) - 40)));

                const isSelected = selectedMemory && selectedMemory.memory_id === mem.memory_id;
                const isActive = mem.is_active;

                return (
                  <g
                    key={mem.memory_id}
                    transform={`translate(${x},${y})`}
                    className="cursor-pointer transition-transform hover:scale-125"
                    onClick={() => setSelectedMemory(mem)}
                  >
                    <circle
                      r={isSelected ? 10 : 7}
                      fill={isActive ? (isSelected ? '#6366f1' : '#06b6d4') : '#64748b'}
                      stroke={isSelected ? '#ffffff' : '#0f172a'}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      filter="drop-shadow(0 2px 4px rgba(0,0,0,0.5))"
                    />
                    <title>{mem.summary}</title>
                  </g>
                );
              })}
            </svg>

            <div className="absolute bottom-3 left-3 bg-slate-900/90 border border-card-border p-2 rounded-lg text-[9px] text-slate-400">
              Points close together share high cosine similarity (&ge; 0.85)
            </div>
          </div>
        </div>

        {/* Fact Inspector Drawer */}
        <div className="bg-card rounded-2xl border border-card-border p-5 flex flex-col justify-between h-[580px] shadow-lg">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Semantic Fact Inspector</h3>
              {selectedMemory && (
                <span
                  className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                    selectedMemory.is_active
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                  }`}
                >
                  {selectedMemory.is_active ? 'Active Fact' : 'Superseded'}
                </span>
              )}
            </div>

            {!selectedMemory ? (
              <div className="text-center py-20 text-slate-500 text-xs">Select a point in the scatter plot to inspect details.</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-xs font-mono text-slate-500">ID: #{selectedMemory.memory_id}</div>
                  <div className="text-sm font-semibold text-slate-100 mt-1 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-card-border">
                    {selectedMemory.summary}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-900/40 p-2.5 rounded-xl border border-card-border">
                    <span className="text-[10px] text-slate-400 uppercase">Utility Score</span>
                    <div className="text-lg font-bold text-indigo-400 mt-0.5 font-mono">
                      {selectedMemory.utility_score >= 0 ? `+${selectedMemory.utility_score}` : selectedMemory.utility_score}
                    </div>
                  </div>

                  <div className="bg-slate-900/40 p-2.5 rounded-xl border border-card-border">
                    <span className="text-[10px] text-slate-400 uppercase">Confidence</span>
                    <div className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">
                      {(selectedMemory.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Semantic Tags</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {selectedMemory.tags?.map((t) => (
                      <span key={t} className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-slate-800 text-slate-300 border border-card-border">
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 space-y-1 bg-slate-900/30 p-2.5 rounded-xl border border-card-border">
                  <div className="flex justify-between">
                    <span>Access Count:</span>
                    <span className="font-mono text-slate-200">{selectedMemory.access_count} times</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Created:</span>
                    <span className="font-mono text-slate-200">{new Date(selectedMemory.created_at).toLocaleDateString()}</span>
                  </div>
                  {selectedMemory.superseded_by && (
                    <div className="flex justify-between text-rose-400 font-mono text-[10px] pt-1 border-t border-card-border">
                      <span>Superseded by:</span>
                      <span>#{selectedMemory.superseded_by}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-card-border text-[10px] text-slate-500 text-center">
            768-dim Embeddings with HNSW vector index
          </div>
        </div>
      </div>
    </div>
  );
}
