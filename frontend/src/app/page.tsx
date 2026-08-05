"use client";

import { useEffect, useState } from "react";
import { api, WatchlistItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

function SignalBadge({ signal }: { signal: string | null }) {
  if (!signal) return <Badge variant="secondary">Pending</Badge>;

  const colors: Record<string, string> = {
    strong_buy: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    buy: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    neutral: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    sell: "bg-red-500/10 text-red-400 border-red-500/20",
    strong_sell: "bg-red-500/20 text-red-400 border-red-500/30",
  };

  return (
    <Badge className={colors[signal] || ""} variant="outline">
      {signal.replace("_", " ").toUpperCase()}
    </Badge>
  );
}

export default function DashboardPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.watchlist
      .list()
      .then((res) => setWatchlist(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-400 mt-1">Your swing trading overview</p>
        </div>
        <Link href="/analyze">
          <Button>
            New Analysis <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Watchlist</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{watchlist.length}</div>
            <p className="text-xs text-gray-500 mt-1">stocks tracked</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Analyses Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">2</div>
            <p className="text-xs text-gray-500 mt-1">of 5 free tier</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Active Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
            <p className="text-xs text-gray-500 mt-1">rules configured</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-gray-900 border-gray-800">
        <CardHeader>
          <CardTitle>Watchlist</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : watchlist.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">Your watchlist is empty</p>
              <Link href="/analyze">
                <Button variant="outline">Analyze your first stock</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {watchlist.map((item) => (
                <Link
                  key={item.id}
                  href={`/analyze/${item.ticker}`}
                  className="flex items-center justify-between p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-sm font-bold">
                      {item.ticker.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-medium">{item.ticker}</div>
                      <div className="text-sm text-gray-400">
                        {item.stock?.companyName || item.ticker}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {item.latestAnalysis && (
                      <SignalBadge signal={item.latestAnalysis.signal} />
                    )}
                    <ArrowRight className="w-4 h-4 text-gray-500" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
