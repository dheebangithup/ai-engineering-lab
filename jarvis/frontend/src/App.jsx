import React, { useState, useEffect } from 'react';
import { MessageSquare, Cpu, Layers, Wrench, HardDrive, Shield, Activity, RefreshCw } from 'lucide-react';
import { ChatView } from './views/ChatView.jsx';
import { ProvidersView } from './views/ProvidersView.jsx';
import { MCPView } from './views/MCPView.jsx';
import { ToolsView } from './views/ToolsView.jsx';
import { WorkspaceView } from './views/WorkspaceView.jsx';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [systemStatus, setSystemStatus] = useState(null);
  const [providersData, setProvidersData] = useState(null);
  const [mcpData, setMcpData] = useState(null);
  const [toolsList, setToolsList] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAllData = async () => {
    try {
      const [statusRes, provRes, mcpRes, toolsRes] = await Promise.all([
        fetch('/v1/status').then((r) => (r.ok ? r.json() : null)),
        fetch('/v1/settings/providers').then((r) => (r.ok ? r.json() : null)),
        fetch('/v1/settings/mcp').then((r) => (r.ok ? r.json() : null)),
        fetch('/v1/tools').then((r) => (r.ok ? r.json() : [])),
      ]);

      if (statusRes) setSystemStatus(statusRes);
      if (provRes) setProvidersData(provRes);
      if (mcpRes) setMcpData(mcpRes);
      if (toolsRes) setToolsList(toolsRes);
    } catch (e) {
      console.warn('Data sync warning:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const navItems = [
    { id: 'chat', label: 'Chat & Console', icon: MessageSquare },
    { id: 'providers', label: 'LLM Providers & Fallback', icon: Cpu },
    { id: 'mcp', label: 'External MCP Servers', icon: Layers },
    { id: 'tools', label: 'Tools & Permissions', icon: Wrench },
    { id: 'workspace', label: 'Workspace SSOT', icon: HardDrive },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: '270px',
          background: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Arc Reactor Header */}
        <div
          style={{
            padding: '24px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div className="arc-reactor-wrapper">
            <div className="arc-outer-ring" />
            <div className="arc-inner-ring" />
            <div className="arc-core" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '2px', color: '#fff', margin: 0 }}>
              J.A.R.V.I.S.
            </h1>
            <div style={{ fontSize: '0.66rem', color: 'var(--cyan)', fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Mark VII Autonomous Core
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ padding: '16px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: '1px solid',
                  borderColor: isActive ? 'var(--cyan)' : 'transparent',
                  background: isActive ? 'rgba(0, 229, 255, 0.12)' : 'transparent',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                  fontSize: '0.86rem',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s',
                  boxShadow: isActive ? '0 0 14px rgba(0, 229, 255, 0.15)' : 'none',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                    e.currentTarget.style.color = '#fff';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-muted)';
                  }
                }}
              >
                <Icon size={18} color={isActive ? 'var(--cyan)' : 'var(--text-dim)'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer Status */}
        <div style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)', background: 'rgba(0, 0, 0, 0.25)' }}>
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.74rem',
              fontWeight: 600,
              color: 'var(--emerald)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span className="pulse-dot" />
            <span>
              {systemStatus?.status ? systemStatus.status.toUpperCase() : 'ONLINE'} (
              {systemStatus?.active_providers?.length || 0} LLMs, {toolsList.length} Tools)
            </span>
          </div>

          <div style={{ marginTop: '8px', fontSize: '0.7rem', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            Root: <span style={{ color: 'var(--text-muted)' }}>{systemStatus?.workspace_root || '~/.jarvis'}</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeTab === 'chat' && (
          <ChatView
            systemStatus={systemStatus}
            providersData={providersData}
          />
        )}
        {activeTab === 'providers' && (
          <ProvidersView
            providersData={providersData}
            systemStatus={systemStatus}
            onRefresh={fetchAllData}
          />
        )}
        {activeTab === 'mcp' && (
          <MCPView
            mcpData={mcpData}
            onRefresh={fetchAllData}
          />
        )}
        {activeTab === 'tools' && (
          <ToolsView toolsList={toolsList} />
        )}
        {activeTab === 'workspace' && (
          <WorkspaceView
            systemStatus={systemStatus}
            providersData={providersData}
            mcpData={mcpData}
          />
        )}
      </main>
    </div>
  );
}
