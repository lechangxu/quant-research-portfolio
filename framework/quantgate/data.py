"""Data adapters: where price history comes from.

`DataAdapter` is the seam. This repo ships a Binance public-klines adapter
(no API key required); adapters for other venues/asset classes plug into
the same two-method interface without touching the framework.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
import requests

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"


class DataAdapter(ABC):
    """One method: daily close prices for a set of symbols."""

    @abstractmethod
    def daily_closes(
        self, symbols: list[str], start: str, end: str | None = None
    ) -> pd.DataFrame:
        """Return a DataFrame of daily closes, UTC-dated index, one column per symbol.

        Missing data must be NaN, never silently filled — downstream
        cross-sectional stats treat NaN as "asset not tradeable that day".
        """


class BinanceAdapter(DataAdapter):
    """USDT-M spot daily klines from Binance's public REST API.

    Results are cached as CSV under `cache_dir`; delete the cache to refetch.
    """

    def __init__(self, cache_dir: str | Path = ".cache/binance", quote: str = "USDT"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.quote = quote

    def _cache_path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol}.csv"

    def _fetch(self, symbol: str, start: str, end: str | None) -> pd.Series:
        pair = f"{symbol}{self.quote}"
        start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
        end_ms = (
            int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
            if end
            else int(time.time() * 1000)
        )
        rows: list[list] = []
        cursor = start_ms
        while cursor < end_ms:
            resp = requests.get(
                BINANCE_KLINES,
                params={
                    "symbol": pair,
                    "interval": "1d",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            rows.extend(batch)
            cursor = batch[-1][6] + 1  # last close time + 1ms
            if len(batch) < 1000:
                break
            time.sleep(0.25)  # be polite to the public API
        if not rows:
            raise ValueError(f"no klines returned for {pair}")
        idx = pd.to_datetime([r[6] for r in rows], unit="ms", utc=True)
        closes = pd.Series(
            [float(r[4]) for r in rows], index=idx, name=symbol
        ).sort_index()
        return closes[~closes.index.duplicated(keep="last")]

    def daily_closes(
        self, symbols: list[str], start: str, end: str | None = None
    ) -> pd.DataFrame:
        cols = {}
        for sym in symbols:
            cache = self._cache_path(sym)
            if cache.exists():
                s = pd.read_csv(cache, index_col=0, parse_dates=True)[sym]
                s.index = pd.to_datetime(s.index, utc=True)
            else:
                s = self._fetch(sym, start, end)
                s.to_frame().to_csv(cache)
            cols[sym] = s
        df = pd.DataFrame(cols).sort_index()
        df = df.loc[df.index >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df.loc[df.index <= pd.Timestamp(end, tz="UTC")]
        # Drop the last row if it is today's still-forming bar — the exact
        # partial-bar divergence documented in docs/01 (#2). Research code
        # uses completed bars only.
        today = pd.Timestamp.now(tz="UTC").normalize()
        if len(df) and df.index[-1] >= today:
            df = df.iloc[:-1]
        return df
