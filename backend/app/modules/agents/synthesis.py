"""Synthesis agent - combines all agent outputs."""

from dataclasses import dataclass

from app.modules.agents.fundamental import FundamentalResult
from app.modules.agents.sentiment import SentimentResult
from app.modules.agents.news import NewsResult


@dataclass
class SynthesisResult:
    """Combined analysis from all agents."""

    ticker: str
    fundamental: FundamentalResult
    sentiment: SentimentResult
    news: NewsResult
    bull_case: str
    bear_case: str
    key_risks: list[str]
    agent_score: float  # 0-100
    confidence: float  # 0-100


class SynthesisAgent:
    """Combines outputs from all agents into a unified thesis."""

    async def synthesize(
        self,
        ticker: str,
        fundamental: FundamentalResult,
        sentiment: SentimentResult,
        news: NewsResult,
    ) -> SynthesisResult:
        """Combine agent results into a unified analysis."""
        # TODO: Implement
        # 1. Read all agent outputs
        # 2. Identify conflicting signals
        # 3. Generate unified bull/bear thesis
        # 4. Calculate agent_score based on confidence-weighted inputs
        raise NotImplementedError
