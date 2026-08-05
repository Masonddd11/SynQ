"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Loader2 } from "lucide-react";

export default function AnalyzePage() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;

    setLoading(true);
    try {
      await api.analyses.create(ticker.trim().toUpperCase());
      router.push(`/analyze/${ticker.trim().toUpperCase()}`);
    } catch (error) {
      console.error("Failed to create analysis:", error);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Analyze a Stock</CardTitle>
          <p className="text-gray-400">Enter a ticker symbol to run AI-powered analysis</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <Input
                placeholder="e.g. NVDA, AAPL, TSLA"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="pl-10 bg-gray-800 border-gray-700 text-white placeholder:text-gray-500"
                maxLength={10}
              />
            </div>
            <Button type="submit" disabled={loading || !ticker.trim()}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Analyze"}
            </Button>
          </form>
          <p className="text-xs text-gray-500 mt-4 text-center">
            Free tier: 5 analyses per day
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
