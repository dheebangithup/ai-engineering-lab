import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Brain,
  Wrench,
  ShieldAlert,
  Cpu,
  Sparkles,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  RotateCcw,
  Zap,
  AlertTriangle,
  Check,
  X,
  Copy,
  Terminal,
  Database,
  FileText,
} from 'lucide-react';

export function ChatView({ systemStatus, providersData }) {
  const [messages, setMessages] = useState([
    {
      id: 'greeting',
      role: 'assistant',
      content: `Good day, sir. All J.A.R.V.I.S. core subsystems are online. 

- **Decision Engine**: Active (Sub-5ms deterministic routing & Laya Decision Model)
- **Strata Memory MCP**: Synchronized (4-Pillar Episodic & Semantic memory)
- **Tools Gateway**: Sandboxed in dedicated workspace (~/.jarvis)
- **Multi-Provider LLM Gateway**: Armed with zero-downtime dynamic routing & failover

How may I assist your engineering tasks today?`,
      metadata: {
        agent_used: 'DirectAgent',
        provider_used: 'Provider Gateway',
        model_used: 'Mark VII Engine',
        classification: { complexity: 'simple', intent: 'conversation' },
      },
    },
  ]);
  const [input, setInput] = useState('');
  const [preferredProvider, setPreferredProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [pendingActionLoading, setPendingActionLoading] = useState({});
  const [copiedOutputId, setCopiedOutputId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  const toggleSteps = (msgId) => {
    setExpandedSteps((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const getToolResults = (metadata) => {
    if (!metadata) return [];
    if (Array.isArray(metadata.tool_results) && metadata.tool_results.length > 0) {
      return metadata.tool_results;
    }
    const extracted = [];
    if (Array.isArray(metadata.steps)) {
      for (const step of metadata.steps) {
        if (step.observation) {
          try {
            const parsed = typeof step.observation === 'string' ? JSON.parse(step.observation) : step.observation;
            if (parsed && (parsed.tool_id || parsed.success !== undefined || parsed.data !== undefined || parsed.permission_denied !== undefined)) {
              extracted.push({
                tool_id: parsed.tool_id || step.action_tool || 'tool',
                success: parsed.success !== false,
                data: parsed.data,
                error: parsed.error,
                permission_denied: parsed.permission_denied || false,
                arguments: step.action_args,
              });
            }
          } catch (e) {}
        }
      }
    }
    return extracted;
  };

  const handlePermissionApprove = async (actionToken, approved) => {
    if (isProcessing) return;
    setPendingActionLoading((prev) => ({ ...prev, [actionToken]: true }));
    setIsProcessing(true);

    try {
      const resp = await fetch('/v1/permissions/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'default',
          action_token: actionToken,
          approved: approved,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `⚠️ **Permission Authorization Failed**: ${err.detail || resp.statusText}`,
          },
        ]);
        return;
      }

      const data = await resp.json();
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          metadata: data,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Network Error**: Unable to complete permission authorization (${e.message}).`,
        },
      ]);
    } finally {
      setPendingActionLoading((prev) => ({ ...prev, [actionToken]: false }));
      setIsProcessing(false);
    }
  };

  const handleProviderChange = (newProvider) => {
    setPreferredProvider(newProvider);
    setSelectedModel('');
  };

  const currentProviderObj = preferredProvider && providersData?.providers
    ? providersData.providers[preferredProvider]
    : null;

  const availableModels = currentProviderObj?.models
    ? Object.keys(currentProviderObj.models)
    : [];

  const handleSend = async (queryText = input) => {
    const text = (queryText || '').trim();
    if (!text || isProcessing) return;

    setInput('');
    const userMsgId = `user-${Date.now()}`;
    const newMessages = [
      ...messages,
      {
        id: userMsgId,
        role: 'user',
        content: text,
        preferredProvider: preferredProvider || null,
        modelOverride: selectedModel || null,
      },
    ];
    setMessages(newMessages);
    setIsProcessing(true);

    try {
      const payload = {
        query: text,
        session_id: 'default',
        preferred_provider: preferredProvider || undefined,
        model_override: selectedModel || undefined,
      };

      const resp = await fetch('/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `⚠️ **Execution Error**: ${err.detail || resp.statusText || 'Failed to complete request.'}`,
          },
        ]);
        return;
      }

      const data = await resp.json();
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          metadata: data,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Network Error**: Unable to reach J.A.R.V.I.S. Core API (${e.message}). Ensure backend server is running.`,
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickPrompts = [
    'Recall from memory what you know about this workspace',
    'List all files in the current root workspace',
    'Check health and latencies of all LLM providers',
    'Write a python script in workspace to test quick sort',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top Console Bar */}
      <div
        style={{
          padding: '12px 20px',
          background: 'rgba(12, 18, 32, 0.6)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="var(--cyan)" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            Command Console
          </span>
          <span className="hud-badge cyan" style={{ marginLeft: '4px' }}>
            Sub-5ms Router
          </span>
        </div>

        {/* Execution Mode & Model Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Provider:
          </span>
          <select
            className="hud-select"
            value={preferredProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
            style={{
              padding: '4px 10px',
              fontSize: '0.78rem',
              borderColor: preferredProvider ? 'var(--cyan)' : 'var(--border-subtle)',
              color: preferredProvider ? 'var(--cyan)' : 'var(--text-main)',
            }}
          >
            <option value="">Auto (Role-Based Fallback)</option>
            {providersData &&
              Object.entries(providersData.providers || {}).map(([pid, p]) => (
                <option key={pid} value={pid} disabled={!p.enabled}>
                  {p.name} {p.enabled ? `(${pid})` : '(Disabled)'}
                </option>
              ))}
          </select>

          {/* Model Selection Option for selected Provider */}
          {preferredProvider && (
            <>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginLeft: '4px' }}>
                Model:
              </span>
              <select
                className="hud-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                style={{
                  padding: '4px 10px',
                  fontSize: '0.78rem',
                  borderColor: selectedModel ? 'var(--cyan)' : 'var(--border-subtle)',
                  color: selectedModel ? 'var(--cyan)' : 'var(--text-main)',
                  maxWidth: '240px',
                }}
              >
                <option value="">Auto (Role Default)</option>
                {availableModels.map((mId) => {
                  const mSpec = currentProviderObj?.models?.[mId];
                  const rolesStr = (mSpec?.roles || []).join(', ');
                  return (
                    <option key={mId} value={mId}>
                      {mId} {rolesStr ? `[${rolesStr}]` : ''}
                    </option>
                  );
                })}
              </select>
            </>
          )}

          {messages.length > 1 && (
            <button
              onClick={() => setMessages([messages[0]])}
              className="hud-btn hud-btn-secondary hud-btn-sm"
              title="Reset conversation"
            >
              <RotateCcw size={12} />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '12px',
              maxWidth: '90%',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {/* Avatar */}
            {msg.role !== 'user' && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(37, 99, 235, 0.3))',
                  border: '1px solid var(--cyan)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--cyan)',
                  flexShrink: 0,
                  boxShadow: '0 0 10px rgba(0, 229, 255, 0.25)',
                }}
              >
                <Bot size={18} />
              </div>
            )}

            {/* Bubble */}
            <div
              className="glass-panel"
              style={{
                padding: '16px 20px',
                background:
                  msg.role === 'user'
                    ? 'linear-gradient(135deg, rgba(0, 229, 255, 0.12), rgba(37, 99, 235, 0.18))'
                    : 'rgba(15, 23, 42, 0.75)',
                borderColor: msg.role === 'user' ? 'rgba(0, 229, 255, 0.4)' : 'var(--border-subtle)',
                borderRadius: '12px',
              }}
            >
              {/* User Target Override Tag */}
              {(msg.preferredProvider || msg.modelOverride) && (
                <div style={{ marginBottom: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {msg.preferredProvider && (
                    <span className="hud-badge purple" style={{ fontSize: '0.7rem' }}>
                      🎯 Provider: {msg.preferredProvider}
                    </span>
                  )}
                  {msg.modelOverride && (
                    <span className="hud-badge cyan" style={{ fontSize: '0.7rem' }}>
                      ⚡ Model: {msg.modelOverride}
                    </span>
                  )}
                </div>
              )}

              {/* Assistant Metadata Badges */}
              {msg.metadata && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                  {msg.metadata.classification && (
                    <>
                      <span className="hud-badge cyan">
                        Complexity: {msg.metadata.classification.complexity}
                      </span>
                      <span className="hud-badge purple">
                        Intent: {msg.metadata.classification.intent}
                      </span>
                    </>
                  )}
                  {msg.metadata.agent_used && (
                    <span className="hud-badge blue">Archetype: {msg.metadata.agent_used}</span>
                  )}
                  {msg.metadata.provider_used && (
                    <span className="hud-badge emerald">
                      LLM: {msg.metadata.provider_used}
                      {msg.metadata.model_used ? ` (${msg.metadata.model_used})` : ''}
                    </span>
                  )}
                  {msg.metadata.fallback_occurred && (
                    <span className="hud-badge amber">⚠️ Failover Fallback Active</span>
                  )}
                  {msg.metadata.execution_time_ms && (
                    <span className="hud-badge blue">{msg.metadata.execution_time_ms} ms</span>
                  )}
                </div>
              )}

              {/* Reasoning Trace Accordion */}
              {msg.metadata?.steps && msg.metadata.steps.length > 0 && (
                <div
                  style={{
                    marginBottom: '14px',
                    borderRadius: '8px',
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(0, 229, 255, 0.15)',
                    overflow: 'hidden',
                  }}
                >
                  <button
                    onClick={() => toggleSteps(msg.id)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--cyan)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Brain size={14} />
                      Reasoning Trace ({msg.metadata.steps.length} steps)
                    </span>
                    {expandedSteps[msg.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </button>

                  {expandedSteps[msg.id] && (
                    <div style={{ padding: '10px 14px', borderTop: '1px solid rgba(0, 229, 255, 0.1)' }}>
                      {msg.metadata.steps.map((st, i) => (
                        <div key={i} style={{ marginBottom: '10px', fontSize: '0.82rem' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-muted)' }}>
                            Step {st.step_number}: {st.action_tool || 'Reflection'}
                          </div>
                          {st.thought && (
                            <div style={{ color: 'var(--text-dim)', marginTop: '2px', fontStyle: 'italic' }}>
                              Thought: {st.thought}
                            </div>
                          )}
                          {st.observation && (
                            <div
                              style={{
                                marginTop: '4px',
                                padding: '6px 8px',
                                background: 'rgba(0, 0, 0, 0.5)',
                                borderRadius: '4px',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '0.76rem',
                                color: 'var(--cyan)',
                                maxHeight: '120px',
                                overflowY: 'auto',
                              }}
                            >
                              Observation: {st.observation}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tools Used Badges */}
              {msg.metadata?.tools_used && msg.metadata.tools_used.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px', flexWrap: 'wrap' }}>
                  <Wrench size={13} color="var(--cyan)" />
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Tools invoked:</span>
                  {msg.metadata.tools_used.map((t) => (
                    <span key={t} className="hud-badge cyan" style={{ fontSize: '0.68rem' }}>
                      {t}
                    </span>
                  ))}
                </div>
              )}

              {/* Tool Execution Results Section */}
              {(() => {
                const toolResults = getToolResults(msg.metadata);
                if (!toolResults || toolResults.length === 0) return null;

                return (
                  <div style={{ marginTop: '10px', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                      <Wrench size={13} color="var(--cyan)" />
                      <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Tool Execution Output ({toolResults.length})
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {toolResults.map((tr, trIdx) => {
                        const isSuccess = tr.success !== false;
                        const isPerm = tr.permission_denied;
                        const cardId = `${msg.id}-tr-${trIdx}`;
                        const isCopied = copiedOutputId === cardId;

                        return (
                          <div
                            key={trIdx}
                            style={{
                              borderRadius: '8px',
                              background: 'rgba(10, 16, 28, 0.85)',
                              border: isPerm
                                ? '1px solid rgba(245, 158, 11, 0.45)'
                                : isSuccess
                                ? '1px solid rgba(16, 185, 129, 0.35)'
                                : '1px solid rgba(244, 63, 94, 0.4)',
                              overflow: 'hidden',
                              boxShadow: isPerm
                                ? '0 0 10px rgba(245, 158, 11, 0.1)'
                                : isSuccess
                                ? '0 0 10px rgba(16, 185, 129, 0.1)'
                                : 'none',
                            }}
                          >
                            {/* Card Header */}
                            <div
                              style={{
                                padding: '7px 12px',
                                background: 'rgba(0, 0, 0, 0.3)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                flexWrap: 'wrap',
                                gap: '6px',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {tr.tool_id?.includes('memory') ? (
                                  <Database size={13} color="var(--purple)" />
                                ) : tr.tool_id?.includes('command') ? (
                                  <Terminal size={13} color="var(--amber)" />
                                ) : (
                                  <FileText size={13} color="var(--cyan)" />
                                )}
                                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-main)' }}>
                                  {tr.tool_id}
                                </span>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {isPerm ? (
                                  <span className="hud-badge amber" style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <ShieldAlert size={10} /> PERMISSION REQUIRED
                                  </span>
                                ) : isSuccess ? (
                                  <span className="hud-badge emerald" style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <CheckCircle2 size={10} /> SUCCESS
                                  </span>
                                ) : (
                                  <span className="hud-badge rose" style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <AlertTriangle size={10} /> FAILED
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Arguments if present */}
                            {tr.arguments && Object.keys(tr.arguments).length > 0 && (
                              <div style={{ padding: '6px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)', fontSize: '0.74rem' }}>
                                <span style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Arguments: </span>
                                <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>
                                  {JSON.stringify(tr.arguments)}
                                </code>
                              </div>
                            )}

                            {/* Result Payload */}
                            <div style={{ padding: '8px 12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                                  Execution Result:
                                </span>
                                {tr.data !== undefined && tr.data !== null && (
                                  <button
                                    onClick={() => {
                                      const str = typeof tr.data === 'object' ? JSON.stringify(tr.data, null, 2) : String(tr.data);
                                      navigator.clipboard?.writeText(str);
                                      setCopiedOutputId(cardId);
                                      setTimeout(() => setCopiedOutputId(null), 2000);
                                    }}
                                    style={{
                                      background: 'transparent',
                                      border: 'none',
                                      color: isCopied ? 'var(--emerald)' : 'var(--text-dim)',
                                      cursor: 'pointer',
                                      fontSize: '0.7rem',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '3px',
                                    }}
                                  >
                                    {isCopied ? <Check size={11} /> : <Copy size={11} />}
                                    {isCopied ? 'Copied' : 'Copy'}
                                  </button>
                                )}
                              </div>

                              {tr.error && (
                                <div style={{ color: 'var(--rose)', fontFamily: 'var(--font-mono)', fontSize: '0.76rem', background: 'rgba(244, 63, 94, 0.1)', padding: '6px 8px', borderRadius: '4px', marginBottom: tr.data ? '6px' : 0 }}>
                                  {tr.error}
                                </div>
                              )}

                              {tr.data !== undefined && tr.data !== null ? (
                                <pre
                                  style={{
                                    margin: 0,
                                    padding: '8px 10px',
                                    background: 'rgba(0, 0, 0, 0.45)',
                                    borderRadius: '4px',
                                    fontFamily: 'var(--font-mono)',
                                    fontSize: '0.76rem',
                                    color: isSuccess ? 'var(--emerald)' : 'var(--text-main)',
                                    overflowX: 'auto',
                                    maxHeight: '180px',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                  }}
                                >
                                  {typeof tr.data === 'object' ? JSON.stringify(tr.data, null, 2) : String(tr.data)}
                                </pre>
                              ) : !tr.error ? (
                                <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                                  Completed with no output data.
                                </span>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* Interactive Permission Authorization Card */}
              {msg.metadata?.pending_permission && (
                <div
                  style={{
                    marginTop: '12px',
                    marginBottom: '14px',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.5)',
                    boxShadow: '0 0 15px rgba(245, 158, 11, 0.15)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <ShieldAlert size={18} color="var(--amber)" />
                    <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--amber)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                      Security Authorization Required
                    </span>
                    <span className="hud-badge amber" style={{ fontSize: '0.68rem', marginLeft: 'auto' }}>
                      Tier: {(msg.metadata.pending_permission.permission_tier || 'DANGEROUS').toUpperCase()}
                    </span>
                  </div>

                  <p style={{ margin: '0 0 10px 0', fontSize: '0.84rem', color: 'var(--text-main)', lineHeight: '1.4' }}>
                    {msg.metadata.pending_permission.reason || `Action requires explicit human clearance before execution.`}
                  </p>

                  <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '8px 12px', borderRadius: '6px', marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Target Tool: <strong style={{ color: 'var(--cyan)' }}>{msg.metadata.pending_permission.tool_id}</strong>
                    </div>
                    {msg.metadata.pending_permission.arguments && Object.keys(msg.metadata.pending_permission.arguments).length > 0 && (
                      <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.76rem', color: 'var(--text-dim)', overflowX: 'auto' }}>
                        {JSON.stringify(msg.metadata.pending_permission.arguments, null, 2)}
                      </pre>
                    )}
                  </div>

                  {/* Interactive Approval Buttons */}
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => handlePermissionApprove(msg.metadata.pending_permission.action_token, true)}
                      disabled={pendingActionLoading[msg.metadata.pending_permission.action_token] || isProcessing}
                      className="hud-btn hud-btn-emerald hud-btn-sm"
                      style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Check size={14} />
                      {pendingActionLoading[msg.metadata.pending_permission.action_token] ? 'Executing...' : 'Approve & Execute'}
                    </button>

                    <button
                      onClick={() => handlePermissionApprove(msg.metadata.pending_permission.action_token, false)}
                      disabled={pendingActionLoading[msg.metadata.pending_permission.action_token] || isProcessing}
                      className="hud-btn hud-btn-secondary hud-btn-sm"
                      style={{ display: 'flex', alignItems: 'center', gap: '6px', borderColor: 'var(--rose)', color: 'var(--rose)' }}
                    >
                      <X size={14} />
                      Deny Action
                    </button>

                    <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginLeft: '6px' }}>
                      💡 Or reply <code>yes</code> / <code>no</code> in chat
                    </span>
                  </div>
                </div>
              )}

              {/* Message Content */}
              <div
                style={{
                  fontSize: '0.92rem',
                  lineHeight: '1.6',
                  color: 'var(--text-main)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {msg.content}
              </div>
            </div>

            {/* User Avatar */}
            {msg.role === 'user' && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                }}
              >
                <User size={16} />
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isProcessing && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'rgba(0, 229, 255, 0.1)',
                border: '1px solid var(--cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--cyan)',
              }}
            >
              <Cpu size={16} className="animate-spin" />
            </div>
            <div
              className="glass-panel"
              style={{
                padding: '10px 16px',
                fontSize: '0.84rem',
                color: 'var(--cyan)',
                fontStyle: 'italic',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span className="pulse-dot" />
              {preferredProvider
                ? `Directing execution to provider '${preferredProvider}'${selectedModel ? ` [model: ${selectedModel}]` : ''}...`
                : 'Routing through Decision Engine and orchestrating agents...'}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar (when idle) */}
      {!isProcessing && messages.length <= 2 && (
        <div style={{ padding: '0 24px 10px', display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {quickPrompts.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              style={{
                padding: '5px 12px',
                fontSize: '0.74rem',
                borderRadius: '16px',
                background: 'rgba(0, 229, 255, 0.06)',
                border: '1px solid rgba(0, 229, 255, 0.2)',
                color: 'var(--text-muted)',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--cyan)';
                e.currentTarget.style.color = 'var(--cyan)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.2)';
                e.currentTarget.style.color = 'var(--text-muted)';
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <div style={{ padding: '14px 24px 20px', background: 'rgba(10, 15, 26, 0.85)', borderTop: '1px solid var(--border-subtle)' }}>
        {/* Active Route Override Pill (if selected) */}
        {(preferredProvider || selectedModel) && (
          <div
            style={{
              marginBottom: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 12px',
              background: 'rgba(0, 229, 255, 0.08)',
              border: '1px solid rgba(0, 229, 255, 0.25)',
              borderRadius: '6px',
              fontSize: '0.76rem',
              color: 'var(--cyan)',
            }}
          >
            <span>
              🎯 <strong>Manual Route Active:</strong> Provider: <code>{preferredProvider}</code>
              {selectedModel ? (
                <> | Model: <code>{selectedModel}</code></>
              ) : (
                <> | Model: <code>Auto (Role Default)</code></>
              )}
            </span>
            <button
              onClick={() => {
                setPreferredProvider('');
                setSelectedModel('');
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '0.72rem',
                textDecoration: 'underline',
              }}
            >
              Clear Override (Auto)
            </button>
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <textarea
            className="hud-textarea"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Instruct J.A.R.V.I.S. (e.g., plan architecture, execute tools, test code)... (Enter to send, Shift+Enter for newline)"
            style={{ flex: 1, resize: 'none' }}
            disabled={isProcessing}
          />
          <button
            onClick={() => handleSend()}
            disabled={isProcessing || !input.trim()}
            className="hud-btn hud-btn-primary"
            style={{ height: '48px', padding: '0 20px', opacity: isProcessing || !input.trim() ? 0.5 : 1 }}
          >
            <Send size={16} />
            <span>Execute</span>
          </button>
        </div>
      </div>
    </div>
  );
}
