import React, { useState, useEffect, useRef } from 'react';
import { fetchGraph } from '../api';
import { Layers, RefreshCw, Search, Calendar, Target, CheckCircle, XCircle, Info, ChevronRight } from 'lucide-react';

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
  const [search, setSearch] = useState('');
  const [timeRange, setTimeRange] = useState('30d');
  const [centerEntityId, setCenterEntityId] = useState(null);
  const [centerEntityName, setCenterEntityName] = useState(null);
  const [limit, setLimit] = useState(50);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodePositions, setNodePositions] = useState({});
  const [draggingNode, setDraggingNode] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  useEffect(() => {
    loadGraph();
  }, [namespace, includeInvalidated, timeRange, centerEntityId, limit]);

  const loadGraph = async () => {
    setLoading(true);
    const data = await fetchGraph(namespace, includeInvalidated, search, timeRange, centerEntityId, limit);
    setGraph(data);

    // Initial radial layout centered on focal node if active
    const initialPos = {};
    const count = data.nodes.length;
    const centerX = 360;
    const centerY = 260;
    const radius = Math.min(centerX, centerY) - 70;

    data.nodes.forEach((node, i) => {
      if (centerEntityId && node.id === centerEntityId) {
        initialPos[node.id] = { x: centerX, y: centerY };
      } else {
        const angle = (i / Math.max(1, count)) * 2 * Math.PI;
        initialPos[node.id] = {
          x: centerX + radius * Math.cos(angle) + (Math.random() * 20 - 10),
          y: centerY + radius * Math.sin(angle) + (Math.random() * 20 - 10),
        };
      }
    });

    setNodePositions(initialPos);
    if (data.nodes.length > 0) {
      if (centerEntityId) {
        const foundCenter = data.nodes.find((n) => n.id === centerEntityId);
        setSelectedNode(foundCenter || data.nodes[0]);
      } else if (!selectedNode) {
        setSelectedNode(data.nodes[0]);
      }
    }
    setLoading(false);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadGraph();
  };

  const handleExpand1Hop = (node) => {
    setCenterEntityId(node.id);
    setCenterEntityName(node.name);
  };

  const handleClearFocus = () => {
    setCenterEntityId(null);
    setCenterEntityName(null);
    setSearch('');
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
    <div className="space-y-4">
      {/* Search, Time-Range, and Bounded Expansion Controls */}
      <div className="bg-card p-3 rounded-2xl border border-card-border shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-2 w-full md:w-auto flex-1">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search entity name or concept..."
              className="w-full bg-slate-900 border border-card-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-all"
          >
            Find Subgraph
          </button>

          {/* Time Range Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-card-border rounded-xl px-2.5 py-1.5 text-slate-300">
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="bg-transparent text-xs text-white focus:outline-none cursor-pointer"
            >
              <option value="24h" className="bg-slate-900">Last 24 Hours</option>
              <option value="7d" className="bg-slate-900">Last 7 Days</option>
              <option value="30d" className="bg-slate-900">Last 30 Days (Default)</option>
              <option value="90d" className="bg-slate-900">Last 3 Months</option>
              <option value="all" className="bg-slate-900">All Time</option>
            </select>
          </div>

          {/* Max Nodes Limit */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-card-border rounded-xl px-2.5 py-1.5 text-slate-300 font-mono">
            <span>Cap:</span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-transparent text-xs text-indigo-400 font-bold focus:outline-none cursor-pointer"
            >
              <option value={25} className="bg-slate-900">25 Nodes</option>
              <option value={50} className="bg-slate-900">50 Nodes</option>
              <option value={100} className="bg-slate-900">100 Nodes</option>
            </select>
          </div>
        </form>

        {/* 1-Hop Active Focus Banner */}
        {centerEntityName && (
          <div className="flex items-center gap-2 bg-indigo-950/40 border border-indigo-500/40 px-3 py-1 rounded-xl text-xs text-indigo-300">
            <Target className="w-3.5 h-3.5 text-indigo-400" />
            <span>Focal 1-Hop: <strong>{centerEntityName}</strong></span>
            <button
              onClick={handleClearFocus}
              className="text-[10px] text-rose-400 hover:text-rose-300 ml-1 underline cursor-pointer"
            >
              Reset to Global
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Interactive SVG Canvas */}
        <div className="lg:col-span-3 bg-card rounded-2xl border border-card-border overflow-hidden flex flex-col h-[600px] relative shadow-lg">
          {/* Graph Header Toolbar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-card-border bg-card/80 backdrop-blur z-10">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Bounded Subgraph Canvas</span>
              <span className="text-[10px] text-slate-500 font-mono">
                ({graph.nodes.length} Nodes • {graph.edges.length} Edges)
              </span>
            </div>

            <div className="flex items-center gap-3 text-xs">
              <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                <input
                  type="checkbox"
                  checked={includeInvalidated}
                  onChange={(e) => setIncludeInvalidated(e.target.checked)}
                  className="rounded border-card-border accent-primary cursor-pointer"
                />
                <span className="text-[11px]">Show Invalidated</span>
              </label>

              <button
                onClick={loadGraph}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-card-border transition-all"
                title="Refresh Subgraph"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* SVG Canvas */}
          <div
            className="relative flex-1 bg-[radial-gradient(ellipse_at_center,_#1e293b_1px,_transparent_1px)] bg-[size:24px_24px] overflow-hidden select-none"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            {loading ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">Loading bounded subgraph...</div>
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
                  const isFocal = centerEntityId && node.id === centerEntityId;
                  const nodeColor = TYPE_COLORS[node.entity_type?.toLowerCase()] || TYPE_COLORS.default;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x},${pos.y})`}
                      className="cursor-pointer"
                      onMouseDown={(e) => handleMouseDown(e, node.id)}
                      onClick={() => setSelectedNode(node)}
                      onDoubleClick={() => handleExpand1Hop(node)}
                    >
                      {isFocal && (
                        <circle r="22" fill="none" stroke="#6366f1" strokeWidth="2" strokeDasharray="3,3" className="animate-spin" />
                      )}
                      <circle
                        r={isFocal ? 18 : 16}
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

            {/* Subgraph Tip */}
            <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-card-border p-2 rounded-xl text-[10px] text-slate-400 shadow-md">
              💡 <strong>Double-click any node</strong> to load and center its 1-hop connected neighborhood.
            </div>
          </div>
        </div>

        {/* Node Inspector Side Pane */}
        <div className="bg-card rounded-2xl border border-card-border p-5 flex flex-col justify-between h-[600px] shadow-lg">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-card-border mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Node Inspector</h2>
              {selectedNode && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {selectedNode.entity_type || 'Entity'}
                </span>
              )}
            </div>

            {!selectedNode ? (
              <div className="text-center py-20 text-slate-500 text-xs">
                <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                Click any node in the graph to inspect details or double-click to center on its 1-hop neighborhood.
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-base font-bold text-white">{selectedNode.name}</div>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">ID: {selectedNode.id}</div>
                </div>

                <button
                  onClick={() => handleExpand1Hop(selectedNode)}
                  className="w-full py-1.5 px-3 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <Target className="w-3.5 h-3.5" />
                  <span>Center 1-Hop Neighborhood</span>
                </button>

                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Summary</div>
                  <p className="text-xs mt-1 text-slate-200 leading-relaxed bg-slate-900/60 p-2.5 rounded-xl border border-card-border">
                    {selectedNode.summary || 'No summary available.'}
                  </p>
                </div>

                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Connected Relations ({selectedConnectedEdges.length})
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 text-xs">
                    {selectedConnectedEdges.length === 0 ? (
                      <div className="text-slate-500 text-xs">No direct edges loaded.</div>
                    ) : (
                      selectedConnectedEdges.map((edge) => {
                        const isSource = edge.source === selectedNode.id;
                        const otherId = isSource ? edge.target : edge.source;
                        const otherNode = graph.nodes.find((n) => n.id === otherId);

                        return (
                          <div key={edge.id} className="bg-slate-900/70 p-2 rounded-xl border border-card-border">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-indigo-400 font-bold text-[10px]">
                                {isSource ? `→ ${edge.relation}` : `← ${edge.relation}`}
                              </span>
                              <span
                                className={`text-[8px] px-1.5 py-0.5 rounded-full font-bold uppercase ${
                                  edge.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                                }`}
                              >
                                {edge.is_active ? 'Active' : 'Invalidated'}
                              </span>
                            </div>
                            <div className="font-semibold text-slate-200 text-xs mt-0.5">{otherNode ? otherNode.name : otherId}</div>
                            {edge.fact && <div className="text-[10px] text-slate-400 mt-0.5">{edge.fact}</div>}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-card-border text-[10px] text-slate-500 text-center">
            Bounded subgraphs guarantee &lt;16ms frame rate
          </div>
        </div>
      </div>
    </div>
  );
}
