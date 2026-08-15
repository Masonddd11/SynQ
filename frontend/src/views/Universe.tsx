'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SymbolPicker } from '@/components/SymbolPicker';
import type { SymbolMeta } from '@/components/SymbolPicker';
import { api } from '@/lib/api';

/**
 * UniversePage — the shared symbol-restriction page (sidebar → Universe).
 *
 * The enabled symbol list persisted here is the common restricter applied to
 * every trading mode: backtesting, paper trading, and (future) live trading.
 * An empty list means "no restriction" — the agent uses the full S&P 500.
 */
export function UniversePage() {
  const [available, setAvailable] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [meta, setMeta] = useState<Record<string, SymbolMeta>>({});
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getUniverse(), api.getUniverseAvailable(), api.getUniverseMeta()])
      .then(([cfg, avail, metaData]) => {
        if (cancelled) return;
        setSelected(cfg.symbols);
        setAvailable(avail.symbols);
        setMeta(metaData);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e?.message || e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function save() {
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const res = await api.saveUniverse(selected);
      setSelected(res.symbols);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(String((e as Error)?.message || e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">Universe</h1>
        <span className="text-[11px] text-muted-foreground">
          Shared symbol restriction for all trading modes
        </span>
      </div>

      {error && (
        <div className="bg-red-soft text-red border border-red/40 rounded-none text-sm px-4 py-2">{error}</div>
      )}

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-medium">Enabled Symbols</CardTitle>
          </div>
          {selected.length === 0 ? (
            <div className="rounded-none bg-gray-100 border border-hairline px-3 py-2 text-xs">
              <span className="font-semibold text-ink">No restriction selected.</span>{' '}
              <span className="text-ink-soft">
                The agent will trade the full S&amp;P 500. Toggle symbols below or use the filter buttons to select what to restrict to.
              </span>
            </div>
          ) : (
            <div className="rounded-none bg-gray-100 border border-hairline px-3 py-2 text-xs">
              <span className="font-semibold text-ink">
                Restricting to {selected.length} symbol{selected.length !== 1 ? 's' : ''}.
              </span>{' '}
              <span className="text-ink-soft">
                The agent will only trade these symbols. Toggle to change, or clear all to go back to the full S&amp;P 500.
              </span>
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <SymbolPicker
            available={available}
            value={selected}
            onValueChange={(next) => {
              setSelected(next);
              setSaved(false);
            }}
            meta={meta}
            loading={loading}
            maxHeight="h-72"
          />

          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              onClick={save}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save Universe'}
            </button>
            {saved && <span className="text-[11px] text-muted-foreground">Saved.</span>}
            {selected.length > 0 && (
              <span className="text-[11px] text-muted-foreground">
                The agent will only trade these {selected.length} symbols.
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
