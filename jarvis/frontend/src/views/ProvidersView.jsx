import React, { useState, useEffect } from 'react';
import {
  Cpu,
  ShieldCheck,
  AlertTriangle,
  Edit3,
  Trash2,
  Activity,
  Save,
  X,
  PlusCircle,
  Check,
  Key,
  Zap,
  CheckCircle2,
  Power,
  Layers,
  Plus,
} from 'lucide-react';

export function ProvidersView({ providersData, onRefresh, systemStatus }) {
  // Fallback chain state
  const [fallbackSelections, setFallbackSelections] = useState({
    fast: { primary: '', secondary: '' },
    reasoning: { primary: '', secondary: '' },
    decision: { primary: '', secondary: '' },
  });
  const [savingFallbacks, setSavingFallbacks] = useState(false);
  const [fallbackToast, setFallbackToast] = useState('');

  // Provider Form State
  const [editingProviderId, setEditingProviderId] = useState(null);
  const [formData, setFormData] = useState({
    provider_id: '',
    name: '',
    kind: 'openai_compatible',
    base_url: '',
    api_key: '',
    models: {},
    enabled: true,
  });

  // Sub-form for adding a model to the provider
  const [newModelInput, setNewModelInput] = useState({
    model_id: '',
    fast: true,
    reasoning: false,
    decision: false,
  });

  const [savingProvider, setSavingProvider] = useState(false);
  const [providerToast, setProviderToast] = useState('');

  // Connectivity & Token Verification State
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [cardPingStatus, setCardPingStatus] = useState({});

  useEffect(() => {
    if (providersData && providersData.fallback_chains) {
      const chains = providersData.fallback_chains;
      setFallbackSelections({
        fast: {
          primary: chains.fast?.[0] || '',
          secondary: chains.fast?.[1] || '',
        },
        reasoning: {
          primary: chains.reasoning?.[0] || '',
          secondary: chains.reasoning?.[1] || '',
        },
        decision: {
          primary: chains.decision?.[0] || '',
          secondary: chains.decision?.[1] || '',
        },
      });
    }
  }, [providersData]);

  const activeProviders = providersData ? Object.entries(providersData.providers || {}) : [];

  // Handle saving Fallback Priorities to providers.json
  const handleSaveFallbacks = async () => {
    setSavingFallbacks(true);
    setFallbackToast('');
    try {
      const roles = ['fast', 'reasoning', 'decision'];
      for (const role of roles) {
        const sel = fallbackSelections[role] || {};
        const chain = [];
        if (sel.primary) chain.push(sel.primary);
        if (sel.secondary && sel.secondary !== sel.primary) chain.push(sel.secondary);

        const resp = await fetch('/v1/settings/fallback_chains', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role, provider_ids: chain }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || resp.statusText);
        }
      }
      setFallbackToast('Fallback chains successfully synchronized to providers.json and reloaded in Provider Gateway!');
      onRefresh();
      setTimeout(() => setFallbackToast(''), 4000);
    } catch (e) {
      alert(`Failed to save fallback priorities: ${e.message}`);
    } finally {
      setSavingFallbacks(false);
    }
  };

  // Test Connection and Verify API Token
  const handleTestConnection = async () => {
    if (!formData.base_url.trim()) {
      alert('Please enter a Base URL Endpoint to test.');
      return;
    }
    setTestingConnection(true);
    setTestResult(null);

    try {
      const firstModelId = Object.keys(formData.models)[0] || newModelInput.model_id.trim() || undefined;
      const resp = await fetch('/v1/settings/providers/test_connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_url: formData.base_url.trim(),
          api_key: formData.api_key.trim(),
          kind: formData.kind,
          model_id: firstModelId,
        }),
      });

      const data = await resp.json();
      setTestResult(data);

      // Auto-populate model input if no models configured yet
      if (data.success && data.available_models && data.available_models.length > 0) {
        if (Object.keys(formData.models).length === 0 && !newModelInput.model_id) {
          setNewModelInput((prev) => ({ ...prev, model_id: data.available_models[0] }));
        }
      }
    } catch (e) {
      setTestResult({
        success: false,
        status: 'error',
        message: `Network error while contacting test endpoint: ${e.message}`,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  // Test Ping directly on existing provider card
  const handlePingCard = async (pid, p) => {
    setCardPingStatus((prev) => ({ ...prev, [pid]: { loading: true } }));
    try {
      const resp = await fetch('/v1/settings/providers/test_connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_url: p.base_url,
          api_key: p.api_key,
          kind: p.kind,
        }),
      });
      const data = await resp.json();
      setCardPingStatus((prev) => ({ ...prev, [pid]: { loading: false, result: data } }));
    } catch (e) {
      setCardPingStatus((prev) => ({
        ...prev,
        [pid]: { loading: false, result: { success: false, message: e.message } },
      }));
    }
  };

  // Quick toggle enabled/disabled directly on card
  const handleToggleCardEnabled = async (pid, p) => {
    try {
      const updated = {
        ...p,
        enabled: !p.enabled,
      };
      const resp = await fetch('/v1/settings/providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      if (resp.ok) {
        onRefresh();
      } else {
        alert('Failed to toggle provider status');
      }
    } catch (e) {
      alert(`Error toggling provider status: ${e.message}`);
    }
  };

  // Start editing a provider
  const handleEditProvider = (pid) => {
    const p = providersData.providers[pid];
    if (!p) return;

    setEditingProviderId(pid);

    const modelsCopy = {};
    if (p.models && Object.keys(p.models).length > 0) {
      Object.entries(p.models).forEach(([k, v]) => {
        modelsCopy[k] = {
          model_id: v.model_id || k,
          roles: Array.isArray(v.roles) ? [...v.roles] : ['fast'],
          max_tokens: v.max_tokens || 4096,
          temperature: v.temperature !== undefined ? v.temperature : 0.7,
        };
      });
    }

    setFormData({
      provider_id: p.provider_id,
      name: p.name,
      kind: p.kind,
      base_url: p.base_url,
      api_key: p.api_key || '',
      models: modelsCopy,
      enabled: p.enabled !== false,
    });
    setNewModelInput({
      model_id: '',
      fast: true,
      reasoning: false,
      decision: false,
    });
    setProviderToast('');
    setTestResult(null);

    // Smooth scroll to form
    document.getElementById('provider-form-anchor')?.scrollIntoView({ behavior: 'smooth' });
  };

  // Cancel edit
  const handleCancelEdit = () => {
    setEditingProviderId(null);
    setFormData({
      provider_id: '',
      name: '',
      kind: 'openai_compatible',
      base_url: '',
      api_key: '',
      models: {},
      enabled: true,
    });
    setNewModelInput({
      model_id: '',
      fast: true,
      reasoning: false,
      decision: false,
    });
    setProviderToast('');
    setTestResult(null);
  };

  // Model management helpers inside form
  const handleToggleModelRole = (modelKey, role) => {
    setFormData((prev) => {
      const curModel = prev.models[modelKey];
      if (!curModel) return prev;
      const curRoles = curModel.roles || [];
      const hasRole = curRoles.includes(role);
      let updatedRoles = hasRole ? curRoles.filter((r) => r !== role) : [...curRoles, role];
      if (updatedRoles.length === 0) updatedRoles = ['fast']; // minimum 1 role
      return {
        ...prev,
        models: {
          ...prev.models,
          [modelKey]: {
            ...curModel,
            roles: updatedRoles,
          },
        },
      };
    });
  };

  const handleRemoveModel = (modelKey) => {
    setFormData((prev) => {
      const nextModels = { ...prev.models };
      delete nextModels[modelKey];
      return { ...prev, models: nextModels };
    });
  };

  const handleAddModelFromInput = () => {
    const mid = newModelInput.model_id.trim();
    if (!mid) return;
    const roles = [];
    if (newModelInput.fast) roles.push('fast');
    if (newModelInput.reasoning) roles.push('reasoning');
    if (newModelInput.decision) roles.push('decision');

    setFormData((prev) => ({
      ...prev,
      models: {
        ...prev.models,
        [mid]: {
          model_id: mid,
          roles: roles.length > 0 ? roles : ['fast'],
          max_tokens: 4096,
          temperature: 0.7,
        },
      },
    }));

    setNewModelInput({
      model_id: '',
      fast: true,
      reasoning: false,
      decision: false,
    });
  };

  const handleQuickAddDiscoveredModel = (modelName) => {
    setFormData((prev) => {
      if (prev.models[modelName]) return prev;

      // Dynamically detect roles from model capabilities without hardcoding
      const caps = (testResult?.model_capabilities?.[modelName] || []).map((c) => c.toLowerCase());
      let roles = [];
      if (caps.includes('decision')) {
        roles.push('decision');
      }
      if (caps.includes('embedding')) {
        roles.push('embedding');
      }
      if (caps.includes('completion') || caps.includes('tools')) {
        roles.push('fast', 'reasoning');
      }
      if (roles.length === 0) {
        roles = ['fast', 'reasoning'];
      }

      return {
        ...prev,
        models: {
          ...prev.models,
          [modelName]: {
            model_id: modelName,
            roles,
            max_tokens: roles.includes('decision') ? 512 : 4096,
            temperature: roles.includes('decision') ? 0.2 : 0.7,
          },
        },
      };
    });
  };

  // Handle save/update provider to providers.json
  const handleSubmitProvider = async (e) => {
    e.preventDefault();
    setSavingProvider(true);
    setProviderToast('');

    const pid = editingProviderId || formData.provider_id.trim();
    if (!pid) {
      alert('Provider Slug ID is required.');
      setSavingProvider(false);
      return;
    }

    const currentModels = { ...formData.models };

    // Auto-add pending model input if present
    if (newModelInput.model_id.trim()) {
      const mid = newModelInput.model_id.trim();
      const roles = [];
      if (newModelInput.fast) roles.push('fast');
      if (newModelInput.reasoning) roles.push('reasoning');
      if (newModelInput.decision) roles.push('decision');
      currentModels[mid] = {
        model_id: mid,
        roles: roles.length > 0 ? roles : ['fast'],
        max_tokens: 4096,
        temperature: 0.7,
      };
    }

    if (Object.keys(currentModels).length === 0) {
      alert('Please configure at least one model for this provider.');
      setSavingProvider(false);
      return;
    }

    const payload = {
      provider_id: pid,
      name: formData.name.trim(),
      kind: formData.kind,
      base_url: formData.base_url.trim(),
      api_key: formData.api_key.trim(),
      models: currentModels,
      enabled: formData.enabled,
      priority: (editingProviderId && providersData.providers[pid]?.priority) || 10,
    };

    try {
      const resp = await fetch('/v1/settings/providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        setProviderToast(`Provider '${formData.name}' successfully synchronized to providers.json!`);
        handleCancelEdit();
        onRefresh();
        setTimeout(() => setProviderToast(''), 4000);
      } else {
        const err = await resp.json().catch(() => ({}));
        alert(`Failed to save provider: ${err.detail || resp.statusText}`);
      }
    } catch (err) {
      alert(`Error saving provider: ${err.message}`);
    } finally {
      setSavingProvider(false);
    }
  };

  // Handle remove provider from providers.json
  const handleDeleteProvider = async (pid) => {
    if (!confirm(`Are you sure you want to remove provider '${pid}' from providers.json?`)) return;
    try {
      const resp = await fetch(`/v1/settings/providers/${pid}`, { method: 'DELETE' });
      if (resp.ok) {
        onRefresh();
      }
    } catch (e) {
      alert(`Failed to remove provider: ${e.message}`);
    }
  };

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      {/* View Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Cpu color="var(--cyan)" size={24} />
          Multi-Provider LLM Gateway & Fallback Chains
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          Decoupled LLM Gateway with zero-downtime dynamic routing, token authentication verification, circuit breakers, and automatic failover. All changes strictly synchronize with <code>~/.jarvis/settings/providers.json</code>.
        </p>
      </div>

      {/* 1. Priority Fallback Chains Control Section */}
      <div className="glass-panel" style={{ padding: '22px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Priority Fallback Chains (Primary & Secondary Control)</h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Configure automatic failover priorities per operational role. If primary fails, traffic immediately cascades to secondary.
            </p>
          </div>
          <button
            onClick={handleSaveFallbacks}
            disabled={savingFallbacks}
            className="hud-btn hud-btn-primary hud-btn-sm"
          >
            <Save size={14} />
            {savingFallbacks ? 'Saving...' : 'Save Fallback Priorities'}
          </button>
        </div>

        {fallbackToast && (
          <div style={{ padding: '8px 12px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--emerald)', borderRadius: '6px', color: 'var(--emerald)', fontSize: '0.82rem', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check size={16} />
            {fallbackToast}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[
            {
              role: 'fast',
              label: 'Fast Execution',
              desc: 'Everyday conversational queries, tool synthesis, and quick stimulus-response',
            },
            {
              role: 'reasoning',
              label: 'Reasoning & Planning',
              desc: 'Complex multi-step engineering, architectural synthesis, coding tasks',
            },
            {
              role: 'decision',
              label: 'Decision Engine Fallback',
              desc: 'Sub-5ms linguistic intent classifier fallback model',
            },
          ].map(({ role, label, desc }) => (
            <div
              key={role}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(200px, 1.8fr) 1fr 1fr',
                gap: '16px',
                alignItems: 'center',
                padding: '12px 14px',
                background: 'rgba(10, 15, 26, 0.6)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, color: 'var(--cyan)', fontSize: '0.86rem', textTransform: 'uppercase' }}>
                  Role: {role} ({label})
                </div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginTop: '2px' }}>{desc}</div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>
                  1️⃣ Primary Provider
                </label>
                <select
                  className="hud-select"
                  style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem' }}
                  value={fallbackSelections[role]?.primary || ''}
                  onChange={(e) =>
                    setFallbackSelections((prev) => ({
                      ...prev,
                      [role]: { ...prev[role], primary: e.target.value },
                    }))
                  }
                >
                  <option value="">(None)</option>
                  {activeProviders.map(([pid, p]) => (
                    <option key={pid} value={pid} disabled={!p.enabled}>
                      {p.name} ({pid})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>
                  2️⃣ Secondary Fallback
                </label>
                <select
                  className="hud-select"
                  style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem' }}
                  value={fallbackSelections[role]?.secondary || ''}
                  onChange={(e) =>
                    setFallbackSelections((prev) => ({
                      ...prev,
                      [role]: { ...prev[role], secondary: e.target.value },
                    }))
                  }
                >
                  <option value="">(None)</option>
                  {activeProviders.map(([pid, p]) => (
                    <option key={pid} value={pid} disabled={!p.enabled}>
                      {p.name} ({pid})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Configured Providers Grid */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Configured Provider Endpoints</h3>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          Sync Target: ~/.jarvis/settings/providers.json
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '18px', marginBottom: '32px' }}>
        {activeProviders.map(([pid, p]) => {
          const health = systemStatus?.provider_health?.[pid];
          const pingInfo = cardPingStatus[pid];

          return (
            <div key={pid} className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>{p.name}</h4>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <button
                      onClick={() => handleToggleCardEnabled(pid, p)}
                      title={p.enabled ? 'Click to disable' : 'Click to enable'}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0,
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      <span className={`hud-badge ${p.enabled ? 'emerald' : 'rose'}`} style={{ cursor: 'pointer' }}>
                        {p.enabled ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </button>
                  </div>
                </div>

                <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
                  ID: {p.provider_id} | Protocol: {p.kind}
                </div>

                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px', wordBreak: 'break-all' }}>
                  Base URL: <code>{p.base_url}</code>
                </div>

                {/* Health & Ping Latency */}
                {health && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', marginBottom: '8px', color: health.status === 'healthy' ? 'var(--emerald)' : 'var(--rose)' }}>
                    <Activity size={14} />
                    <span>
                      {health.status.toUpperCase()} ({health.latency_ms ? `${Math.round(health.latency_ms)}ms latency` : 'Active'})
                    </span>
                  </div>
                )}

                {/* Live Card Ping Result */}
                {pingInfo && (
                  <div style={{ marginBottom: '10px', fontSize: '0.76rem', fontFamily: 'var(--font-mono)' }}>
                    {pingInfo.loading ? (
                      <span style={{ color: 'var(--cyan)' }}>Testing connection & credentials...</span>
                    ) : pingInfo.result?.success ? (
                      <span style={{ color: 'var(--emerald)' }}>
                        ✅ Token Verified ({pingInfo.result.latency_ms}ms)
                      </span>
                    ) : (
                      <span style={{ color: 'var(--rose)' }}>
                        ❌ {pingInfo.result?.status === 'auth_failed' ? 'Invalid API Token' : 'Unreachable'}
                      </span>
                    )}
                  </div>
                )}

                {/* Configured Models & Operational Roles */}
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                    Configured Models ({Object.keys(p.models || {}).length}):
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {Object.entries(p.models || {}).map(([mKey, mSpec]) => (
                      <div
                        key={mKey}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '4px 8px',
                          background: 'rgba(0, 0, 0, 0.35)',
                          borderRadius: '4px',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                        }}
                      >
                        <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>
                          {mKey}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {(mSpec.roles || ['fast']).map((role) => (
                            <span
                              key={role}
                              style={{
                                fontSize: '0.64rem',
                                padding: '2px 5px',
                                borderRadius: '3px',
                                textTransform: 'uppercase',
                                background:
                                  role === 'fast'
                                    ? 'rgba(0, 229, 255, 0.15)'
                                    : role === 'reasoning'
                                    ? 'rgba(168, 85, 247, 0.15)'
                                    : 'rgba(245, 158, 11, 0.15)',
                                color:
                                  role === 'fast'
                                    ? 'var(--cyan)'
                                    : role === 'reasoning'
                                    ? 'var(--purple)'
                                    : 'var(--amber)',
                                border: `1px solid ${
                                  role === 'fast'
                                    ? 'var(--cyan)'
                                    : role === 'reasoning'
                                    ? 'var(--purple)'
                                    : 'var(--amber)'
                                }`,
                              }}
                            >
                              {role}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => handlePingCard(pid, p)}
                  disabled={pingInfo?.loading}
                  className="hud-btn hud-btn-secondary hud-btn-sm"
                  title="Test API token & endpoint ping"
                >
                  <Zap size={13} color="var(--cyan)" />
                  Verify Ping
                </button>
                <button
                  onClick={() => handleEditProvider(pid)}
                  className="hud-btn hud-btn-secondary hud-btn-sm"
                >
                  <Edit3 size={13} />
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteProvider(pid)}
                  className="hud-btn hud-btn-danger hud-btn-sm"
                >
                  <Trash2 size={13} />
                  Remove
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. Add / Edit Provider Form Card */}
      <div id="provider-form-anchor" className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
              {editingProviderId ? `✏️ Edit Provider: ${formData.name}` : 'Add New Provider Endpoint'}
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Configure base URL, authentication token, and model role mappings. Saves directly to <code>providers.json</code>.
            </p>
          </div>
          {editingProviderId && (
            <span className="hud-badge cyan" style={{ fontSize: '0.78rem' }}>
              EDITING MODE
            </span>
          )}
        </div>

        {providerToast && (
          <div style={{ padding: '8px 12px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--emerald)', borderRadius: '6px', color: 'var(--emerald)', fontSize: '0.82rem', marginBottom: '16px' }}>
            {providerToast}
          </div>
        )}

        {/* Live Connectivity Test Result Display Banner */}
        {testResult && (
          <div
            style={{
              padding: '14px 18px',
              borderRadius: '8px',
              border: `1px solid ${testResult.success ? 'var(--emerald)' : 'var(--rose)'}`,
              background: testResult.success ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
              marginBottom: '18px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: testResult.success ? 'var(--emerald)' : 'var(--rose)', fontSize: '0.9rem' }}>
              {testResult.success ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
              <span>
                {testResult.success
                  ? `Connection & API Token Verified! (${testResult.latency_ms}ms latency)`
                  : testResult.status === 'auth_failed'
                  ? 'Authentication Failed: Invalid API Token / Key'
                  : testResult.status === 'unreachable'
                  ? 'Endpoint Unreachable'
                  : 'Connectivity Test Failed'}
              </span>
            </div>

            <div style={{ fontSize: '0.82rem', color: 'var(--text-main)', marginTop: '6px', lineHeight: 1.4 }}>
              {testResult.message}
            </div>

            {/* Discovered Models List */}
            {testResult.available_models && testResult.available_models.length > 0 && (
              <div style={{ marginTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '8px' }}>
                <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                  Discovered Remote Models ({testResult.available_models.length}): Click any model to attach it to this provider
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '110px', overflowY: 'auto' }}>
                  {testResult.available_models.slice(0, 30).map((m) => (
                    <span
                      key={m}
                      className="hud-badge cyan"
                      style={{ cursor: 'pointer', fontSize: '0.7rem' }}
                      title="Click to add this model to the provider"
                      onClick={() => handleQuickAddDiscoveredModel(m)}
                    >
                      + {m}
                    </span>
                  ))}
                  {testResult.available_models.length > 30 && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', alignSelf: 'center' }}>
                      +{testResult.available_models.length - 30} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmitProvider}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Provider Slug ID
              </label>
              <input
                type="text"
                className="hud-input"
                style={{ width: '100%', opacity: editingProviderId ? 0.6 : 1 }}
                placeholder="e.g. kodekloud, custom_llm"
                required
                disabled={Boolean(editingProviderId)}
                value={formData.provider_id}
                onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
              />
              {editingProviderId && (
                <div style={{ fontSize: '0.7rem', color: 'var(--cyan)', marginTop: '4px' }}>
                  Provider ID is locked while editing
                </div>
              )}
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Display Name
              </label>
              <input
                type="text"
                className="hud-input"
                style={{ width: '100%' }}
                placeholder="e.g. KodeKloud AI (OpenAI Compatible)"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Kind / Protocol
              </label>
              <select
                className="hud-select"
                style={{ width: '100%' }}
                value={formData.kind}
                onChange={(e) => setFormData({ ...formData, kind: e.target.value })}
              >
                <option value="openai_compatible">OpenAI-Compatible</option>
                <option value="ollama">Ollama</option>
                <option value="groq">Groq</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Base URL Endpoint
              </label>
              <input
                type="url"
                className="hud-input"
                style={{ width: '100%' }}
                placeholder="https://api.ai.kodekloud.com/v1"
                required
                value={formData.base_url}
                onChange={(e) => {
                  setFormData({ ...formData, base_url: e.target.value });
                  setTestResult(null);
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              API Key / Authentication Token (Optional for Ollama)
            </label>
            <input
              type="password"
              className="hud-input"
              style={{ width: '100%' }}
              placeholder="sk-..."
              value={formData.api_key}
              onChange={(e) => {
                setFormData({ ...formData, api_key: e.target.value });
                setTestResult(null);
              }}
            />
          </div>

          {/* Models Configuration & Role Assignment */}
          <div
            style={{
              padding: '16px',
              background: 'rgba(0, 0, 0, 0.4)',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase' }}>
                  Configured Models & Operational Role Assignment
                </label>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Assign roles to each model: <strong>Fast</strong> (conversations & tools), <strong>Reasoning</strong> (code & planning), <strong>Decision</strong> (intent classification).
                </div>
              </div>
              <span className="hud-badge cyan">
                {Object.keys(formData.models).length} Models Configured
              </span>
            </div>

            {/* Existing Models List in Form */}
            {Object.keys(formData.models).length === 0 ? (
              <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '6px', fontSize: '0.78rem', color: 'var(--text-dim)', textAlign: 'center', marginBottom: '14px' }}>
                No models added yet. Use the model input below or click discovered models from connection test.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                {Object.entries(formData.models).map(([mKey, mSpec]) => (
                  <div
                    key={mKey}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      background: 'rgba(10, 15, 26, 0.8)',
                      borderRadius: '6px',
                      border: '1px solid var(--border-subtle)',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-main)' }}>
                      {mKey}
                    </span>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Roles:</span>
                      {['fast', 'reasoning', 'decision'].map((role) => {
                        const isAssigned = (mSpec.roles || []).includes(role);
                        return (
                          <button
                            type="button"
                            key={role}
                            onClick={() => handleToggleModelRole(mKey, role)}
                            style={{
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              cursor: 'pointer',
                              border: `1px solid ${isAssigned ? 'var(--cyan)' : 'var(--border-subtle)'}`,
                              background: isAssigned ? 'rgba(0, 229, 255, 0.2)' : 'transparent',
                              color: isAssigned ? 'var(--cyan)' : 'var(--text-dim)',
                            }}
                          >
                            {isAssigned ? `✓ ${role}` : role}
                          </button>
                        );
                      })}

                      <button
                        type="button"
                        onClick={() => handleRemoveModel(mKey)}
                        className="hud-btn hud-btn-danger hud-btn-sm"
                        style={{ padding: '4px 6px', marginLeft: '6px' }}
                        title="Remove this model"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add Model Sub-Row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1.5fr auto auto auto auto',
                gap: '8px',
                alignItems: 'center',
                padding: '10px 12px',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '6px',
              }}
            >
              <input
                type="text"
                className="hud-input"
                style={{ width: '100%', fontSize: '0.78rem', padding: '6px 10px' }}
                placeholder="Model ID (e.g. gpt-6-luna, qwen/qwen3.8-flash)"
                value={newModelInput.model_id}
                onChange={(e) => setNewModelInput({ ...newModelInput, model_id: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddModelFromInput();
                  }
                }}
              />

              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={newModelInput.fast}
                  onChange={(e) => setNewModelInput({ ...newModelInput, fast: e.target.checked })}
                  style={{ accentColor: 'var(--cyan)' }}
                />
                Fast
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={newModelInput.reasoning}
                  onChange={(e) => setNewModelInput({ ...newModelInput, reasoning: e.target.checked })}
                  style={{ accentColor: 'var(--purple)' }}
                />
                Reasoning
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={newModelInput.decision}
                  onChange={(e) => setNewModelInput({ ...newModelInput, decision: e.target.checked })}
                  style={{ accentColor: 'var(--amber)' }}
                />
                Decision
              </label>

              <button
                type="button"
                onClick={handleAddModelFromInput}
                disabled={!newModelInput.model_id.trim()}
                className="hud-btn hud-btn-secondary hud-btn-sm"
                style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}
              >
                <Plus size={13} />
                Add Model
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <input
              type="checkbox"
              id="enabled-toggle"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              style={{ width: '16px', height: '16px', accentColor: 'var(--cyan)' }}
            />
            <label htmlFor="enabled-toggle" style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
              Enable this provider in Provider Gateway execution pool
            </label>
          </div>

          {/* Form Action Buttons with Test Connection */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testingConnection || !formData.base_url.trim()}
              className="hud-btn hud-btn-secondary"
              style={{
                borderColor: 'var(--cyan)',
                color: 'var(--cyan)',
                background: 'rgba(0, 229, 255, 0.08)',
              }}
            >
              <Zap size={16} className={testingConnection ? 'animate-spin' : ''} />
              {testingConnection ? 'Testing Connection & Token...' : '⚡ Test Connection & Verify Token'}
            </button>

            <button
              type="submit"
              disabled={savingProvider}
              className="hud-btn hud-btn-primary"
            >
              <Save size={16} />
              {editingProviderId ? 'Update & Sync to providers.json' : 'Save & Sync to providers.json'}
            </button>

            {editingProviderId && (
              <button
                type="button"
                onClick={handleCancelEdit}
                className="hud-btn hud-btn-secondary"
              >
                <X size={16} />
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
