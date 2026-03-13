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
        return yields, None, "FRED (St. Louis Fed)"

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

    # ── 3. Static fallback ────────────────────────────────────────────────────
    return approx_base.copy(), None, "Static (BOJ approx)"


@st.cache_data(ttl=600, show_spinner=False)
def get_yield_curve() -> pd.DataFrame | None:
    """Fetch US Treasury yield curve data (2Y, 5Y, 10Y, 30Y)."""
    yf_symbols = {"5Y": "^FVX", "10Y": "^TNX", "30Y": "^TYX"}
    maturities  = {"2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}
    data = {}

    for label, sym in yf_symbols.items():
        q = get_quote(sym)
        if q and q["price"]:
            data[label] = q["price"]

    # 2Y from FRED (no yfinance ticker available)
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
        df2 = pd.read_csv(url, na_values=".")
        df2.columns = ["Date", "Value"]
        df2["Value"] = pd.to_numeric(df2["Value"], errors="coerce")
        df2 = df2.dropna(subset=["Value"])
        if not df2.empty:
            data["2Y"] = float(df2["Value"].iloc[-1])
    except Exception:
        pass

    if not data:
        return None

    rows = []
    for label in ["2Y", "5Y", "10Y", "30Y"]:
        if label in data:
            rows.append({"maturity": label, "years": maturities[label], "yield": data[label]})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def get_us_yield_history(tenor: str, lookback_days: int = 365) -> "pd.Series | None":
    """Fetch US Treasury yield history from FRED public CSV (no API key required)."""
    _FRED = {
        "1M": "DGS1MO", "3M": "DGS3MO",
        "2Y": "DGS2",   "5Y": "DGS5",
        "10Y": "DGS10", "30Y": "DGS30",
    }
    series_id = _FRED.get(tenor)
    if not series_id:
        return None
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        df = pd.read_csv(url, na_values=".")
        df.columns = ["Date", "Value"]
        df["Date"]  = pd.to_datetime(df["Date"])
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
        df = df.dropna(subset=["Value"]).set_index("Date").sort_index()
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
        return df["Value"][df.index >= cutoff]
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_japan_yield_history(tenor: str, lookback_days: int = 365) -> "pd.Series | None":
    """Fetch Japan Government Bond yield history from Stooq via pandas_datareader."""
    _STOOQ = {"2Y": "jp2y.b", "5Y": "jp5y.b", "10Y": "jp10y.b", "20Y": "jp20y.b", "30Y": "jp30y.b"}
    sym = _STOOQ.get(tenor)
    if not sym:
        return None
    try:
        import pandas_datareader.data as web
        end_dt   = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        df = web.DataReader(sym, "stooq", start_dt, end_dt)
        if df.empty:
            return None
        return df["Close"].dropna().sort_index()
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_fred_series(series_id: str, lookback_days: int = 365) -> "pd.Series | None":
    """Fetch any FRED series by ID as a pandas Series (no API key required)."""
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        df = pd.read_csv(url, na_values=".")
        df.columns = ["Date", "Value"]
        df["Date"]  = pd.to_datetime(df["Date"])
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
        df = df.dropna(subset=["Value"]).set_index("Date").sort_index()
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
        return df["Value"][df.index >= cutoff]
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def get_performance_summary(symbols_dict: dict, period: str = "1mo") -> pd.DataFrame:
    """
    Compute performance + flow proxy table for a symbols dict {name: ticker}.
    Downloads 1Y OHLCV in one call to cover performance (1D/5D/1M/YTD) and
    flow proxy (Flow 1D, Flow 5D) without nested cache calls.
    Flow proxy = (Volume - 20D_avg_volume) × Close × sign(Return)
    """
    rows = []
    all_syms = list(symbols_dict.values())
    ytd_start = pd.Timestamp(datetime.now().year, 1, 1)
    try:
        raw = yf.download(
            all_syms, period="1y", interval="1d",
            progress=False, auto_adjust=True,
        )
        if raw.empty:
            return pd.DataFrame()

        # yfinance 1.2 MultiIndex handling
        close_df = raw["Close"] if "Close" in raw else raw.xs("Close", axis=1, level=0)
        vol_df   = raw["Volume"] if "Volume" in raw else raw.xs("Volume", axis=1, level=0)
        if isinstance(close_df, pd.Series):
            close_df = close_df.to_frame(name=all_syms[0])
        if isinstance(vol_df, pd.Series):
            vol_df = vol_df.to_frame(name=all_syms[0])
        close_df = close_df.dropna(how="all")
        vol_df   = vol_df.dropna(how="all")

        quotes = get_bulk_quotes(all_syms)

        for name, sym in symbols_dict.items():
            try:
                q      = quotes.get(sym, {})
                price  = q.get("price")
                pct_1d = q.get("pct_change")

                if sym in close_df.columns:
                    closes = close_df[sym].dropna()
                elif len(all_syms) == 1:
                    closes = close_df.iloc[:, 0].dropna()
                else:
                    continue
                if len(closes) < 2:
                    continue

                vols = (vol_df[sym].dropna() if sym in vol_df.columns
                        else (vol_df.iloc[:, 0].dropna() if len(all_syms) == 1
                              else pd.Series(dtype=float)))

                # ── Performance ───────────────────────────────────────────────
                pct_5d  = (closes.iloc[-1] / closes.iloc[-6] - 1) * 100 if len(closes) >= 6 else None
                mo_start = closes[closes.index >= closes.index[-1] - pd.Timedelta(days=31)]
                pct_1mo = (mo_start.iloc[-1] / mo_start.iloc[0] - 1) * 100 if len(mo_start) >= 2 else None
                ytd_c   = closes[closes.index >= ytd_start]
                pct_ytd = (ytd_c.iloc[-1] / ytd_c.iloc[0] - 1) * 100 if len(ytd_c) >= 2 else None

                # ── Flow proxy (volume-based estimate) ────────────────────────
                flow_1d = flow_5d = None
                if len(vols) >= 21 and len(closes) >= 21:
                    avg20 = vols.rolling(20).mean()
                    rets  = closes.pct_change()
                    fp    = ((vols - avg20) * closes * np.sign(rets)).dropna()
                    if len(fp) >= 1:
                        flow_1d = float(fp.iloc[-1])
                    if len(fp) >= 5:
                        flow_5d = float(fp.iloc[-5:].sum())

                rows.append({
                    "Name":    name,
                    "Ticker":  sym,
                    "Price":   price,
                    "1D %":    pct_1d,
                    "Flow 1D": flow_1d,
                    "5D %":    pct_5d,
                    "Flow 5D": flow_5d,
                    "1M %":    pct_1mo,
                    "YTD %":   pct_ytd,
                    "Volume":  q.get("volume"),
                })
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Performance summary error: {e}")

    return pd.DataFrame(rows)
