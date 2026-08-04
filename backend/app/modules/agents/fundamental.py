"""Fundamental analysis agent."""

from dataclasses import dataclass


@dataclass
class FundamentalResult:
    """Result from fundamental analysis."""

    ticker: str
    bull_case: str
    bear_case: str
    key_metrics: dict
    risk_score: float  # 0-100, higher = more risky
    confidence: float  # 0-100


class FundamentalAgent:
    """Analyzes financial fundamentals: filings, earnings, ratios."""

    async def analyze(self, ticker: str) -> FundamentalResult:
        """Run fundamental analysis on a ticker."""
        # TODO: Implement
        # 1. Fetch SEC filings (10-K, 10-Q) via EDGAR API
        # 2. Fetch earnings data
        # 3. Run LLM analysis on documents
        # 4. Extract bull/bear thesis, key metrics
        raise NotImplementedError
