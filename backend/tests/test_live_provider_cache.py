"""
tests/test_live_provider_cache.py — Local parquet bar cache for LiveProvider.

Covers the local bar cache: the first get_bars()
call writes {cache_dir}/bars_{interval}.parquet, and subsequent calls read
from disk and only fetch the recent incremental window (no full-history
re-download). No real network calls are made — yfinance is stubbed out.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from providers.live_provider import LiveProvider


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _fake_download(symbols, start_str, end_str, interval):
    """Return fake daily OHLCV bars for each symbol across the requested range.

    Mirrors the signature of LiveProvider._yf_batch_download so it can be
    used as a MagicMock side_effect.
    """
    result = {}
    for sym in symbols:
        dates = pd.bdate_range(start=start_str, end=end_str)
        if len(dates) == 0:
            continue
        df = pd.DataFrame(
            {
                "open": np.linspace(100.0, 110.0, len(dates)),
                "high": np.linspace(101.0, 111.0, len(dates)),
                "low": np.linspace(99.0, 109.0, len(dates)),
                "close": np.linspace(100.5, 110.5, len(dates)),
                "volume": np.full(len(dates), 1_000_000.0),
            },
            index=pd.DatetimeIndex(dates, name="date"),
        )
        result[sym] = df
    return result


def _make_provider(tmp_path) -> LiveProvider:
    """Return a LiveProvider wired to a temp local cache dir."""
    return LiveProvider(SimpleNamespace(cache_dir=str(tmp_path)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLiveProviderLocalCache:
    def test_first_call_writes_parquet_and_second_reads_from_disk(self, tmp_path):
        """(a)(b)(c) First get_bars writes {cache_dir}/bars_1d.parquet; the second
        call reads from disk and never repeats the full-history download."""
        provider = _make_provider(tmp_path)
        cache_file = tmp_path / "bars_1d.parquet"

        # Given: yfinance download returns full history on the first run
        with mock.patch.object(
            LiveProvider, "_yf_batch_download", side_effect=_fake_download
        ) as dl:
            # When: the first get_bars() call runs
            result1 = provider.get_bars(["TEST"])

            # Then: (a) a parquet file was written under the local cache dir
            assert cache_file.exists(), "first call must persist {cache_dir}/bars_1d.parquet"
            # Then: full history was downloaded exactly once (>= 200 bars for 200MA)
            assert dl.call_count == 1
            assert len(result1["TEST"]) >= 200

        # Given: the cache is now on disk; the second run downloads nothing new
        with mock.patch.object(
            LiveProvider, "_yf_batch_download", return_value={}
        ) as dl2:
            # When: the second get_bars() call runs
            result2 = provider.get_bars(["TEST"])

            # Then: (b) data comes from the disk cache (download returned nothing)
            assert "TEST" in result2
            assert len(result2["TEST"]) == len(result1["TEST"])
            # Then: only the recent incremental window was requested, never 730 days
            start_arg = dl2.call_args.args[1]
            start_dt = datetime.strptime(start_arg, "%Y-%m-%d")
            assert (datetime.now() - start_dt).days <= 10, (
                f"expected recent incremental window, got {start_arg}"
            )

        # Then: (c) the parquet cache file still exists at the expected path
        assert cache_file.exists()

    def test_local_cache_roundtrip_reads_from_disk_without_download(self, tmp_path):
        """The cache is served straight from the parquet file on disk — no
        download method involved in the read path."""
        provider = _make_provider(tmp_path)
        cache_file = tmp_path / "bars_1d.parquet"

        bars = _fake_download(["TEST"], "2024-01-01", "2024-01-20", "1d")
        provider._save_local_cache("1d", bars)

        assert cache_file.exists()

        with mock.patch.object(
            LiveProvider, "_yf_batch_download", wraps=provider._yf_batch_download
        ) as dl:
            cached = provider._load_local_cache("1d")
            assert "TEST" in cached
            assert len(cached["TEST"]) == len(bars["TEST"])
            assert dl.call_count == 0, "reading the local cache must not download"
