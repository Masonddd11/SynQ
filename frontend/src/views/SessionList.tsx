'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { api, type SessionSummary } from '@/lib/api';
import { formatSessionId } from '@/lib/format';

const STATUS_STYLES: Record<string, string> = {
  running: 'bg-red-soft text-red border-red/40',
  completed: 'bg-gray-100 text-ink-soft border-hairline',
  failed: 'bg-gray-100 text-faint border-hairline',
  stopped: 'bg-gray-100 text-faint border-hairline',
};

export function SessionListPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricsLoaded, setMetricsLoaded] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [stopping, setStopping] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [, setEditValue] = useState('');

  function load() {
    // Phase 1: lite (meta only) — fast
    api.listSessionsLite().then((lite) => {
      setSessions(lite);
      setLoading(false);
      // Phase 2: full (with metrics) — background
      api.listSessions().then((full) => {
        setSessions(full);
        setMetricsLoaded(true);
      });
    }).catch(() => {
      // Fallback to full load
      api.listSessions().then(setSessions).finally(() => {
        setLoading(false);
        setMetricsLoaded(true);
      });
    });
  }

  useEffect(() => { load(); }, []);

  // Poll while any session is running
  useEffect(() => {
    const hasRunning = sessions.some((s) => s.status === 'running');
    if (!hasRunning) return;
    const interval = setInterval(() => {
      api.listSessions().then(setSessions);
    }, 30000);
    return () => clearInterval(interval);
  }, [sessions]);

  async function handleStop(e: React.MouseEvent, sessionId: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Stop session "${sessionId}"?`)) return;
    setStopping(sessionId);
    try {
      await api.stopSession(sessionId);
      setSessions((prev) =>
        prev.map((s) => s.session_id === sessionId ? { ...s, status: 'stopped' } : s),
      );
    } finally {
      setStopping(null);
    }
  }

  async function handleRename(sessionId: string, newName: string) {
    const trimmed = newName.trim();
    await api.updateSessionMeta(sessionId, { display_name: trimmed });
    setSessions((prev) =>
      prev.map((s) => s.session_id === sessionId ? { ...s, display_name: trimmed || undefined } : s),
    );
    setEditing(null);
  }

  async function handleDelete(e: React.MouseEvent, sessionId: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete session "${sessionId}"?`)) return;
    setDeleting(sessionId);
    try {
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } finally {
      setDeleting(null);
    }
  }

  if (loading) {
    return <p className="text-xs text-ink-soft">Loading sessions...</p>;
  }

  // Only show backtest sessions (exclude paper/live)
  const backtestOnly = sessions.filter((s) => !s.mode || s.mode === 'backtest');

  // Sort: running first, then by session_id descending
  const sorted = [...backtestOnly].sort((a, b) => {
    if (a.status === 'running' && b.status !== 'running') return -1;
    if (b.status === 'running' && a.status !== 'running') return 1;
    return b.session_id.localeCompare(a.session_id);
  });

  function handleRefresh() {
    setLoading(true);
    setMetricsLoaded(false);
    load();
  }

  if (sorted.length === 0) {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between border-b border-hairline pb-3">
          <h1 className="module-title text-ink">BACKTEST SESSIONS</h1>
          <button
            className="border border-hairline bg-gray-100 px-3 py-1.5 text-xs font-bold text-ink hover:bg-gray-200 disabled:opacity-50"
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        {/* Honest empty module — never a fabricated result */}
        <div className="border border-hairline bg-gray-50 px-4 py-12 text-center">
          <p className="caption text-faint">NO SESSIONS YET</p>
          <p className="mt-1 text-xs text-faint">
            Run a backtest to see results here — the mosaic fills in as sessions complete.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between border-b border-hairline pb-3">
        <h1 className="module-title text-ink">BACKTEST SESSIONS</h1>
        <button
          className="border border-hairline bg-gray-100 px-3 py-1.5 text-xs font-bold text-ink hover:bg-gray-200 disabled:opacity-50"
          onClick={handleRefresh}
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Dense module mosaic — tiles pack edge-to-edge over 1px hairline gaps */}
      <div className="grid grid-cols-1 gap-px bg-gray-100 md:grid-cols-2 xl:grid-cols-[repeat(auto-fill,minmax(250px,1fr))]">
        {sorted.map((s) => {
          const isRunning = s.status === 'running';
          const isCompleted = !s.status || s.status === 'completed' || s.status === 'stopped';
          const showMetrics = isCompleted || (isRunning && s.sim_days > 0);
          const excess = (s.total_return_pct ?? 0) - (s.spy_total_return_pct ?? 0);
          const label = s.display_name || formatSessionId(s.session_id);
          // Shorten model ID for display (e.g. "us.anthropic.claude-haiku-4-5-20251001" → "haiku-4.5")
          const modelShort = s.model_id
            ? s.model_id.replace(/^.*?claude-/, '').replace(/-\d{8}$/, '').replace(/(\d+)-(\d+)$/, '$1.$2')
            : '';

          return (
            <Link
              key={s.session_id}
              href={`/sessions/${s.session_id}`}
              className={cn(
                'group relative flex flex-col border border-transparent bg-gray-50 transition-colors',
                isRunning ? 'border-red bg-red-soft/60' : 'hover:border-ink',
              )}
            >
              {/* Header tab — red text; white-on-red when live/running */}
              <div className="flex items-center justify-between gap-2 border-b border-hairline px-3 py-1.5">
                {editing === s.session_id ? (
                  <input
                    autoFocus
                    className="w-32 border border-border-strong bg-background px-1 py-0.5 font-mono text-[11px] text-ink focus:outline-none focus:ring-2 focus:ring-red"
                    defaultValue={label}
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onBlur={(e) => handleRename(s.session_id, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { handleRename(s.session_id, e.currentTarget.value); }
                      if (e.key === 'Escape') { setEditing(null); }
                    }}
                  />
                ) : isRunning ? (
                  <span className="flex min-w-0 items-center gap-1.5 bg-red px-2 py-0.5 text-white">
                    <span className="js-pulse h-1.5 w-1.5 shrink-0 bg-white" aria-hidden />
                    <span className="tab-heading truncate">{label}</span>
                  </span>
                ) : (
                  <button
                    className="tab-heading min-w-0 truncate text-left text-red"
                    onDoubleClick={(e) => {
                      e.preventDefault(); e.stopPropagation();
                      setEditing(s.session_id);
                      setEditValue(label);
                    }}
                  >
                    {label}
                  </button>
                )}
                <span className="flex shrink-0 items-center gap-1">
                  <span
                    className={cn(
                      'border px-1.5 py-px text-[9px] font-semibold tracking-wider',
                      isRunning
                        ? 'border-red/40 bg-red-soft text-red'
                        : 'border-hairline text-faint',
                    )}
                  >
                    {isRunning ? 'RUNNING' : (s.phase ?? '').toUpperCase() || 'DONE'}
                  </span>
                </span>
              </div>

              {/* Value cells */}
              <div className="flex flex-col gap-2.5 px-3 py-2.5">
                <div className="flex items-baseline justify-between gap-2">
                  <p
                    className={cn(
                      'number-hero',
                      isRunning ? 'text-red' : 'text-ink',
                    )}
                  >
                    {(s.total_return_pct ?? 0) >= 0 ? '+' : ''}{(s.total_return_pct ?? 0).toFixed(2)}%
                  </p>
                  {s.status && s.status !== 'completed' && !isRunning && (
                    <span
                      className={cn(
                        'border px-1.5 py-px text-[9px] font-semibold',
                        STATUS_STYLES[s.status] ?? 'border-hairline text-faint',
                      )}
                    >
                      {s.status}
                    </span>
                  )}
                </div>

                {showMetrics && !metricsLoaded && (
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i}>
                        <div className="h-2 w-10 bg-gray-100 animate-pulse" />
                        <div className="mt-1 h-3 w-14 bg-gray-100 animate-pulse" />
                      </div>
                    ))}
                  </div>
                )}

                {showMetrics && metricsLoaded && (
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    <div>
                      <p className="caption text-faint">VS SPY</p>
                      <p className="number-sm text-ink">{excess >= 0 ? '+' : ''}{excess.toFixed(2)}%</p>
                    </div>
                    <div>
                      <p className="caption text-faint">MAX DD</p>
                      <p className="number-sm text-ink">{(s.max_drawdown_pct ?? 0).toFixed(2)}%</p>
                    </div>
                    <div>
                      <p className="caption text-faint">SHARPE</p>
                      <p className="number-sm text-ink">{(s.sharpe_ratio ?? 0).toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="caption text-faint">POSITIONS</p>
                      <p className="number-sm text-ink">{s.final_position_count}</p>
                    </div>
                  </div>
                )}

                {/* Meta footer */}
                <div className="flex items-center justify-between gap-2 border-t border-hairline pt-1.5">
                  <p className="number-xs text-faint">
                    {s.start_date && s.end_date
                      ? `${s.start_date} ~ ${s.end_date}`
                      : 'Starting...'}
                    {s.sim_days > 0 && ` · ${s.sim_days}d`}
                  </p>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {modelShort && (
                      <span className="border border-hairline px-1 py-px text-[9px] text-faint">
                        {modelShort}
                      </span>
                    )}
                    {s.enable_playbook === false && (
                      <span className="border border-hairline px-1 py-px text-[9px] text-faint">
                        no playbook
                      </span>
                    )}
                    {s.extended_thinking === true && (
                      <span className="border border-hairline px-1 py-px text-[9px] text-faint">
                        thinking
                      </span>
                    )}
                    {isRunning ? (
                      <button
                        className="border border-hairline bg-background px-1.5 py-px text-[9px] font-semibold text-ink hover:border-red hover:text-red disabled:opacity-50"
                        onClick={(e) => handleStop(e, s.session_id)}
                        disabled={stopping === s.session_id}
                        title="Stop session"
                      >
                        {stopping === s.session_id ? 'Stopping...' : 'Stop'}
                      </button>
                    ) : (
                      <button
                        className="border border-transparent px-1.5 py-px text-[9px] font-semibold text-faint opacity-0 transition-opacity group-hover:opacity-100 hover:border-red hover:text-red"
                        onClick={(e) => handleDelete(e, s.session_id)}
                        disabled={deleting === s.session_id}
                        title="Delete session"
                      >
                        {deleting === s.session_id ? '...' : 'Delete'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
