const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Stock {
  ticker: string;
  companyName: string;
  sector: string | null;
  industry: string | null;
  marketCap: number | null;
  exchange: string | null;
  isActive: boolean;
  lastPrice: number | null;
}

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  publishedAt: string | null;
  sentiment: number | null;
}

export interface Analysis {
  id: string;
  ticker: string;
  stock: Stock | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  agentResult: {
    fundamental: { bullCase: string; bearCase: string; riskScore: number } | null;
    sentiment: { score: number; sources: string[]; keyThemes: string[] } | null;
    news: { recentNews: NewsItem[]; upcomingCatalysts: string[]; riskEvents: string[] } | null;
  } | null;
  indicatorResult: {
    entrySignal: { direction: string; stopLoss: number; takeProfit: number[] } | null;
  } | null;
  confluenceScore: number | null;
  signal: string | null;
  createdAt: string | null;
  completedAt: string | null;
}

export interface WatchlistItem {
  id: string;
  ticker: string;
  stock: Stock | null;
  notes: string | null;
  alertThreshold: number;
  lastAnalyzedAt: string | null;
  latestAnalysis: Analysis | null;
  createdAt: string;
  updatedAt: string;
}

export interface Alert {
  id: string;
  ticker: string;
  alertType: string;
  threshold: number | null;
  targetPrice: number | null;
  isActive: boolean;
  createdAt: string;
}

export interface Pagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch((): { detail?: string; error?: { message: string } } => ({}));
    throw new Error(error.detail || error.error?.message || 'API error');
  }
  if (res.status === 204) return null as T;
  return res.json();
}

export const api = {
  stocks: {
    list: (query?: string) =>
      apiFetch<{ data: Stock[]; pagination: Pagination }>(
        `/api/stocks${query ? `?query=${encodeURIComponent(query)}` : ''}`
      ),
    get: (ticker: string) => apiFetch<Stock>(`/api/stocks/${ticker}`),
  },
  analyses: {
    create: (ticker: string) =>
      apiFetch<Analysis>('/api/analyses', {
        method: 'POST',
        body: JSON.stringify({ ticker }),
      }),
    list: (params?: { ticker?: string; status?: string }) => {
      const qs = new URLSearchParams(params).toString();
      return apiFetch<{ data: Analysis[]; pagination: Pagination }>(`/api/analyses${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => apiFetch<Analysis>(`/api/analyses/${id}`),
    getLatest: (ticker: string) =>
      apiFetch<Analysis>(`/api/analyses/latest?ticker=${ticker}`),
  },
  watchlist: {
    list: () => apiFetch<{ data: WatchlistItem[]; pagination: Pagination }>('/api/watchlist'),
    add: (ticker: string, notes?: string) =>
      apiFetch<WatchlistItem>('/api/watchlist', {
        method: 'POST',
        body: JSON.stringify({ ticker, notes }),
      }),
    update: (id: string, data: { notes?: string; alertThreshold?: number }) =>
      apiFetch<WatchlistItem>(`/api/watchlist/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    remove: (id: string) =>
      apiFetch<null>(`/api/watchlist/${id}`, { method: 'DELETE' }),
  },
  alerts: {
    list: () => apiFetch<{ data: Alert[]; pagination: Pagination }>('/api/alerts'),
    create: (ticker: string, alertType: string, threshold?: number, targetPrice?: number) =>
      apiFetch<Alert>('/api/alerts', {
        method: 'POST',
        body: JSON.stringify({ ticker, alertType, threshold, targetPrice }),
      }),
    update: (id: string, data: { threshold?: number; isActive?: boolean }) =>
      apiFetch<Alert>(`/api/alerts/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    remove: (id: string) =>
      apiFetch<null>(`/api/alerts/${id}`, { method: 'DELETE' }),
  },
};
