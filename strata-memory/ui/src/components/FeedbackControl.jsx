import React, { useState } from 'react';
import { submitFeedback } from '../api';
import { ThumbsUp, ThumbsDown, Award, Sparkles, CheckCircle2 } from 'lucide-react';

const INITIAL_MEMORIES = [
  { id: "mem-003c", summary: "User architecture uses Neon Serverless Postgres with scale-to-zero suspend and HNSW 768-dim embeddings.", score: 8 },
  { id: "mem-004d", summary: "Project uses python 3.12 with asyncpg and FastAPI REST interface.", score: 3 },
  { id: "mem-005e", summary: "Embedding model: text-embedding-3-small (768 dimensions) with local fallback.", score: 5 },
];

export default function FeedbackControl({ namespace }) {
  const [items, setItems] = useState(INITIAL_MEMORIES);
  const [lastAction, setLastAction] = useState(null);

  const handleFeedback = async (id, delta) => {
    // Update local UI state
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, score: item.score + delta } : item))
    );

    const success = delta > 0;
    setLastAction(`Updated memory #${id}: utility score ${delta > 0 ? '+1' : '-2'}!`);

    try {
      await submitFeedback({
        memory_ids_used: [id],
        success: success,
        namespace: namespace,
      });
    } catch (err) {
      console.warn("Feedback API offline, local state updated:", err);
    }
  };

  return (
    <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-card-border gap-2">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Award className="w-5 h-5 text-indigo-400" />
            Reinforcement Learning &amp; Memory Utility Feedback
          </h2>
          <p className="text-xs text-slate-400">
            Submit positive (+1) or negative (-2) reinforcement. Memories with high utility rank higher in hybrid RRF search; low utility leads to automatic cognitive pruning.
          </p>
        </div>
      </div>

      {lastAction && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{lastAction}</span>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="bg-slate-900/60 p-4 rounded-xl border border-card-border flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="space-y-1">
              <span className="font-mono text-[10px] text-slate-500">ID: #{item.id}</span>
              <div className="text-xs font-semibold text-slate-200 leading-relaxed">{item.summary}</div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <span className="font-mono font-bold text-sm text-indigo-400 px-3 py-1 bg-slate-800 rounded-lg border border-card-border">
                {item.score >= 0 ? `+${item.score}` : item.score}
              </span>
              <button
                onClick={() => handleFeedback(item.id, 1)}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                title="Reinforce utility score (+1)"
              >
                <ThumbsUp className="w-3.5 h-3.5" /> +1
              </button>
              <button
                onClick={() => handleFeedback(item.id, -2)}
                className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                title="Penalize utility score (-2)"
              >
                <ThumbsDown className="w-3.5 h-3.5" /> -2
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
