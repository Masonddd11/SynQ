"""Seed script to populate the stocks table with real stock data."""

import sys
from pathlib import Path

import supabase

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Real stock data for major companies
SEED_STOCKS = [
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "market_cap": 3_000_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 125.50,
    },
    {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3_500_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 195.20,
    },
    {
        "ticker": "TSLA",
        "company_name": "Tesla, Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "market_cap": 800_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 245.80,
    },
    {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software—Infrastructure",
        "market_cap": 3_200_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 420.72,
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "sector": "Technology",
        "industry": "Internet Content & Information",
        "market_cap": 2_100_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 175.98,
    },
    {
        "ticker": "AMZN",
        "company_name": "Amazon.com, Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
        "market_cap": 2_000_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 186.51,
    },
    {
        "ticker": "META",
        "company_name": "Meta Platforms, Inc.",
        "sector": "Technology",
        "industry": "Social Media",
        "market_cap": 1_300_000_000_000,
        "exchange": "NASDAQ",
        "is_active": True,
        "last_price": 505.32,
    },
    {
        "ticker": "JPM",
        "company_name": "JPMorgan Chase & Co.",
        "sector": "Financial Services",
        "industry": "Banks—Diversified",
        "market_cap": 600_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 205.78,
    },
    {
        "ticker": "V",
        "company_name": "Visa Inc.",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "market_cap": 550_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 279.45,
    },
    {
        "ticker": "JNJ",
        "company_name": "Johnson & Johnson",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers",
        "market_cap": 380_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 156.32,
    },
    {
        "ticker": "WMT",
        "company_name": "Walmart Inc.",
        "sector": "Consumer Defensive",
        "industry": "Discount Stores",
        "market_cap": 530_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 65.89,
    },
    {
        "ticker": "UNH",
        "company_name": "UnitedHealth Group Incorporated",
        "sector": "Healthcare",
        "industry": "Healthcare Plans",
        "market_cap": 480_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 512.45,
    },
    {
        "ticker": "MA",
        "company_name": "Mastercard Incorporated",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "market_cap": 420_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 458.67,
    },
    {
        "ticker": "PG",
        "company_name": "Procter & Gamble Company",
        "sector": "Consumer Defensive",
        "industry": "Household & Personal Products",
        "market_cap": 380_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 162.34,
    },
    {
        "ticker": "HD",
        "company_name": "The Home Depot, Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Home Improvement Retail",
        "market_cap": 350_000_000_000,
        "exchange": "NYSE",
        "is_active": True,
        "last_price": 352.78,
    },
]


def _service_client() -> supabase.Client:
    """Build a service-role client (bypasses RLS so we can upsert)."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured in .env")
    return supabase.create_client(settings.supabase_url, settings.supabase_service_key)


def seed_stocks():
    """Seed the stocks table with real stock data.

    Uses the service-role client so writes bypass the SELECT-only RLS policy
    on `stocks`; the anon client cannot insert.
    """
    client = _service_client()

    print(f"Seeding {len(SEED_STOCKS)} stocks...")

    for stock in SEED_STOCKS:
        try:
            # Upsert: insert or update on conflict (ticker is PK)
            result = client.table("stocks").upsert(stock, on_conflict="ticker").execute()
            if result.data:
                print(f"  [OK] {stock['ticker']} - {stock['company_name']}")
            else:
                print(f"  [FAIL] {stock['ticker']} - Failed to upsert")
        except Exception as e:
            print(f"  [FAIL] {stock['ticker']} - Error: {e}")

    print("\nSeeding complete!")


if __name__ == "__main__":
    seed_stocks()
