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
    total_assets = None
    expense_ratio = None
    category = ""
    fund_family = ""

    try:
        t = yf.Ticker(ticker)
        # Primary: .info (works locally; may return empty dict on cloud IPs)
        info = t.info
        total_assets = info.get("totalAssets") or info.get("netAssets")
        expense_ratio = info.get("netExpenseRatio") or info.get("annualReportExpenseRatio")
        category = info.get("category", "")
        fund_family = info.get("fundFamily", "")
    except Exception:
        pass

    # Fallback: funds_data.fund_operations (different Yahoo endpoint, more resilient)
    if total_assets is None or expense_ratio is None:
        try:
            t = yf.Ticker(ticker)
            fo = t.funds_data.fund_operations
            if ticker in fo.columns:
                if total_assets is None:
                    raw = fo.loc["Total Net Assets", ticker]
                    if raw and not np.isnan(float(raw)):
                        # fund_operations returns value in millions of USD
                        total_assets = float(raw) * 1_000_000
                if expense_ratio is None:
                    raw_er = fo.loc["Annual Report Expense Ratio", ticker]
                    if raw_er and not np.isnan(float(raw_er)):
                        expense_ratio = float(raw_er)
            if not fund_family:
                fo2 = t.funds_data.fund_overview
                fund_family = fo2.get("family", "")
                category = fo2.get("categoryName", "")
        except Exception:
            pass

    return {
        "total_assets": total_assets,
        "expense_ratio": expense_ratio,
        "category": category,
        "fund_family": fund_family,
    }


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


@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_yield_curve() -> tuple[dict, "pd.Series | None", str]:
    """
    Fetch Japan Government Bond (JGB) yield curve data.
    Sources tried in order:
      1. FRED public CSV via pd.read_csv (no API key)
      2. Stooq via pandas_datareader
      3. Static fallback
    History fallback: 1482.T ETF price inverted as yield proxy (yfinance, always works).
    Returns: (current_yields dict, history_10y Series|None, source_label str)
    """
    import io
    import requests as _req
    from datetime import datetime, timedelta

    two_years_ago = datetime.now() - timedelta(days=730)
    approx_base   = {"3M": 0.10, "2Y": 0.40, "5Y": 0.80, "10Y": 1.50, "20Y": 2.10, "30Y": 2.30}

    def _fill_curve(yields: dict) -> dict:
        """Fill missing tenors by scaling from 10Y anchor."""
        anchor = yields.get("10Y", approx_base["10Y"])
        scale  = anchor / approx_base["10Y"] if approx_base["10Y"] > 0 else 1.0
        for k, v in approx_base.items():
            if k not in yields:
                yields[k] = round(v * scale, 3)
        return yields

    def _etf_yield_proxy(anchor_yield: float) -> "pd.Series | None":
        """
        Construct approximate 10Y JGB yield history from 1482.T ETF price.
        Uses inverse price-yield relationship:  yield(t) ≈ anchor × latest_price / price(t)
        yfinance always works on Streamlit Cloud — use as last resort for history.
        """
        try:
            hist = get_history("1482.T", "1y")
            if hist is None or hist.empty:
                return None
            prices = hist["Close"].dropna()
            if len(prices) < 5:
                return None
            latest_price = float(prices.iloc[-1])
            proxy = (anchor_yield * latest_price / prices).rename("Yield")
            # Sanity check: keep only values in realistic JGB range
            proxy = proxy[(proxy > 0) & (proxy < 5)]
            return proxy if not proxy.empty else None
        except Exception:
            return None

    yields: dict = {}
    hist10 = None

    # ── 1a. FRED via pd.read_csv (simplest, pandas handles HTTP) ─────────────
    fred_map = {
        "3M":  "IR3TBB01JPM156N",
        "10Y": "IRLTLT01JPM156N",
    }
    for tenor, series_id in fred_map.items():
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            df = pd.read_csv(url, na_values=".")
            df.columns = ["Date", "Value"]
            df["Date"]  = pd.to_datetime(df["Date"])
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
            df = df.dropna(subset=["Value"]).set_index("Date").sort_index()
            if not df.empty:
                yields[tenor] = float(df["Value"].iloc[-1])
                if tenor == "10Y":
                    hist10 = df["Value"][df.index >= pd.Timestamp(two_years_ago)]
                    if hist10.empty:
                        hist10 = None
        except Exception:
            continue

    # ── 1b. FRED via requests if pd.read_csv failed ───────────────────────────
    if not yields:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GlobalMarketsDashboard/1.0)"}
        for tenor, series_id in fred_map.items():
            try:
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
                resp = _req.get(url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    df = pd.read_csv(io.StringIO(resp.text), na_values=".")
                    df.columns = ["Date", "Value"]
                    df["Date"]  = pd.to_datetime(df["Date"])
                    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
                    df = df.dropna(subset=["Value"]).set_index("Date").sort_index()
                    if not df.empty:
                        yields[tenor] = float(df["Value"].iloc[-1])
                        if tenor == "10Y":
                            hist10 = df["Value"][df.index >= pd.Timestamp(two_years_ago)]
                            if hist10.empty:
                                hist10 = None
            except Exception:
                continue

    if len(yields) >= 1:
        _fill_curve(yields)
        # If FRED gave snapshot but no history, build proxy from 1482.T
        if hist10 is None:
            hist10 = _etf_yield_proxy(yields.get("10Y", approx_base["10Y"]))
        src = "FRED (monthly)" if hist10 is None or "Yield" not in getattr(hist10, "name", "") else "FRED + 1482.T proxy"
        return yields, hist10, src

    # ── 2. Stooq via pandas_datareader ────────────────────────────────────────
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=400)
    stooq_syms = {"2Y": "jp2y.b", "5Y": "jp5y.b", "10Y": "jp10y.b", "20Y": "jp20y.b", "30Y": "jp30y.b"}
    try:
        import pandas_datareader.data as web
        sq_yields: dict = {}
        sq_hist10 = None
        for tenor, sym in stooq_syms.items():
            try:
                df = web.DataReader(sym, "stooq", start_dt, end_dt)
                if df is not None and not df.empty:
                    s = df["Close"].dropna()
                    if len(s) > 0:
                        v = float(s.iloc[-1])
                        if -1 < v < 20:
                            sq_yields[tenor] = v
                            if tenor == "10Y":
                                sq_hist10 = s.sort_index()
            except Exception:
                continue
        if len(sq_yields) >= 2:
            return sq_yields, sq_hist10, "Stooq (daily)"
    except Exception:
        pass

    # ── 3. Static fallback — yield curve from BOJ approx, history from 1482.T ─
    anchor = approx_base["10Y"]
    hist10 = _etf_yield_proxy(anchor)
    return approx_base.copy(), hist10, "Static (BOJ approx)"


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
