"""
Cross-Market Regime Indicator
─────────────────────────────
Two modes:
  short — daily bars, 3-year fetch, z-score 252d, momentum 20d/60d, display 2024+
  long  — weekly bars, 7-year fetch, z-score 52w,  momentum 4w/13w,  display 2020+

Methodology:
  1. Fetch price history for 5 macro indicators
  2. Compute rolling z-score + fast/slow momentum for each
  3. Build composite risk-on score (signs aligned so +score = risk-on)
  4. Fit a 3-component GMM on full history → label regimes
  5. Return current regime, probabilities, and full history for charting
"""

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
from sklearn.mixture import GaussianMixture


# ── Indicator definitions ─────────────────────────────────────────────────────
INDICATORS = {
    "VIX":         {"tickers": ["^VIX"],        "ratio": False, "risk_on_dir": -1},
    "EEM/TLT":     {"tickers": ["EEM", "TLT"],  "ratio": True,  "risk_on_dir": +1},
    "Gold/SPX":    {"tickers": ["GLD", "SPY"],  "ratio": True,  "risk_on_dir": -1},
    "Copper/Gold": {"tickers": ["CPER", "GLD"], "ratio": True,  "risk_on_dir": +1},
    "HYG/TLT":     {"tickers": ["HYG", "TLT"],  "ratio": True,  "risk_on_dir": +1},
}

# ── Mode configs ──────────────────────────────────────────────────────────────
_CONFIGS = {
    "long": {
        "interval":      "1wk",
        "zscore_window": 52,
        "mom_fast":      4,
        "mom_slow":      13,
        "lookback_years": 7,
        "disp_start":    "2020-01-01",
        "label":         "Long-term (Weekly)",
    },
    "short": {
        "interval":      "1d",
        "zscore_window": 252,
        "mom_fast":      20,
        "mom_slow":      60,
        "lookback_years": 3,
        "disp_start":    "2024-01-01",
        "label":         "Short-term (Daily)",
    },
}


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_closes(tickers: tuple[str, ...], interval: str, lookback_years: int) -> pd.DataFrame:
    """Download adjusted close prices for a list of tickers."""
    raw = yf.download(
        list(tickers),
        period=f"{lookback_years}y",
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]] if "Close" in raw.columns else raw
    return closes.dropna(how="all")


# ── Core computation ──────────────────────────────────────────────────────────
def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mu  = series.rolling(window, min_periods=window // 2).mean()
    sig = series.rolling(window, min_periods=window // 2).std()
    return (series - mu) / sig.replace(0, np.nan)


def _momentum_score(series: pd.Series, mom_fast: int, mom_slow: int,
                    zscore_window: int) -> pd.Series:
    """Normalised momentum: fast ROC minus slow ROC, z-scored."""
    roc_fast = series.pct_change(mom_fast)
    roc_slow = series.pct_change(mom_slow)
    return _rolling_zscore(roc_fast - roc_slow, zscore_window)


def _build_indicator_series(interval: str, lookback_years: int) -> pd.DataFrame:
    """Return DataFrame with one column per indicator (raw price/ratio)."""
    all_tickers = list({t for v in INDICATORS.values() for t in v["tickers"]})
    closes = _fetch_closes(tuple(all_tickers), interval, lookback_years)
    if closes.empty:
        return pd.DataFrame()

    series = {}
    for name, cfg in INDICATORS.items():
        tks = cfg["tickers"]
        if cfg["ratio"]:
            if tks[0] not in closes.columns or tks[1] not in closes.columns:
                continue
            s = closes[tks[0]] / closes[tks[1]]
        else:
            if tks[0] not in closes.columns:
                continue
            s = closes[tks[0]]
        series[name] = s

    return pd.DataFrame(series).ffill().dropna(how="all")


def _compute_signals(raw: pd.DataFrame, zscore_window: int,
                     mom_fast: int, mom_slow: int) -> pd.DataFrame:
    z_scores   = {}
    mom_scores = {}
    composites = {}

    for name, cfg in INDICATORS.items():
        if name not in raw.columns:
            continue
        s   = raw[name]
        z   = _rolling_zscore(s, zscore_window)
        mom = _momentum_score(s, mom_fast, mom_slow, zscore_window)
        d   = cfg["risk_on_dir"]

        z_scores[name]   = z   * d
        mom_scores[name] = mom * d
        composites[name] = (z * d + mom * d) / 2

    df_z    = pd.DataFrame(z_scores)
    df_mom  = pd.DataFrame(mom_scores)
    df_comp = pd.DataFrame(composites)

    composite = df_comp.mean(axis=1)
    out = pd.DataFrame({"composite": composite})
    for col in df_z.columns:
        out[f"z_{col}"]    = df_z[col]
        out[f"mom_{col}"]  = df_mom[col]
        out[f"comp_{col}"] = df_comp[col]

    return out.dropna(subset=["composite"])


# ── GMM regime classification ─────────────────────────────────────────────────
def _fit_gmm(composite: pd.Series, n_components: int = 3) -> GaussianMixture:
    X = composite.dropna().values.reshape(-1, 1)
    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        n_init=10,
        random_state=42,
    )
    gmm.fit(X)
    return gmm


def _label_regimes(gmm: GaussianMixture) -> dict[int, str]:
    order  = np.argsort(gmm.means_.flatten())
    labels = {}
    for rank, comp_idx in enumerate(order):
        labels[comp_idx] = ["Risk-Off", "Neutral", "Risk-On"][rank]
    return labels


# ── Public API ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_regime_data(mode: str = "short") -> dict:
    """
    mode: "short" (daily, 2024+) or "long" (weekly, 2020+)

    Returns:
        regime        : str
        probabilities : dict {label: probability}
        composite_now : float
        z_scores_now  : dict {indicator: z-score}
        mom_scores_now: dict {indicator: momentum score}
        history       : pd.DataFrame (composite + regime)
        signals       : pd.DataFrame
        config        : dict (mode config used)
    """
    cfg = _CONFIGS[mode]

    raw = _build_indicator_series(cfg["interval"], cfg["lookback_years"])
    if raw.empty:
        return {}

    signals = _compute_signals(raw, cfg["zscore_window"],
                                cfg["mom_fast"], cfg["mom_slow"])
    if signals.empty or signals["composite"].dropna().empty:
        return {}

    gmm         = _fit_gmm(signals["composite"])
    label_map   = _label_regimes(gmm)
    comp_series = signals["composite"].dropna()

    X      = comp_series.values.reshape(-1, 1)
    labels = gmm.predict(X)
    probs  = gmm.predict_proba(X)

    history = pd.DataFrame({
        "date":      comp_series.index,
        "composite": comp_series.values,
        "regime":    [label_map[l] for l in labels],
    }).set_index("date")

    current_label = history["regime"].iloc[-1]
    current_probs = {label_map[i]: round(float(probs[-1, i]), 3)
                     for i in range(gmm.n_components)}
    composite_now = float(comp_series.iloc[-1])

    z_now   = {k.replace("z_", ""): float(v)
               for k in signals.columns if k.startswith("z_")
               for v in [signals[k].iloc[-1]] if not np.isnan(v)}
    mom_now = {k.replace("mom_", ""): float(v)
               for k in signals.columns if k.startswith("mom_")
               for v in [signals[k].iloc[-1]] if not np.isnan(v)}

    return {
        "regime":         current_label,
        "probabilities":  current_probs,
        "composite_now":  composite_now,
        "z_scores_now":   z_now,
        "mom_scores_now": mom_now,
        "history":        history,
        "signals":        signals,
        "config":         cfg,
    }


REGIME_COLORS = {
    "Risk-On":  "#16a34a",
    "Neutral":  "#f59e0b",
    "Risk-Off": "#dc2626",
}
