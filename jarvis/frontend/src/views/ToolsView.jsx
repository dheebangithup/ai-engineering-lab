import React, { useState } from 'react';
import { Wrench, Shield, Search, Lock, CheckCircle2, AlertOctagon } from 'lucide-react';

export function ToolsView({ toolsList }) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const tools = toolsList || [];

  const categories = ['all', ...Array.from(new Set(tools.map((t) => t.category)))];

  const filteredTools = tools.filter((t) => {
    const matchesSearch =
      t.tool_id.toLowerCase().includes(search.toLowerCase()) ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || t.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Wrench color="var(--emerald)" size={24} />
          Tools Gateway & Security Permissions
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          Deterministic sandbox enforcing three security tiers (SAFE, SENSITIVE, DANGEROUS) and the Uber 3-meta-tool pattern.
        </p>
      </div>

      {/* Meta-Tools Uber Pattern Info Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.08), rgba(16, 24, 40, 0.75))',
          borderColor: 'rgba(0, 229, 255, 0.25)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <Shield size={28} color="var(--cyan)" style={{ flexShrink: 0 }} />
        <div>
          <div style={{ fontWeight: 600, color: 'var(--cyan)', fontSize: '0.9rem' }}>
            Uber Pattern Active: Agents Only See 3 Dynamic Meta-Tools
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Regardless of tool count ({tools.length} currently registered), LLMs are only provided with <code>search_tools</code>, <code>list_tools</code>, and <code>execute_tool</code>, preventing context exhaustion and hallucinated arguments.
          </div>
        </div>
      </div>

      {/* Search and Category Filter */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <Search size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
          <input
            type="text"
            className="hud-input"
            placeholder="Search tools by id, keyword, or action..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: '100%', paddingLeft: '36px' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className="hud-btn hud-btn-sm"
              style={{
                background: selectedCategory === cat ? 'var(--cyan)' : 'rgba(255, 255, 255, 0.06)',
                color: selectedCategory === cat ? '#000' : 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                border: '1px solid',
                borderColor: selectedCategory === cat ? 'var(--cyan)' : 'var(--border-subtle)',
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Tools Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.86rem' }}>
          <thead>
            <tr style={{ background: 'rgba(10, 15, 26, 0.8)', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Tool ID & Name</th>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Category</th>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Security Tier</th>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Approval Gate</th>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Description</th>
              <th style={{ padding: '14px 18px', color: 'var(--text-muted)', fontWeight: 600 }}>Parameters</th>
            </tr>
          </thead>
          <tbody>
            {filteredTools.map((t) => {
              const tierClass =
                t.permission_tier === 'dangerous'
                  ? 'rose'
                  : t.permission_tier === 'sensitive'
                  ? 'amber'
                  : 'emerald';
              const paramKeys = Object.keys(t.parameters || {});

              return (
                <tr
                  key={t.tool_id}
                  style={{ borderBottom: '1px solid rgba(0, 229, 255, 0.06)', transition: 'background 0.2s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0, 229, 255, 0.03)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '14px 18px' }}>
                    <div style={{ fontWeight: 600, color: '#fff', fontFamily: 'var(--font-mono)' }}>{t.tool_id}</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)' }}>{t.name}</div>
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    <span className="hud-badge cyan">{t.category}</span>
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    <span className={`hud-badge ${tierClass}`}>{t.permission_tier}</span>
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    {t.requires_approval ? (
                      <span style={{ color: 'var(--rose)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem' }}>
                        <AlertOctagon size={14} /> Mandatory Human Approval
                      </span>
                    ) : (
                      <span style={{ color: 'var(--emerald)', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem' }}>
                        <CheckCircle2 size={14} /> Auto-Permitted
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '14px 18px', color: 'var(--text-muted)', maxWidth: '320px', lineHeight: 1.4 }}>
                    {t.description}
                  </td>
                  <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                    {paramKeys.length > 0 ? (
                      paramKeys.map((p) => (
                        <code key={p} style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', marginRight: '4px', color: 'var(--cyan)' }}>
                          {p}
                        </code>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-dim)' }}>None</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
