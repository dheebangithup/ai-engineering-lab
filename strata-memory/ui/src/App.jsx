import React, { useState, useEffect } from 'react';
import { fetchStats } from './api';
import StatsRibbon from './components/StatsRibbon';
import EntityGraphView from './components/EntityGraphView';
import SemanticClusterView from './components/SemanticClusterView';
import EpisodicTimelineView from './components/EpisodicTimelineView';
import ProceduralRunbooksView from './components/ProceduralRunbooksView';
import SupersedingLineageView from './components/SupersedingLineageView';
import IngestWorkbench from './components/IngestWorkbench';
import RecallSandbox from './components/RecallSandbox';
import FeedbackControl from './components/FeedbackControl';
import WorkingMemoryInspector from './components/WorkingMemoryInspector';
import {
  Share2,
  Sparkles,
  Clock,
  BookOpen,
  GitBranch,
  Zap,
  Search,
  Award,
  Cpu,
  Database
} from 'lucide-react';

const TABS = [
  { id: 'entity_graph', label: 'Entity Graph', icon: Share2 },
  { id: 'semantic', label: 'Semantic Clusters', icon: Sparkles },
  { id: 'episodic', label: 'Episodic Stream', icon: Clock },
  { id: 'procedural', label: 'Runbooks', icon: BookOpen },
  { id: 'lineage', label: 'Superseding & Lineage', icon: GitBranch },
  { id: 'ingest', label: 'Ingest Pipeline', icon: Zap },
  { id: 'recall', label: 'Recall Sandbox', icon: Search },
  { id: 'feedback', label: 'Feedback & Utility', icon: Award },
  { id: 'working', label: 'Working Memory', icon: Cpu },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('entity_graph');
  const [namespace, setNamespace] = useState('default');
  const [stats, setStats] = useState(null);
  const [namespaces, setNamespaces] = useState(['default', 'user_alice', 'coding_assistant']);

  useEffect(() => {
    loadStats();
  }, [namespace]);

  const loadStats = async () => {
    const data = await fetchStats(namespace);
    setStats(data);
    if (data?.namespaces?.length > 0) {
      setNamespaces(data.namespaces);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 p-4 md:p-6 max-w-7xl mx-auto flex flex-col justify-between">
      <div>
        {/* Top Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between pb-4 mb-6 border-b border-card-border gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-bold text-lg">
              Σ
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">Strata Memory Studio</h1>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Live Engine
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  4-Pillar Cognitive System
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Visualizer &amp; Testing Workbench for Neon PostgreSQL &amp; Laya Decision Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            {/* Namespace Selector */}
            <div className="flex items-center gap-2 bg-card px-3 py-1.5 rounded-xl border border-card-border">
              <span className="text-slate-400">Namespace:</span>
              <select
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                className="bg-transparent font-medium text-white focus:outline-none cursor-pointer"
              >
                {namespaces.map((ns) => (
                  <option key={ns} value={ns} className="bg-slate-900 text-white">
                    {ns}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 bg-card px-3 py-1.5 rounded-xl border border-card-border">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-mono text-slate-200">Neon Postgres</span>
            </div>
          </div>
        </header>

        {/* Global Statistics Ribbon */}
        <StatsRibbon stats={stats} />

        {/* Navigation Tabs */}
        <nav className="mb-6">
          <div className="flex items-center gap-1.5 bg-card p-1.5 rounded-2xl border border-card-border overflow-x-auto">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl whitespace-nowrap transition-all duration-150 ${
                    isActive
                      ? 'bg-primary text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </nav>

        {/* Active View Container */}
        <main>
          {activeTab === 'entity_graph' && <EntityGraphView namespace={namespace} />}
          {activeTab === 'semantic' && <SemanticClusterView namespace={namespace} />}
          {activeTab === 'episodic' && <EpisodicTimelineView namespace={namespace} />}
          {activeTab === 'procedural' && <ProceduralRunbooksView namespace={namespace} />}
          {activeTab === 'lineage' && <SupersedingLineageView namespace={namespace} />}
          {activeTab === 'ingest' && <IngestWorkbench namespace={namespace} />}
          {activeTab === 'recall' && <RecallSandbox namespace={namespace} />}
          {activeTab === 'feedback' && <FeedbackControl namespace={namespace} />}
          {activeTab === 'working' && <WorkingMemoryInspector namespace={namespace} />}
        </main>
      </div>

      {/* Footer */}
      <footer className="mt-12 pt-4 border-t border-card-border flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
        <div>Strata Memory Engine • Standalone 4-Pillar Cognitive System</div>
        <div className="font-mono text-[11px]">API: http://localhost:8080 • UI: http://localhost:3000</div>
      </footer>
    </div>
  );
}
