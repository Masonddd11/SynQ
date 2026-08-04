# SynQ — Confirmed Intent

> **Date:** 2026-08-05
> **Status:** Confirmed (explicit yes)

---

## Outcome

Build an AI-powered stock analysis platform for swing traders that combines three signal layers — LLM-based agents (fundamental/sentiment/news analysis), MiroFish GraphRAG (knowledge graph ingestion for document analysis), and a proprietary swing trade indicator (technical confluence for entry/exit confirmation) — into a single coherent trading signal with a confidence score.

## User

Swing traders — starting with the founder personally, but designed as a product from day one. People who context-switch between screeners, indicators, and news sources and want one coherent system that reasons across fundamentals, sentiment, and technicals.

## Why Now

LLM agents can now autonomously reason about stocks with tools and context. The combination of agent-driven analysis + knowledge graph ingestion + a proprietary indicator is a genuine edge that didn't exist 2 years ago. The market is crowded with AI stock tools, but none combine all three layers with a proprietary technical indicator as the final confluence.

## Success

A working web/desktop product that improves the founder's own trading within 3 months, and has clear interest from other traders by month 6. Not monetizing yet at month 6 — product-market fit signal. Target: 100+ daily active users, $5K MRR by month 6.

## Constraint

Solo founder, bootstrapping. Need to ship fast and validate before raising. Timeline: 6 months to working product + traction.

## Out of Scope

- No brokerage integration (v1)
- No mobile app
- No social features
- No real-time scalping
- No portfolio optimization
- No backtesting engine (v1 — validate signals manually first)
- No API access for external developers (v1)

v1 is a web tool where you run analysis on stocks and get a cohesive trading signal.

## Key Architectural Decision

Use only MiroFish's GraphRAG and ReportAgent components. Strip the social simulation layer (Twitter/Reddit agent interactions). The swarm architecture causes consensus collapse — agents converge toward agreement, destroying independent analysis. The knowledge graph layer is valuable for extracting entity relationships from documents (earnings transcripts, 10-K filings, press releases).

## Naming

Working name: **SynQ** (Synthetic + Quantitative). Domain needs to be secured — "synq" is taken by multiple companies. Consider variations: SynQ.ai, AlphaSynq, Confluence.
