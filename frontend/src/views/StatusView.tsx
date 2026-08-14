'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardAction, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { api, type SystemHealthResponse, type SystemServiceHealth, type SystemCheckResult } from '@/lib/api';

// DESIGN.md: status follows the light register — emerald/amber are the only
// foreign hues here (ok / degraded), the red signal #d8332f stays for `down`.
type StatusStyle = { variant: 'default' | 'secondary' | 'outline'; className?: string };

const STATUS_STYLE: Record<SystemServiceHealth['status'], StatusStyle> = {
  ok: { variant: 'default', className: 'bg-emerald-600 text-white' },
  degraded: { variant: 'default', className: 'bg-amber-500 text-white' },
  down: { variant: 'default' }, // bg-red text-white → #d8332f
  idle: { variant: 'secondary' },
  not_configured: { variant: 'outline' },
};

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

export function StatusView() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkState, setCheckState] = useState<Record<string, { running: boolean; result?: SystemCheckResult }>>({});

  const load = useCallback(() => {
    api
      .getSystemHealth()
      .then(setHealth)
      .catch(() => {}) // transient failure keeps last good data
      .finally(() => setLoading(false));
  }, []);

  const runCheck = useCallback(async (service: string) => {
    setCheckState((p) => ({ ...p, [service]: { running: true } }));
    try {
      const result = await api.checkSystemService(service);
      setCheckState((p) => ({ ...p, [service]: { running: false, result } }));
    } catch (e) {
      setCheckState((p) => ({
        ...p,
        [service]: {
          running: false,
          result: { service, ok: false, status: 'down', latency_ms: 0, detail: 'Check request failed', error: String(e) },
        },
      }));
    }
  }, []);

  // Poll every 5s — same gated-interval cleanup shape as SessionDetail.
  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  if (loading) return <p className="text-xs text-ink-soft">Loading...</p>;

  if (!health) {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between border-b border-hairline pb-3">
          <h1 className="module-title text-ink">SERVICES HEALTH</h1>
        </div>
        <div className="border border-hairline bg-gray-50 px-4 py-12 text-center">
          <p className="caption text-faint">SYSTEM HEALTH UNAVAILABLE</p>
          <p className="mt-1 text-xs text-faint">
            The health endpoint is not responding — services will appear here once it does.
          </p>
        </div>
      </div>
    );
  }

  const overallStyle = STATUS_STYLE[health.overall];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between border-b border-hairline pb-3">
        <h1 className="module-title text-ink">SERVICES HEALTH</h1>
        <Badge variant={overallStyle.variant} className={overallStyle.className}>
          {health.overall.toUpperCase()}
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {health.services.map((service) => {
          const style = STATUS_STYLE[service.status];
          const ck = checkState[service.name];
          return (
            <Card key={service.name} size="sm">
              <CardHeader>
                <CardTitle>{service.name}</CardTitle>
                <CardAction>
                  <Badge variant={style.variant} className={style.className}>
                    {service.status.replace('_', ' ').toUpperCase()}
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent>
                <p className="caption text-ink-soft">{service.detail}</p>
                <div className="mt-2 flex items-center gap-2">
                  <button
                    className="border border-hairline bg-gray-100 px-2 py-1 text-[10px] font-bold text-ink hover:bg-gray-200 disabled:opacity-50"
                    onClick={() => runCheck(service.name)}
                    disabled={ck?.running}
                  >
                    {ck?.running ? 'Checking…' : 'RUN CHECK'}
                  </button>
                  {ck?.running && (
                    <span className="js-pulse h-1.5 w-1.5 shrink-0 bg-red" aria-hidden />
                  )}
                  {ck?.result && (
                    <span className="flex min-w-0 items-center gap-1.5 text-[10px]">
                      <Badge
                        variant={ck.result.ok ? 'default' : 'outline'}
                        className={ck.result.ok ? 'bg-emerald-600 text-white' : 'bg-red text-white'}
                      >
                        {ck.result.ok ? 'PASS' : 'FAIL'}
                      </Badge>
                      <span className="font-mono text-faint">{ck.result.latency_ms}ms</span>
                      <span className="truncate text-faint" title={ck.result.detail}>
                        {ck.result.detail}
                      </span>
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="mt-4 border-t border-hairline pt-2">
        <p className="caption text-faint">
          LAST UPDATED <span className="font-mono">{formatTimestamp(health.timestamp)}</span>
        </p>
      </div>
    </div>
  );
}
