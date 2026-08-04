"""Sentiment analysis agent."""

from dataclasses import dataclass


@dataclass
class SentimentResult:
    """Result from sentiment analysis."""

    ticker: str
    score: float  # -100 (bearish) to 100 (bullish)
    sources: list[str]
    key_themes: list[str]
    confidence: float  # 0-100


class SentimentAgent:
    """Analyzes social and news sentiment."""

    async def analyze(self, ticker: str) -> SentimentResult:
        """Run sentiment analysis on a ticker."""
        # TODO: Implement
        # 1. Fetch Reddit mentions (wallstreetbets, stocks, etc.)
        # 2. Fetch Twitter/X mentions
        # 3. Score sentiment per source
        # 4. Aggregate into overall sentiment score
        raise NotImplementedError
