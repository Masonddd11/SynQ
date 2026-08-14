'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type SystemLogSource } from '@/lib/api';
import { Button } from '@/components/ui/button';

interface RenderedLine {
  tag: string;
  text: string;
}

const POLL_INTERVAL_MS = 3000;
const LOG_LIMIT = 50;

export function TerminalView() {
  const [lines, setLines] = useState<RenderedLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const lastCountsRef = useRef(new Map<string, number>());

  // Append-diff per source: only lines past the last seen count are new.
  // New sources append their full buffer; a shrunk buffer (rotated log file)
  // restarts from the top; sources no longer present are forgotten.
  const mergeDiffs = useCallback((sources: SystemLogSource[]): RenderedLine[] => {
    const present = new Set(sources.map((s) => s.name));
    for (const name of [...lastCountsRef.current.keys()]) {
      if (!present.has(name)) lastCountsRef.current.delete(name);
    }

    const appended: RenderedLine[] = [];
    for (const source of sources) {
      const prev = lastCountsRef.current.get(source.name);
      const start = prev == null || source.lines.length < prev ? 0 : prev;
      for (let i = start; i < source.lines.length; i++) {
        appended.push({ tag: `[${source.name}]`, text: source.lines[i] });
      }
      lastCountsRef.current.set(source.name, source.lines.length);
    }
    return appended;
  }, []);

  useEffect(() => {
    if (paused) return;
    let cancelled = false;

    function poll() {
      api
        .getSystemLog(LOG_LIMIT)
        .then((res) => {
          if (cancelled) return;
          setLoading(false);
          const appended = mergeDiffs(res.sources ?? []);
          if (appended.length > 0) setLines((prev) => [...prev, ...appended]);
        })
        .catch(() => {
          // Backend may be mid-restart (route not yet registered) —
          // keep the last data, never crash.
          if (cancelled) return;
          setLoading(false);
        });
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [paused, mergeDiffs]);

  // Auto-scroll to bottom on new output, unless paused.
  useEffect(() => {
    const panel = panelRef.current;
    if (!paused && panel) panel.scrollTop = panel.scrollHeight;
  }, [lines, paused]);

  function handleClear() {
    setLines([]);
    lastCountsRef.current.clear();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">Terminal</h1>
        <span className="relative flex h-2 w-2">
          <span className={`js-pulse absolute inline-flex h-full w-full ${paused ? 'bg-faint' : 'bg-red'}`} />
          <span className={`relative inline-flex h-2 w-2 ${paused ? 'bg-faint' : 'bg-red'}`} />
        </span>
        <span className="caption text-faint">{paused ? 'Paused' : 'Live'}</span>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => setPaused((v) => !v)}>
            {paused ? 'Resume' : 'Pause'}
          </Button>
          <Button variant="outline" size="sm" onClick={handleClear}>
            Clear
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="text-xs text-ink-soft">Loading...</p>
      ) : (
        <div
          ref={panelRef}
          className="bg-muted rounded-md p-3 h-[400px] overflow-y-auto font-mono text-[11px] leading-relaxed text-muted-foreground"
        >
          {lines.length > 0 ? (
            lines.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap break-words">
                <span className="text-red/80">{line.tag}</span>
                {line.text || '\u00A0'}
              </div>
            ))
          ) : (
            <div>No log output yet.</div>
          )}
        </div>
      )}
    </div>
  );
}
