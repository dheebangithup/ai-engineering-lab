import React, { useState } from 'react';
import { Folder, FileText, Database, Shield, Terminal, HardDrive } from 'lucide-react';

export function WorkspaceView({ systemStatus, providersData, mcpData }) {
  const [activeTab, setActiveTab] = useState('tree');

  const workspaceRoot = systemStatus?.workspace_root || '~/.jarvis';

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HardDrive color="var(--blue)" size={24} />
          Centralized Workspace & SSOT Memory Storage
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          Single Source of Truth (SSOT) directory anchoring all configs, memory caches, logs, and sandboxed code execution.
        </p>
      </div>

      {/* Directory Root Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Root Storage Anchor (JARVIS_WORKSPACE)
          </div>
          <div style={{ fontSize: '1rem', color: 'var(--cyan)', fontFamily: 'var(--font-mono)', fontWeight: 600, marginTop: '2px' }}>
            {workspaceRoot}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('tree')}
            className="hud-btn hud-btn-sm"
            style={{
              background: activeTab === 'tree' ? 'var(--cyan)' : 'rgba(255,255,255,0.06)',
              color: activeTab === 'tree' ? '#000' : 'var(--text-muted)',
              border: '1px solid',
              borderColor: activeTab === 'tree' ? 'var(--cyan)' : 'var(--border-subtle)',
            }}
          >
            Folder Architecture
          </button>
          <button
            onClick={() => setActiveTab('providers_json')}
            className="hud-btn hud-btn-sm"
            style={{
              background: activeTab === 'providers_json' ? 'var(--cyan)' : 'rgba(255,255,255,0.06)',
              color: activeTab === 'providers_json' ? '#000' : 'var(--text-muted)',
              border: '1px solid',
              borderColor: activeTab === 'providers_json' ? 'var(--cyan)' : 'var(--border-subtle)',
            }}
          >
            providers.json
          </button>
          <button
            onClick={() => setActiveTab('mcp_json')}
            className="hud-btn hud-btn-sm"
            style={{
              background: activeTab === 'mcp_json' ? 'var(--cyan)' : 'rgba(255,255,255,0.06)',
              color: activeTab === 'mcp_json' ? '#000' : 'var(--text-muted)',
              border: '1px solid',
              borderColor: activeTab === 'mcp_json' ? 'var(--cyan)' : 'var(--border-subtle)',
            }}
          >
            mcp_servers.json
          </button>
        </div>
      </div>

      {activeTab === 'tree' && (
        <div className="glass-panel" style={{ padding: '24px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--cyan)', fontWeight: 600, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Folder size={18} />
            {workspaceRoot}/
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '20px' }}>
            <div>
              <div style={{ color: '#60a5fa', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={16} /> settings/
              </div>
              <div style={{ paddingLeft: '24px', color: 'var(--text-muted)', marginTop: '4px', fontSize: '0.8rem' }}>
                ├── <strong>providers.json</strong> — Dynamic LLM provider registry, priorities & fallback chains<br />
                ├── <strong>mcp_servers.json</strong> — External MCP server stdio configs & tool security overrides<br />
                └── <strong>agent_config.json</strong> — System prompt archetypes & runtime parameters
              </div>
            </div>

            <div>
              <div style={{ color: '#c084fc', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={16} /> memory/
              </div>
              <div style={{ paddingLeft: '24px', color: 'var(--text-muted)', marginTop: '4px', fontSize: '0.8rem' }}>
                ├── <strong>cache/</strong> — Fast semantic & procedural recall context caches<br />
                └── <strong>audit.jsonl</strong> — Append-only audit trail of all memory queries, edits, & purges
              </div>
            </div>

            <div>
              <div style={{ color: '#34d399', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={16} /> code_workspace/
              </div>
              <div style={{ paddingLeft: '24px', color: 'var(--text-muted)', marginTop: '4px', fontSize: '0.8rem' }}>
                └── <strong>artifacts/</strong> — Isolated directory for coding agent execution, tests, and diffs
              </div>
            </div>

            <div>
              <div style={{ color: '#fbbf24', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={16} /> logs/
              </div>
              <div style={{ paddingLeft: '24px', color: 'var(--text-muted)', marginTop: '4px', fontSize: '0.8rem' }}>
                ├── <strong>app.log</strong> — REST API gateway & HTTP request logs<br />
                └── <strong>jarvis.log</strong> — Agent reasoning traces, tool execution traces, & failover events
              </div>
            </div>

            <div>
              <div style={{ color: '#94a3b8', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Folder size={16} /> storage/
              </div>
              <div style={{ paddingLeft: '24px', color: 'var(--text-muted)', marginTop: '4px', fontSize: '0.8rem' }}>
                └── <strong>sessions.db</strong> — Conversation checkpoints & session history
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'providers_json' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <pre
            style={{
              background: 'rgba(0, 0, 0, 0.6)',
              padding: '16px',
              borderRadius: '8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.82rem',
              color: 'var(--cyan)',
              overflowX: 'auto',
              maxHeight: '520px',
            }}
          >
            {JSON.stringify(providersData, null, 2)}
          </pre>
        </div>
      )}

      {activeTab === 'mcp_json' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <pre
            style={{
              background: 'rgba(0, 0, 0, 0.6)',
              padding: '16px',
              borderRadius: '8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.82rem',
              color: 'var(--purple)',
              overflowX: 'auto',
              maxHeight: '520px',
            }}
          >
            {JSON.stringify(mcpData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
