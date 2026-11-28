import React from 'react';
import { Search, Calendar, Filter, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

export default function FilterPaginationBar({
  search,
  setSearch,
  timeRange,
  setTimeRange,
  status,
  setStatus,
  page,
  setPage,
  pageSize,
  setPageSize,
  total,
  totalPages,
  onRefresh,
}) {
  return (
    <div className="bg-card p-3 rounded-2xl border border-card-border shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs mb-5">
      {/* Search & Date Filter Group */}
      <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto flex-1">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search keyword, tag, or fact..."
            className="w-full bg-slate-900 border border-card-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Time Range Filter */}
        <div className="flex items-center gap-1.5 bg-slate-900 border border-card-border rounded-xl px-2.5 py-1.5 text-slate-300">
          <Calendar className="w-3.5 h-3.5 text-indigo-400" />
          <select
            value={timeRange}
            onChange={(e) => {
              setTimeRange(e.target.value);
              setPage(1);
            }}
            className="bg-transparent text-xs text-white focus:outline-none cursor-pointer"
          >
            <option value="24h" className="bg-slate-900">Last 24 Hours</option>
            <option value="7d" className="bg-slate-900">Last 7 Days</option>
            <option value="30d" className="bg-slate-900">Last 30 Days (Default)</option>
            <option value="90d" className="bg-slate-900">Last 3 Months</option>
            <option value="all" className="bg-slate-900">All Time</option>
          </select>
        </div>

        {/* Status Filter */}
        {setStatus && (
          <div className="flex items-center gap-1.5 bg-slate-900 border border-card-border rounded-xl px-2.5 py-1.5 text-slate-300">
            <Filter className="w-3.5 h-3.5 text-emerald-400" />
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="bg-transparent text-xs text-white focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900">All Statuses</option>
              <option value="active" className="bg-slate-900">Active Only</option>
              <option value="superseded" className="bg-slate-900">Superseded Only</option>
            </select>
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center gap-3 justify-between w-full md:w-auto">
        <div className="text-[11px] text-slate-400 font-mono">
          Total: <span className="text-white font-bold">{total}</span> • Page <span className="text-indigo-400 font-bold">{page}</span> of <span className="text-slate-200">{totalPages}</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(1)}
            disabled={page <= 1}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none text-slate-300 transition-all"
            title="First Page"
          >
            <ChevronsLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none text-slate-300 transition-all"
            title="Previous Page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none text-slate-300 transition-all"
            title="Next Page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setPage(totalPages)}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none text-slate-300 transition-all"
            title="Last Page"
          >
            <ChevronsRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
