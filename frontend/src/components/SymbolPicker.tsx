'use client';

import { useMemo, useState } from 'react';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { parseSymbols } from '@/lib/universe';

export interface SymbolMeta {
  sector?: string;
  marketCapBucket?: string | null;
}

/**
 * SymbolPicker — a checklist of available symbols with per-symbol enable/disable.
 *
 * Controlled + presentational: the parent owns the enabled list (`value`) and
 * persists it. Renders per DESIGN.md (dense mosaic, hairline borders, mono
 * tickers, one utility-red signal, square corners).
 *
 * The checklist always shows ALL enabled symbols as ON rows — even custom
 * symbols not in `available` — so the on/off state never desyncs.
 *
 * Filter chips narrow the visible list to a sector or cap bucket.
 * Batch actions ("select all in filter", "clear all") operate on the
 * currently-visible set.
 */
export function SymbolPicker({
  available,
  value,
  onValueChange,
  meta,
  loading = false,
  disabled = false,
  maxHeight = 'h-64',
}: {
  available: string[];
  value: string[];
  onValueChange: (next: string[]) => void;
  meta?: Record<string, SymbolMeta>;
  loading?: boolean;
  disabled?: boolean;
  maxHeight?: string;
}) {
  const [query, setQuery] = useState('');
  const [customInput, setCustomInput] = useState('');
  const [activeSector, setActiveSector] = useState<string | null>(null);
  const [activeCapBucket, setActiveCapBucket] = useState<string | null>(null);

  const selectedSet = useMemo(() => new Set(value), [value]);

  // Derive unique sectors from meta (only for symbols in available).
  const sectors = useMemo(() => {
    if (!meta) return [];
    const s = new Set<string>();
    for (const sym of available) {
      const m = meta[sym];
      if (m?.sector && m.sector !== '') s.add(m.sector);
    }
    return [...s].sort();
  }, [meta, available]);

  const capBuckets = ['low', 'mid', 'high'] as const;
  const capBucketLabels: Record<string, string> = {
    low: 'Low (<$2B)',
    mid: 'Mid ($2B–$10B)',
    high: 'High (>$10B)',
  };

  // Apply text query + sector filter + cap filter to available.
  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    return available.filter((s) => {
      if (q && !s.includes(q)) return false;
      if (activeSector) {
        const m = meta?.[s];
        if (!m || m.sector !== activeSector) return false;
      }
      if (activeCapBucket) {
        const m = meta?.[s];
        if (!m || m.marketCapBucket !== activeCapBucket) return false;
      }
      return true;
    });
  }, [available, query, activeSector, activeCapBucket, meta]);

  const filteredSet = useMemo(() => new Set(filtered), [filtered]);

  // Desync fix: show selected symbols NOT in filtered as a separate "already
  // selected" section. This ensures custom symbols (not in available) and
  // selected symbols hidden by the current filter always appear as ON rows.
  const selectedNotInFiltered = useMemo(() => {
    return value.filter((s) => !filteredSet.has(s));
  }, [value, filteredSet]);

  const toggle = (symbol: string) => {
    if (disabled) return;
    const next = new Set(selectedSet);
    if (next.has(symbol)) next.delete(symbol);
    else next.add(symbol);
    // Order: available-selected first (in available order), then extras.
    const ordered = available.filter((s) => next.has(s));
    const extras = [...next].filter((s) => !available.includes(s));
    onValueChange([...ordered, ...extras]);
  };

  const selectAllInFilter = () => {
    if (disabled || filtered.length === 0) return;
    const next = new Set(selectedSet);
    filtered.forEach((s) => next.add(s));
    const ordered = available.filter((s) => next.has(s));
    const extras = [...next].filter((s) => !available.includes(s));
    onValueChange([...ordered, ...extras]);
  };

  const clearAllInFilter = () => {
    if (disabled || filtered.length === 0) return;
    const next = new Set(selectedSet);
    filtered.forEach((s) => next.delete(s));
    const ordered = available.filter((s) => next.has(s));
    const extras = [...next].filter((s) => !available.includes(s));
    onValueChange([...ordered, ...extras]);
  };

  const addCustom = () => {
    if (disabled) return;
    const parsed = parseSymbols(customInput);
    if (parsed.length === 0) return;
    const next = new Set(selectedSet);
    parsed.forEach((s) => next.add(s));
    const ordered = available.filter((s) => next.has(s));
    const extras = parsed.filter((s) => !available.includes(s) && next.has(s));
    onValueChange([...ordered, ...extras]);
    setCustomInput('');
  };

  const enabledCount = value.length;
  const filteredSelectedCount = filtered.filter((s) => selectedSet.has(s)).length;
  const hasFilter = activeSector !== null || activeCapBucket !== null;
  const hasTextFilter = query.trim() !== '';

  return (
    <div className="space-y-2">
      {/* ── State header + batch controls (always visible) ── */}
      <div className="flex items-center justify-between gap-2">
        <Badge variant={enabledCount > 0 ? 'default' : 'secondary'} className="text-[10px]">
          {enabledCount} enabled
          {enabledCount === 0 && ' — no restriction (full S&P 500)'}
        </Badge>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            className="px-2 py-0.5 rounded-[2px] text-[10px] font-semibold border border-primary text-primary hover:bg-primary/10 transition-colors disabled:opacity-50"
            onClick={() => available.length > 0 && onValueChange([...available])}
            disabled={disabled}
          >
            Select all
          </button>
          <button
            type="button"
            className="px-2 py-0.5 rounded-[2px] text-[10px] font-semibold border border-hairline text-ink-soft hover:bg-gray-100 transition-colors disabled:opacity-50"
            onClick={() => onValueChange([])}
            disabled={disabled}
          >
            Clear all
          </button>
        </div>
      </div>

      {/* ── Search ── */}
      <input
        className="input-field"
        placeholder="Filter symbols…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={disabled}
        aria-label="Filter symbols by name"
      />

      {/* ── Sector chips ── */}
      {sectors.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {sectors.map((sec) => (
            <button
              key={sec}
              type="button"
              className={`px-2 py-0.5 rounded-[2px] text-[10px] font-medium transition-colors border ${
                activeSector === sec
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-gray-100 text-ink-soft border-hairline hover:bg-gray-200'
              }`}
              disabled={disabled}
              onClick={() => setActiveSector(activeSector === sec ? null : sec)}
            >
              {sec}
            </button>
          ))}
        </div>
      )}

      {/* ── Market-cap chips ── */}
      <div className="flex flex-wrap gap-1">
        {capBuckets.map((bucket) => {
          const active = activeCapBucket === bucket;
          return (
            <button
              key={bucket}
              type="button"
              className={`px-2 py-0.5 rounded-[2px] text-[10px] font-medium transition-colors border ${
                active
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-gray-100 text-ink-soft border-hairline hover:bg-gray-200'
              }`}
              disabled={disabled}
              onClick={() => setActiveCapBucket(activeCapBucket === bucket ? null : bucket)}
            >
              {capBucketLabels[bucket]}
            </button>
          );
        })}
      </div>

      {/* ── Batch controls (visible when any filter is active) ── */}
      {(hasFilter || hasTextFilter) && filtered.length > 0 && (
        <div className="flex items-center gap-2 text-[11px]">
          <span className="text-muted-foreground">
            {filteredSelectedCount}/{filtered.length} in filter
          </span>
          <button
            type="button"
            className="px-2 py-0.5 rounded-[2px] text-[10px] font-semibold border border-primary text-primary hover:bg-primary/10 transition-colors disabled:opacity-50"
            disabled={disabled}
            onClick={selectAllInFilter}
          >
            Select all in filter
          </button>
          <button
            type="button"
            className="px-2 py-0.5 rounded-[2px] text-[10px] font-semibold border border-hairline text-ink-soft hover:bg-gray-100 transition-colors disabled:opacity-50"
            disabled={disabled}
            onClick={clearAllInFilter}
          >
            Clear filter
          </button>
        </div>
      )}

      {/* ── Checklist ── */}
      {loading ? (
        <div className={`${maxHeight} flex items-center justify-center border border-hairline bg-gray-50 text-[11px] text-muted-foreground`}>
          Loading universe…
        </div>
      ) : (
        <ScrollArea className={`${maxHeight} border border-hairline bg-gray-50`}>
          {/* Filtered available symbols */}
          {filtered.length === 0 && selectedNotInFiltered.length === 0 ? (
            <div className="px-2 py-3 text-[11px] text-muted-foreground">No symbols match.</div>
          ) : (
            <>
              {filtered.map((s) => (
                <div
                  key={s}
                  className="flex items-center justify-between gap-2 border-b border-hairline px-2 py-1 last:border-0"
                >
                  <span className="font-mono text-xs text-ink">{s}</span>
                  <Switch
                    size="sm"
                    checked={selectedSet.has(s)}
                    onCheckedChange={() => toggle(s)}
                    disabled={disabled}
                  />
                </div>
              ))}
              {/* Selected symbols NOT in the current filter (custom / excluded by filter) */}
              {selectedNotInFiltered.length > 0 && (
                <>
                  <div className="px-2 py-0.5 text-[9px] font-semibold text-muted-foreground border-b border-hairline bg-gray-100">
                    Also selected ({selectedNotInFiltered.length})
                  </div>
                  {selectedNotInFiltered.map((s) => (
                    <div
                      key={`sel-${s}`}
                      className="flex items-center justify-between gap-2 border-b border-hairline px-2 py-1 last:border-0"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs text-ink">{s}</span>
                        {!available.includes(s) && (
                          <Badge variant="secondary" className="text-[8px] px-1 py-0 h-3.5">custom</Badge>
                        )}
                      </div>
                      <Switch
                        size="sm"
                        checked={true}
                        onCheckedChange={() => toggle(s)}
                        disabled={disabled}
                      />
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </ScrollArea>
      )}

      {/* ── Add custom symbol ── */}
      <div className="flex items-center gap-2">
        <input
          className="input-field"
          placeholder="Add symbol (e.g. IREN)"
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addCustom();
            }
          }}
          disabled={disabled}
          aria-label="Add a custom symbol"
        />
        <button
          type="button"
          className="px-2.5 py-1.5 rounded-md text-[11px] font-medium bg-secondary text-secondary-foreground hover:bg-accent transition-colors disabled:opacity-50"
          onClick={addCustom}
          disabled={disabled || parseSymbols(customInput).length === 0}
        >
          Add
        </button>
      </div>
    </div>
  );
}
