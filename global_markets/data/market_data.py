"""
Market data fetching module using yfinance.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@st.cache_data(ttl=120, show_spinner=False)
def get_quote(symbol: str) -> dict | None:
    """Fetch current quote for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        fi = ticker.fast_info
        price = fi.last_price
        prev = fi.previous_close
        if price is None or prev is None:
            return None
        change = price - prev
        pct = change / prev * 100
        return {
            "symbol": symbol,
            "price": price,
            "prev_close": prev,
            "change": change,
            "pct_change": pct,
            "day_high": getattr(fi, "day_high", None),
            "day_low": getattr(fi, "day_low", None),
            "year_high": getattr(fi, "year_high", None),
            "year_low": getattr(fi, "year_low", None),
            "volume": getattr(fi, "last_volume", None),
        }
    except Exception as e:
        logger.debug(f"Quote error {symbol}: {e}")
        return None


@st.cache_data(ttl=120, show_spinner=False)
def get_bulk_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch quotes for multiple symbols efficiently."""
    results = {}
    if not symbols:
        return results
    try:
        data = yf.download(
            symbols,
            period="5d",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        # yfinance 1.x always returns MultiIndex columns
        close_df = data["Close"] if "Close" in data else data.xs("Close", axis=1, level=0)
        vol_df = data["Volume"] if "Volume" in data else data.xs("Volume", axis=1, level=0)

        # Normalise to DataFrame with symbol columns
        if isinstance(close_df, pd.Series):
            close_df = close_df.to_frame(name=symbols[0])
        if isinstance(vol_df, pd.Series):
            vol_df = vol_df.to_frame(name=symbols[0])

        for sym in symbols:
            try:
                if sym in close_df.columns:
                    closes = close_df[sym].dropna()
                else:
                    continue
                if len(closes) < 2:
                    continue
                price = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
                change = price - prev
                pct = change / prev * 100

                volume = vol_df[sym].dropna() if sym in vol_df.columns else pd.Series(dtype=float)

                results[sym] = {
                    "symbol": sym,
                    "price": price,
                    "prev_close": prev,
                    "change": change,
                    "pct_change": pct,
                    "volume": float(volume.iloc[-1]) if len(volume) > 0 else None,
                }
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Bulk quote error: {e}")
    return results


@st.cache_data(ttl=600, show_spinner=False)
def get_history(
    symbol: str, period: str = "3mo", interval: str = "1d"
) -> pd.DataFrame | None:
    """Fetch historical OHLCV data."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, auto_adjust=True)
        if hist.empty:
            return None
        return hist
    except Exception as e:
        logger.debug(f"History error {symbol}: {e}")
        return None


@st.cache_data(ttl=600, show_spinner=False)
def get_multi_history(
    symbols: list[str], period: str = "3mo"
) -> pd.DataFrame | None:
    """Fetch close prices for multiple symbols."""
    try:
        data = yf.download(
            symbols,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return None
        # yfinance 1.2.0 always returns MultiIndex (Metric, Ticker)
        closes = data["Close"] if "Close" in data else data.xs("Close", axis=1, level=0)
        # Normalise: always return a DataFrame with symbol-named columns
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=symbols[0])
        return closes.dropna(how="all")
    except Exception as e:
        logger.debug(f"Multi history error: {e}")
        return None


@st.cache_data(ttl=300, show_spinner=False)
def get_etf_info(ticker: str) -> dict:
    """Fetch ETF metadata: AUM, expense ratio, etc."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        # totalAssets is primary; netAssets is fallback (both represent AUM)
        total_assets = info.get("totalAssets") or info.get("netAssets")
        expense_ratio = info.get("netExpenseRatio") or info.get("annualReportExpenseRatio")
        return {
            "total_assets": total_assets,
            "expense_ratio": expense_ratio,
            "shares_outstanding": info.get("sharesOutstanding"),
            "avg_volume": info.get("averageVolume"),
            "avg_volume_10d": info.get("averageVolume10days"),
            "category": info.get("category", ""),
            "fund_family": info.get("fundFamily", ""),
        }
    except Exception:
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def compute_etf_flow_proxy(
    ticker: str, lookback_days: int = 30
) -> dict:
    """
    Estimate ETF flows using volume-price method.

    Real ETF flows = creations/redemptions of shares by Authorized Participants.
    Without institutional data, we approximate via:
      Flow Proxy = (Today Volume - Avg Volume) × Price × Sign(Price Return)
    Positive = estimated inflow pressure, Negative = outflow pressure.
    """
    try:
        hist = get_history(ticker, period="3mo")
        if hist is None or len(hist) < 5:
            return {}

        hist = hist.tail(lookback_days + 20)
        hist["avg_vol_20d"] = hist["Volume"].rolling(20).mean()
        hist["vol_excess"] = hist["Volume"] - hist["avg_vol_20d"]
        hist["price_ret"] = hist["Close"].pct_change()
        hist["flow_proxy"] = (
            hist["vol_excess"] * hist["Close"] * np.sign(hist["price_ret"])
        )

        recent = hist.tail(lookback_days)
        flow_5d = hist.tail(5)["flow_proxy"].sum()
        flow_1mo = recent["flow_proxy"].sum()

        latest = hist.iloc[-1]
        current_price = latest["Close"]
        current_vol = latest["Volume"]
        avg_vol = latest["avg_vol_20d"]
        rel_vol = current_vol / avg_vol if avg_vol > 0 else 1.0

        # Performance
        perf_1d = hist["Close"].pct_change().iloc[-1] * 100
        perf_5d = (hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) * 100 if len(hist) >= 6 else None
        perf_1mo = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100

        # YTD
        ytd_hist = get_history(ticker, period="ytd")
        perf_ytd = None
        if ytd_hist is not None and not ytd_hist.empty:
            perf_ytd = (ytd_hist["Close"].iloc[-1] / ytd_hist["Close"].iloc[0] - 1) * 100

        return {
            "ticker": ticker,
            "price": current_price,
            "volume": current_vol,
            "avg_vol_20d": avg_vol,
            "rel_volume": rel_vol,
            "flow_proxy_5d": flow_5d,
            "flow_proxy_1mo": flow_1mo,
            "perf_1d": perf_1d,
            "perf_5d": perf_5d,
            "perf_1mo": perf_1mo,
            "perf_ytd": perf_ytd,
            "flow_history": hist[["Close", "Volume", "flow_proxy", "avg_vol_20d"]].tail(30),
        }
    except Exception as e:
        logger.debug(f"ETF flow error {ticker}: {e}")
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def get_yield_curve() -> pd.DataFrame | None:
    """Fetch US Treasury yield curve data."""
    symbols = {
        "1M": "^IRX",
        "5Y": "^FVX",
        "10Y": "^TNX",
        "30Y": "^TYX",
    }
    data = {}
    for label, sym in symbols.items():
        q = get_quote(sym)
        if q and q["price"]:
            data[label] = q["price"]

    if not data:
        return None

    maturities = {"1M": 1/12, "5Y": 5, "10Y": 10, "30Y": 30}
    rows = []
    for label, yld in data.items():
        rows.append({"maturity": label, "years": maturities[label], "yield": yld})
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def get_performance_summary(symbols_dict: dict, period: str = "1mo") -> pd.DataFrame:
    """Compute performance table for a symbols dict {name: ticker}."""
    rows = []
    all_syms = list(symbols_dict.values())
    try:
        hist = get_multi_history(all_syms, period=period)
        if hist is None:
            return pd.DataFrame()

        quotes = get_bulk_quotes(all_syms)

        ytd_hist = get_multi_history(all_syms, period="ytd")

        for name, sym in symbols_dict.items():
            try:
                q = quotes.get(sym, {})
                price = q.get("price")
                pct_1d = q.get("pct_change")

                if sym in hist.columns:
                    closes = hist[sym].dropna()
                elif len(all_syms) == 1:
                    closes = hist.iloc[:, 0].dropna()
                else:
                    continue

                pct_5d = (closes.iloc[-1] / closes.iloc[-6] - 1) * 100 if len(closes) >= 6 else None
                pct_1mo = (closes.iloc[-1] / closes.iloc[0] - 1) * 100 if len(closes) >= 2 else None

                pct_ytd = None
                if ytd_hist is not None:
                    if sym in ytd_hist.columns:
                        yc = ytd_hist[sym].dropna()
                    elif len(all_syms) == 1:
                        yc = ytd_hist.iloc[:, 0].dropna()
                    else:
                        yc = pd.Series()
                    if len(yc) >= 2:
                        pct_ytd = (yc.iloc[-1] / yc.iloc[0] - 1) * 100

                rows.append({
                    "Name": name,
                    "Ticker": sym,
                    "Price": price,
                    "1D %": pct_1d,
                    "5D %": pct_5d,
                    "1M %": pct_1mo,
                    "YTD %": pct_ytd,
                    "Volume": q.get("volume"),
                })
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Performance summary error: {e}")

    return pd.DataFrame(rows)
