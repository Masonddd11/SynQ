# SynQ — PRD v1.0

> **Status:** Draft
> **Author:** Sisyphus (Orchestration Lead)
> **Date:** 2026-08-05
> **Target:** Solo founder, bootstrapping

---

## 1. Executive Summary

SynQ is an AI-powered swing trading analysis platform that combines three signal layers — LLM-based agents (fundamental/sentiment/news), MiroFish GraphRAG (knowledge graph ingestion), and a proprietary swing trade indicator (technical confluence) — into a single coherent trading signal. Built for swing traders who context-switch between screeners, indicators, and news sources.

**One-liner:** *AI agents reason about your stocks. Your indicator confirms the entry.*

---

## 2. Problem Statement

Swing traders face three compounding problems:

1. **Context-switching tax.** Fundamental analysis in one tool, sentiment in another, technical signals in a third. No single system synthesizes all three.
2. **Narrative blindness.** News and social sentiment are hard to quantify. Traders miss how narratives shift around a stock before price moves.
3. **Signal noise.** Technical indicators fire constantly. Without fundamental/sentiment confirmation, most signals are noise.

**How might we** give swing traders a single system that reasons across fundamentals, sentiment, and technicals — and produces one actionable signal with a confidence score?

---

## 3. Target Users

### Primary: Active Swing Traders
- Holding period: 2 days to 4 weeks
- Already use technical indicators but want fundamental/sentiment overlay
- Willing to pay $50-200/month for an edge
- Comfortable with AI tools, but not building them

### Secondary: Quant-Curious Traders
- Want to automate parts of their workflow
- Interested in backtesting and simulation
- May want API access for custom integrations

---

## 4. Product Architecture

### 4.1 Three-Layer Signal Stack

```
┌─────────────────────────────────────────────────┐
│                 CONFLUENCE LAYER                │
│          Final Signal + Confidence Score        │
└─────────────────────────────────────────────────┘
         ▲                    ▲              ▲
         │                    │              │
┌────────┴────────┐  ┌───────┴───────┐  ┌───┴────────────┐
│  LAYER 1:       │  │  LAYER 2:     │  │  LAYER 3:      │
│  Agent Analysis │  │  MiroFish     │  │  Swing         │
│                 │  │  GraphRAG     │  │  Indicator     │
│  • Fundamentals │  │  • Knowledge  │  │  • Momentum    │
│  • Sentiment    │  │    Graph      │  │  • Volume      │
│  • News         │  │  • Entity     │  │  • Structure   │
│  • Earnings     │  │    Relations  │  │  • Entry/Exit  │
└─────────────────┘  └───────────────┘  └────────────────┘
```

### 4.2 Layer 1: LLM Agent Analysis

**Architecture:** Multi-agent system with specialized agents.

| Agent | Role | Tools |
|-------|------|-------|
| **Fundamental Agent** | Analyzes financials, ratios, growth | SEC filings API, earnings data |
| **Sentiment Agent** | Scores social/news sentiment | News API, Reddit/Twitter feeds |
| **News Agent** | Tracks catalysts and events | News API, earnings calendar |
| **Risk Agent** | Identifies red flags, volatility | Options data, short interest |
| **Synthesis Agent** | Combines all inputs into thesis | Reads all agent outputs |

**Output:** Structured analysis with bull/bear thesis, key risks, sentiment score (0-100), and confidence level.

### 4.3 Layer 2: MiroFish GraphRAG

**What we use:** Only the GraphRAG and ReportAgent components — NOT the full swarm simulation.

**Why:** The swarm simulation creates consensus collapse (agents converge toward agreement, destroying independent analysis). The knowledge graph layer is valuable for extracting entity relationships from documents.

**Use cases:**
- Ingest earnings transcripts, 10-K filings, press releases
- Build entity relationship graphs (company → suppliers → competitors → market)
- Track how entity relationships change over time
- Generate structured reports from document clusters

**Integration:** Feed structured output to Layer 1 agents as context.

### 4.4 Layer 3: Swing Trade Indicator (Proprietary)

**Components:**
- Momentum composite (RSI + MACD + rate of change)
- Volume profile (accumulation/distribution)
- Structure analysis (support/resistance, trend)
- Volatility regime (ATR-based)

**Output:** Entry signal (long/short/neutral), stop loss level, take profit targets, confidence score.

**Edge:** This is the proprietary component that differentiates SynQ from competitors.

### 4.5 Confluence Engine

Combines all three layers into a final signal:

```
Final Score = (Agent Score × 0.35) + (GraphRAG Score × 0.15) + (Indicator Score × 0.50)
```

**Signal strength:**
- **Strong Buy:** Score > 75, all three layers agree
- **Buy:** Score > 60, at least two layers agree
- **Neutral:** Score 40-60, mixed signals
- **Sell:** Score < 40, at least two layers agree
- **Strong Sell:** Score < 25, all three layers agree

---

## 5. User Experience

### 5.1 Core Flow

```
1. User enters ticker (e.g., "NVDA")
2. System runs all three layers in parallel
3. Results appear in ~30-60 seconds
4. User sees:
   ├── Agent Analysis (bull/bear thesis, sentiment)
   ├── Knowledge Graph (entity relationships)
   ├── Technical Signal (entry/exit, confidence)
   └── Confluence Score (final recommendation)
5. User adds to watchlist or executes trade
```

### 5.2 Key Screens

| Screen | Purpose |
|--------|---------|
| **Dashboard** | Watchlist with confluence scores, alerts |
| **Stock Analysis** | Full three-layer analysis for one ticker |
| **Watchlist** | Tracked stocks with score changes |
| **Backtest** | Historical signal performance |
| **Settings** | API keys, notification preferences |

### 5.3 Notifications

- **Signal alerts:** When confluence score crosses threshold
- **Earnings alerts:** Before/after earnings reports
- **Narrative shifts:** When sentiment changes significantly
- **Price alerts:** Custom price levels

---

## 6. Technical Architecture

### 6.1 Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js + Tailwind | Fast development, good DX |
| Backend | FastAPI (Python) | ML/AI ecosystem, async support |
| Database | PostgreSQL + pgvector | Structured data + embeddings |
| Cache | Redis | Rate limiting, session management |
| Queue | Celery + Redis | Async agent execution |
| LLM | OpenAI/Claude/Anthropic | Primary analysis |
| GraphRAG | MiroFish (custom fork) | Knowledge graph ingestion |
| Hosting | Railway/Fly.io | Fast deployment, scaling |
| Payments | Stripe | Subscription management |

### 6.2 Data Sources

| Source | Data | Cost |
|--------|------|------|
| Alpha Vantage | Fundamentals, technicals | Free tier available |
| Polygon.io | Real-time quotes, options | $29/mo |
| NewsAPI | News aggregation | Free tier available |
| Reddit API | Social sentiment | Free |
| SEC EDGAR | Filings, 10-K, 10-Q | Free |
| Earnings Whispers | Earnings calendar | Free |

### 6.3 MiroFish Integration

**Custom fork needed:**
1. Strip social simulation layer (Twitter/Reddit agent interactions)
2. Keep GraphRAG for document ingestion
3. Keep ReportAgent for synthesis
4. Add financial document parsers (10-K, 10-Q, earnings transcripts)
5. Build API wrapper for SynQ integration

**Estimated effort:** 2-3 weeks for fork + customization

---

## 7. MVP Scope (v0.1)

### In Scope
- [ ] Single stock analysis (one ticker at a time)
- [ ] LLM agent analysis (fundamental + sentiment + news)
- [ ] MiroFish GraphRAG for document ingestion
- [ ] Basic swing trade indicator
- [ ] Confluence score calculation
- [ ] Simple dashboard with watchlist
- [ ] Email alerts for score changes
- [ ] Stripe subscription (free trial → paid)

### Out of Scope (v0.1)
- [ ] Real-time streaming data
- [ ] Backtesting engine
- [ ] Portfolio optimization
- [ ] Mobile app
- [ ] Social features
- [ ] API access for external developers
- [ ] Custom indicator configuration
- [ ] Multiple watchlists
- [ ] Advanced charting

---

## 8. Revenue Model

### Pricing Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0/mo | 5 analyses/day, basic signals |
| **Pro** | $79/mo | Unlimited analyses, alerts, backtest |
| **Elite** | $199/mo | API access, custom indicators, priority support |

### Unit Economics (Target)

| Metric | Target |
|--------|--------|
| CAC | < $100 |
| LTV | > $1,200 (12+ months) |
| Gross margin | > 70% |
| Break-even | Month 8-10 |

---

## 9. Go-to-Market

### Phase 1: Validate (Months 1-2)
- Build MVP for personal use
- Run 50+ analyses on real trades
- Track signal accuracy vs. actual outcomes
- Document results

### Phase 2: Beta (Months 3-4)
- Invite 20-50 beta users (trading communities)
- Collect feedback on signal quality
- Iterate on indicator tuning
- Build email list

### Phase 3: Launch (Months 5-6)
- Product Hunt launch
- Trading community outreach (Reddit, Twitter, Discord)
- Content marketing (signal accuracy reports)
- Referral program

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MiroFish fork complexity | Delays MVP | Start with simpler document parser, add GraphRAG later |
| Signal accuracy | No users if signals are wrong | Extensive backtesting, transparent track record |
| LLM costs | Margin erosion | Optimize prompts, use cheaper models for non-critical agents |
| Regulatory | Legal issues with financial advice | Clear disclaimers, not registered investment advisor |
| Competition | crowded market | Proprietary indicator is differentiator |

---

## 11. Success Metrics

### Product Metrics
- Signal accuracy: > 55% win rate (target)
- User retention: > 40% month-3
- NPS: > 50
- Daily active users: 100+ by month 6

### Business Metrics
- MRR: $5,000 by month 6
- MRR: $20,000 by month 12
- CAC payback: < 3 months
- LTV/CAC ratio: > 3

---

## 12. Open Questions

1. **Indicator specifics:** What exactly does the swing trade indicator measure? Need to define the exact formula.
2. **MiroFish fork:** Should we build the GraphRAG fork first, or start with a simpler document parser and add it later?
3. **Data quality:** How do we handle missing data or conflicting signals from different sources?
4. **Backtesting:** Do we need a backtesting engine in v0.1, or can we validate signals manually first?
5. **Legal:** What disclaimers are needed for a tool that provides trading signals?

---

## 13. Next Steps

1. **Validate the indicator:** Backtest the swing trade indicator on historical data to confirm edge
2. **Prototype MiroFish fork:** Test GraphRAG with financial documents
3. **Build agent pipeline:** Start with one agent (fundamental) and expand
4. **Design UI:** Create wireframes for the core analysis screen
5. **Set up infrastructure:** Railway/Fly.io, PostgreSQL, Redis

---

*This PRD is a living document. Update as decisions are made and assumptions are validated.*
