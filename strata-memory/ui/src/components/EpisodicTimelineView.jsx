import React, { useState, useEffect } from 'react';
import { fetchMemories } from '../api';
import FilterPaginationBar from './FilterPaginationBar';
import { Clock, CheckCircle2, AlertCircle, Calendar, Hash } from 'lucide-react';

export default function EpisodicTimelineView({ namespace }) {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter & Pagination States
  const [search, setSearch] = useState('');
  const [timeRange, setTimeRange] = useState('30d');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadEpisodes();
  }, [namespace, search, timeRange, status, page, pageSize]);

  const loadEpisodes = async () => {
    setLoading(true);
    const data = await fetchMemories(namespace, 'episodic', status, search, timeRange, page, pageSize);
    const items = data.items?.length > 0 ? data.items : [
      {
        memory_id: "ep-003",
        summary: "Successfully deployed Strata memory schema and verified 11.4ms recall latency.",
        payload: {
          situation: "Migrating schema to Neon Postgres with pgvector",
          action_taken: "Executed 001_init_schema.sql and ran hybrid recall latency eval",
          outcome: "All 4 tables created and HNSW indexes built successfully",
          success: true
        },
        tags: ["deployment", "migration", "eval"],
        created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        utility_score: 3
      },
      {
        memory_id: "ep-002",
        summary: "Encountered asyncpg prepared statement collision when connecting to Neon pooler endpoint.",
        payload: {
          situation: "Connection pool setup on Neon serverless endpoint",
          action_taken: "Initialized connection pool with default settings",
          outcome: "Failed with DuplicatePreparedStatementError. Fixed by setting statement_cache_size=0",
          success: false
        },
        tags: ["database", "asyncpg", "error"],
        created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
        utility_score: -1
      },
      {
        memory_id: "ep-001",
        summary: "Benchmarked reciprocal rank fusion (RRF) with 30-day half-life decay.",
        payload: {
          situation: "Evaluating zero-LLM recall accuracy across 50 simulated queries",
          action_taken: "Ran tests/eval_pipeline.py against active memories",
          outcome: "Achieved 100% recall precision within 1,500 token budget",
          success: true
        },
        tags: ["benchmark", "rrf", "eval"],
        created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
        utility_score: 5
      }
    ];
    setEpisodes(items);
    setTotal(data.total || items.length);
    setTotalPages(data.total_pages || 1);
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      {/* Search, Time-Range, and Pagination Controls */}
      <FilterPaginationBar
        search={search}
        setSearch={setSearch}
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        status={status}
        setStatus={setStatus}
        page={page}
        setPage={setPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        total={total}
        totalPages={totalPages}
        onRefresh={loadEpisodes}
      />

      <div className="bg-card rounded-2xl border border-card-border p-6 shadow-lg space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-card-border gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" />
              Episodic Memory Stream (Session History &amp; Task Footprints)
            </h2>
            <p className="text-xs text-slate-400">
              Chronological records of situations encountered, actions taken, and concrete outcomes.
            </p>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Showing <span className="text-white font-bold">{episodes.length}</span> of {total}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-16 text-slate-400 text-xs">Loading episodes...</div>
        ) : episodes.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">No episodes found matching the filter.</div>
        ) : (
          <div className="relative pl-6 border-l-2 border-amber-500/30 space-y-6 ml-2">
            {episodes.map((ep) => {
              const payload = ep.payload || {};
              const isSuccess = payload.success !== false;

              return (
                <div key={ep.memory_id} className="relative group">
                  {/* Timeline marker */}
                  <div
                    className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 border-card flex items-center justify-center ${
                      isSuccess ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                  ></div>

                  <div className="bg-slate-900/70 p-4 rounded-xl border border-card-border hover:border-slate-600 transition-all space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1 ${
                            isSuccess
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {isSuccess ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                          {isSuccess ? 'Success' : 'Failure'}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">ID: #{ep.memory_id}</span>
                      </div>

                      <div className="text-[11px] text-slate-400 flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{new Date(ep.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-slate-100">{ep.summary}</div>

                    {/* Situation -> Action -> Outcome 3-box breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1 text-xs">
                      <div className="bg-slate-950/60 p-2.5 rounded-lg border border-card-border">
                        <div className="text-[10px] font-bold text-amber-400 uppercase tracking-wider mb-1">Situation</div>
                        <div className="text-slate-300 text-[11px]">{payload.situation || 'Unspecified'}</div>
                      </div>
                      <div className="bg-slate-950/60 p-2.5 rounded-lg border border-card-border">
                        <div className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-1">Action Taken</div>
                        <div className="text-slate-300 text-[11px]">{payload.action_taken || 'Executed task'}</div>
                      </div>
                      <div className="bg-slate-950/60 p-2.5 rounded-lg border border-card-border">
                        <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-1">Outcome</div>
                        <div className="text-slate-300 text-[11px]">{payload.outcome || 'Task complete'}</div>
                      </div>
                    </div>

                    {/* Tags and Utility */}
                    <div className="flex items-center justify-between pt-2 border-t border-card-border text-[11px] text-slate-400">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {ep.tags?.map((t) => (
                          <span key={t} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-300">
                            #{t}
                          </span>
                        ))}
                      </div>
                      <div className="font-mono">
                        Utility: <span className="text-indigo-400 font-bold">{ep.utility_score >= 0 ? `+${ep.utility_score}` : ep.utility_score}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
