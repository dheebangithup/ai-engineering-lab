import React, { useState, useEffect, useRef } from 'react';
import { fetchGraph } from '../api';
import { Layers, RefreshCw, ZoomIn, ZoomOut, CheckCircle, XCircle, Info } from 'lucide-react';

const TYPE_COLORS = {
  person: '#6366f1', // Indigo
  technology: '#06b6d4', // Cyan
  architecture: '#10b981', // Emerald
  location: '#f59e0b', // Amber
  concept: '#a855f7', // Purple
  default: '#3b82f6' // Blue
};

export default function EntityGraphView({ namespace }) {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [includeInvalidated, setIncludeInvalidated] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodePositions, setNodePositions] = useState({});
  const [draggingNode, setDraggingNode] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  useEffect(() => {
    loadGraph();
  }, [namespace, includeInvalidated]);

  const loadGraph = async () => {
    setLoading(true);
    const data = await fetchGraph(namespace, includeInvalidated);
    setGraph(data);

    // Initial radial/grid layout
    const initialPos = {};
    const count = data.nodes.length;
    const centerX = 360;
    const centerY = 260;
    const radius = Math.min(centerX, centerY) - 80;

    data.nodes.forEach((node, i) => {
      const angle = (i / Math.max(1, count)) * 2 * Math.PI;
      initialPos[node.id] = {
        x: centerX + radius * Math.cos(angle) + (Math.random() * 20 - 10),
        y: centerY + radius * Math.sin(angle) + (Math.random() * 20 - 10),
      };
    });
    setNodePositions(initialPos);
    if (data.nodes.length > 0 && !selectedNode) {
      setSelectedNode(data.nodes[0]);
    }
    setLoading(false);
  };

  const handleMouseDown = (e, nodeId) => {
    e.stopPropagation();
    const pos = nodePositions[nodeId] || { x: 0, y: 0 };
    setDraggingNode(nodeId);
    setDragOffset({
      x: e.clientX - pos.x,
      y: e.clientY - pos.y,
    });
  };

  const handleMouseMove = (e) => {
    if (!draggingNode) return;
    const svgRect = svgRef.current.getBoundingClientRect();
    const newX = Math.max(30, Math.min(svgRect.width - 30, e.clientX - dragOffset.x));
    const newY = Math.max(30, Math.min(svgRect.height - 30, e.clientY - dragOffset.y));

    setNodePositions((prev) => ({
      ...prev,
      [draggingNode]: { x: newX, y: newY },
    }));
  };

  const handleMouseUp = () => {
    setDraggingNode(null);
  };

  const selectedConnectedEdges = selectedNode
    ? graph.edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
    : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Interactive SVG Canvas */}
      <div className="lg:col-span-3 bg-card rounded-2xl border border-card-border overflow-hidden flex flex-col h-[640px] relative shadow-lg">
        {/* Graph Header Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-card-border bg-card/80 backdrop-blur z-10">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Bi-Temporal Entity Graph</span>
            <span className="text-[10px] text-slate-500">({graph.nodes.length} Nodes • {graph.edges.length} Edges)</span>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
              <input
                type="checkbox"
                checked={includeInvalidated}
                onChange={(e) => setIncludeInvalidated(e.target.checked)}
                className="rounded border-card-border accent-primary cursor-pointer"
              />
              <span className="text-[11px]">Show Invalidated Edges</span>
            </label>

            <button
              onClick={loadGraph}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-card-border transition-all"
              title="Reset View"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* SVG Drawing Canvas */}
        <div
          className="relative flex-1 bg-[radial-gradient(ellipse_at_center,_#1e293b_1px,_transparent_1px)] bg-[size:24px_24px] overflow-hidden select-none"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          {loading ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">Loading graph...</div>
          ) : (
            <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing">
              <defs>
                <marker id="arrow-active" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#6366f1" />
                </marker>
                <marker id="arrow-invalidated" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#64748b" />
                </marker>
              </defs>

              {/* Render Edges */}
              {graph.edges.map((edge) => {
                const sPos = nodePositions[edge.source];
                const tPos = nodePositions[edge.target];
                if (!sPos || !tPos) return null;

                const isConnectedToSelected = selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id);
                const strokeColor = edge.is_active ? (isConnectedToSelected ? '#818cf8' : '#6366f1') : '#475569';
                const strokeWidth = isConnectedToSelected ? 2.5 : 1.5;

                return (
                  <g key={edge.id}>
                    <line
                      x1={sPos.x}
                      y1={sPos.y}
                      x2={tPos.x}
                      y2={tPos.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeOpacity={edge.is_active ? 0.85 : 0.4}
                      strokeDasharray={edge.is_active ? undefined : '4,4'}
                      markerEnd={edge.is_active ? 'url(#arrow-active)' : 'url(#arrow-invalidated)'}
                    />
                    <text
                      x={(sPos.x + tPos.x) / 2}
                      y={(sPos.y + tPos.y) / 2 - 6}
                      fill={edge.is_active ? '#a5b4fc' : '#64748b'}
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="pointer-events-none select-none font-bold"
                    >
                      {edge.relation}
                    </text>
                  </g>
                );
              })}

              {/* Render Nodes */}
              {graph.nodes.map((node) => {
                const pos = nodePositions[node.id] || { x: 300, y: 300 };
                const isSelected = selectedNode && selectedNode.id === node.id;
                const nodeColor = TYPE_COLORS[node.entity_type?.toLowerCase()] || TYPE_COLORS.default;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x},${pos.y})`}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleMouseDown(e, node.id)}
                    onClick={() => setSelectedNode(node)}
                  >
                    <circle
                      r="16"
                      fill={nodeColor}
                      stroke={isSelected ? '#ffffff' : '#0f172a'}
                      strokeWidth={isSelected ? 3 : 2}
                      className="transition-all duration-150"
                      filter="drop-shadow(0 4px 6px rgba(0,0,0,0.4))"
                    />
                    <text
                      y="26"
                      textAnchor="middle"
                      fill={isSelected ? '#ffffff' : '#cbd5e1'}
                      fontSize="10"
                      fontWeight="600"
                      className="pointer-events-none select-none"
                    >
                      {node.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          {/* Legend */}
          <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-card-border p-2.5 rounded-xl text-[10px] space-y-1 shadow-md">
            <div className="font-semibold text-slate-300 mb-1">Entity Categories</div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span> Person</div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-500"></span> Technology</div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Architecture</div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Location</div>
            <div className="pt-1 mt-1 border-t border-card-border text-[9px] text-slate-500">
              Solid = Active • Dashed = Invalidated
            </div>
          </div>
        </div>
      </div>

      {/* Node Inspector Side Pane */}
      <div className="bg-card rounded-2xl border border-card-border p-5 flex flex-col justify-between h-[640px] shadow-lg">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Entity Details</h2>
            {selectedNode && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {selectedNode.entity_type || 'Entity'}
              </span>
            )}
          </div>

          {!selectedNode ? (
            <div className="text-center py-20 text-slate-500 text-xs">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              Click any node in the graph to inspect its summary, attributes, and connected edges.
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <div className="text-lg font-bold text-white">{selectedNode.name}</div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">ID: {selectedNode.id}</div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Summary</div>
                <p className="text-xs mt-1 text-slate-200 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-card-border">
                  {selectedNode.summary || 'No summary available.'}
                </p>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Connected Relationships ({selectedConnectedEdges.length})</div>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1 text-xs">
                  {selectedConnectedEdges.length === 0 ? (
                    <div className="text-slate-500 text-xs">No direct edges found.</div>
                  ) : (
                    selectedConnectedEdges.map((edge) => {
                      const isSource = edge.source === selectedNode.id;
                      const otherId = isSource ? edge.target : edge.source;
                      const otherNode = graph.nodes.find((n) => n.id === otherId);

                      return (
                        <div key={edge.id} className="bg-slate-900/70 p-2.5 rounded-xl border border-card-border">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-indigo-400 font-bold text-[11px]">
                              {isSource ? `→ ${edge.relation}` : `← ${edge.relation}`}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase ${
                                edge.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                              }`}
                            >
                              {edge.is_active ? 'Active' : 'Invalidated'}
                            </span>
                          </div>
                          <div className="font-semibold text-slate-200 text-xs">{otherNode ? otherNode.name : otherId}</div>
                          {edge.fact && <div className="text-[10px] text-slate-400 mt-1 leading-snug">{edge.fact}</div>}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="pt-3 border-t border-card-border text-[11px] text-slate-500 text-center">
          Bi-temporal tracking in Neon Postgres
        </div>
      </div>
    </div>
  );
}
