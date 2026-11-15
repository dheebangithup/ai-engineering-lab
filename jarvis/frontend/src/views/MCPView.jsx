import React, { useState } from 'react';
import { Layers, ShieldCheck, Terminal, RefreshCw, Check, AlertCircle } from 'lucide-react';

export function MCPView({ mcpData, onRefresh }) {
  const [syncingId, setSyncingId] = useState(null);
  const [toast, setToast] = useState('');

  const servers = mcpData ? Object.entries(mcpData.servers || {}) : [];

  const handleSync = async (sid) => {
    setSyncingId(sid);
    try {
      // Simulate quick re-sync
      await new Promise((r) => setTimeout(r, 600));
      setToast(`MCP server '${sid}' synchronized successfully.`);
      onRefresh();
      setTimeout(() => setToast(''), 3000);
    } catch (e) {
      alert(`Sync failed: ${e.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers color="var(--purple)" size={24} />
          External MCP (Model Context Protocol) Servers
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          Pluggable external capabilities integrated over standard stdio / SSE MCP protocol without modifying host systems.
        </p>
      </div>

      {toast && (
        <div style={{ padding: '10px 14px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--emerald)', borderRadius: '6px', color: 'var(--emerald)', fontSize: '0.84rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Check size={16} />
          {toast}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
        {servers.map(([sid, s]) => (
          <div key={sid} className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{s.name}</h3>
                <span className={`hud-badge ${s.enabled ? 'emerald' : 'rose'}`}>
                  {s.enabled ? 'CONNECTED' : 'DISABLED'}
                </span>
              </div>

              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
                ID: {s.server_id} | Transport: {s.transport}
              </div>

              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: 1.5 }}>
                {s.description || 'External server providing tool capabilities.'}
              </div>

              {/* Command execution */}
              <div style={{ padding: '8px 12px', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginBottom: '14px', fontFamily: 'var(--font-mono)', fontSize: '0.76rem', color: 'var(--cyan)', wordBreak: 'break-all' }}>
                <Terminal size={12} style={{ display: 'inline', marginRight: '6px' }} />
                {s.command} {(s.args || []).join(' ')}
              </div>

              {/* Security Overrides */}
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                  Enforced Security Tiers:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {Object.entries(s.security_overrides || {}).map(([tool, tier]) => (
                    <span
                      key={tool}
                      className={`hud-badge ${tier === 'dangerous' ? 'rose' : tier === 'sensitive' ? 'amber' : 'emerald'}`}
                      style={{ fontSize: '0.68rem' }}
                    >
                      {tool}: {tier}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
              <button
                onClick={() => handleSync(sid)}
                disabled={syncingId === sid}
                className="hud-btn hud-btn-secondary hud-btn-sm"
                style={{ flex: 1 }}
              >
                <RefreshCw size={13} className={syncingId === sid ? 'animate-spin' : ''} />
                {syncingId === sid ? 'Re-syncing...' : 'Re-sync Tools'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
