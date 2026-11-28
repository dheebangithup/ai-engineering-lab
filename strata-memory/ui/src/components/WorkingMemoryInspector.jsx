import React, { useState } from 'react';
import { Shield, ShieldAlert, Cpu, Terminal, Trash2 } from 'lucide-react';

export default function WorkingMemoryInspector({ namespace }) {
  const [messages, setMessages] = useState([
    {
      id: "wm-1",
      role: "user",
      content: "Deploy the latest Strata memory schema to the Neon cluster and test the HNSW indexes.",
      tokens: 45,
      protected: false,
    },
    {
      id: "wm-2",
      role: "tool",
      tool_name: "pgvector_index_check",
      content: '{"index_name": "idx_memories_embedding_hnsw", "status": "valid", "dimensions": 768, "ef_search": 64}',
      tokens: 320,
      protected: true,
    },
    {
      id: "wm-3",
      role: "assistant",
      content: "All HNSW vector indexes verified active on 768-dimension vectors. Ready for hybrid recall.",
      tokens: 110,
      protected: false,
    },
  ]);

  const totalTokens = messages.reduce((acc, m) => acc + m.tokens, 0);
  const maxTokens = 4000;
  const percentage = Math.min(100, (totalTokens / maxTokens) * 100);

  const handleUnprotect = (id) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, protected: false } : m))
    );
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-card-border gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            Working Memory Context Buffer
          </h2>
          <p className="text-xs text-slate-400">
            Short-term agent scratchpad. Pinned tool results are protected with <code className="text-amber-400">protected=True</code> to prevent eviction.
          </p>
        </div>

        {/* Token Budget Gauge */}
        <div className="text-right min-w-[180px]">
          <div className="text-xs font-mono font-bold text-white">
            {totalTokens} / {maxTokens} Tokens
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-1.5 border border-card-border">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${percentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {messages.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">Working memory context buffer is empty.</div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`p-4 rounded-xl border transition-all ${
                msg.protected
                  ? 'bg-amber-950/20 border-amber-500/40 shadow-sm'
                  : 'bg-slate-900/60 border-card-border'
              }`}
            >
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-card-border text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                      msg.role === 'tool'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        : msg.role === 'user'
                        ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {msg.protected ? '🛡️ Tool (Protected)' : msg.role}
                  </span>
                  {msg.tool_name && <span className="font-mono text-[11px] text-slate-400">{msg.tool_name}</span>}
                </div>

                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-slate-500">{msg.tokens} tokens</span>
                  {msg.protected && (
                    <button
                      onClick={() => handleUnprotect(msg.id)}
                      className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 transition-all font-semibold"
                    >
                      Unprotect
                    </button>
                  )}
                </div>
              </div>

              <div className="text-xs text-slate-200 font-mono leading-relaxed">{msg.content}</div>
            </div>
          ))
        )}
      </div>

      {messages.length > 0 && (
        <div className="pt-3 border-t border-card-border flex justify-end">
          <button
            onClick={handleClear}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/40 hover:text-rose-400 text-slate-400 text-xs flex items-center gap-1.5 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" /> Clear Working Memory
          </button>
        </div>
      )}
    </div>
  );
}
