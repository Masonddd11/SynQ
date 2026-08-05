"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Analysis } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Loader2, Plus, TrendingUp, TrendingDown, Minus } from "lucide-react";

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 70 ? "text-emerald-400" : score >= 40 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="text-center">
      <div className={`text-5xl font-bold ${color}`}>{score.toFixed(0)}</div>
      <div className="text-sm text-gray-400 mt-1">Confluence Score</div>
    </div>
  );
}

function DirectionBadge({ direction }: { direction: string }) {
  const colors: Record<string, string> = {
    long: "bg-emerald-500/20 text-emerald-400",
    short: "bg-red-500/20 text-red-400",
    neutral: "bg-gray-500/20 text-gray-400",
  };
  return (
    <Badge className={colors[direction] || ""} variant="outline">
      {direction === "long" && <TrendingUp className="w-3 h-3 mr-1" />}
      {direction === "short" && <TrendingDown className="w-3 h-3 mr-1" />}
      {direction === "neutral" && <Minus className="w-3 h-3 mr-1" />}
      {direction.toUpperCase()}
    </Badge>
  );
}

export default function AnalysisPage() {
  const params = useParams();
  const ticker = params.ticker as string;
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);

  useEffect(() => {
    api.analyses
      .getLatest(ticker)
      .then(setAnalysis)
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false));
  }, [ticker]);

  const handleAddToWatchlist = async () => {
    setAddingToWatchlist(true);
    try {
      await api.watchlist.add(ticker);
    } catch (error) {
      console.error("Failed to add to watchlist:", error);
    } finally {
      setAddingToWatchlist(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">No Analysis Found</h1>
        <p className="text-gray-400 mb-6">No completed analysis for {ticker}</p>
        <Button onClick={async () => {
          setLoading(true);
          const newAnalysis = await api.analyses.create(ticker);
          setAnalysis(newAnalysis);
          setLoading(false);
        }}>
          Run Analysis
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">{ticker}</h1>
          <p className="text-gray-400">{analysis.stock?.companyName || ticker}</p>
        </div>
        <Button onClick={handleAddToWatchlist} disabled={addingToWatchlist} variant="outline">
          <Plus className="w-4 h-4 mr-2" />
          {addingToWatchlist ? "Adding..." : "Add to Watchlist"}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-gray-900 border-gray-800 md:col-span-2">
          <CardContent className="pt-6">
            {analysis.confluenceScore !== null ? (
              <ScoreGauge score={analysis.confluenceScore} />
            ) : (
              <div className="text-center py-4 text-gray-500">Score pending...</div>
            )}
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-6">
            <div className="text-center">
              {analysis.signal && <DirectionBadge direction={analysis.signal.includes("buy") ? "long" : analysis.signal.includes("sell") ? "short" : "neutral"} />}
              <div className="text-sm text-gray-400 mt-2">Signal</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {analysis.indicatorResult?.entrySignal && (
        <Card className="bg-gray-900 border-gray-800 mb-6">
          <CardHeader>
            <CardTitle>Entry Signal</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-sm text-gray-400">Stop Loss</div>
                <div className="text-lg font-mono">${analysis.indicatorResult.entrySignal.stopLoss}</div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Take Profit 1</div>
                <div className="text-lg font-mono text-emerald-400">
                  ${analysis.indicatorResult.entrySignal.takeProfit?.[0]}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Take Profit 2</div>
                <div className="text-lg font-mono text-emerald-400">
                  ${analysis.indicatorResult.entrySignal.takeProfit?.[1]}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {analysis.agentResult?.fundamental && (
        <Card className="bg-gray-900 border-gray-800 mb-6">
          <CardHeader>
            <CardTitle>Fundamental Analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-emerald-400 mb-1">Bull Case</h3>
              <p className="text-gray-300">{analysis.agentResult.fundamental.bullCase}</p>
            </div>
            <Separator className="bg-gray-800" />
            <div>
              <h3 className="text-sm font-medium text-red-400 mb-1">Bear Case</h3>
              <p className="text-gray-300">{analysis.agentResult.fundamental.bearCase}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {analysis.agentResult?.sentiment && (
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle>Sentiment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-4">
              <div className="text-3xl font-bold">
                {analysis.agentResult.sentiment.score > 0 ? "+" : ""}
                {analysis.agentResult.sentiment.score}
              </div>
              <div className="text-sm text-gray-400">Sentiment Score</div>
            </div>
            {analysis.agentResult.sentiment.keyThemes && (
              <div className="flex flex-wrap gap-2">
                {analysis.agentResult.sentiment.keyThemes.map((theme) => (
                  <Badge key={theme} variant="secondary">{theme}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
