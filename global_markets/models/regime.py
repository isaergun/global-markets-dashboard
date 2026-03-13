"""
Cross-Market Regime Indicator
─────────────────────────────
Methodology:
  1. Fetch ~2 years of daily closes for 5 macro indicators
  2. Compute rolling 252-day z-score + 20D/60D momentum for each
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
# Each entry: single ticker or ratio of two tickers.
# risk_on_direction: +1 if higher value = more risk-on, -1 if inverse.
INDICATORS = {
    "VIX":         {"tickers": ["^VIX"],        "ratio": False, "risk_on_dir": -1},
    "EEM/TLT":     {"tickers": ["EEM", "TLT"],  "ratio": True,  "risk_on_dir": +1},
    "Gold/SPX":    {"tickers": ["GLD", "SPY"],  "ratio": True,  "risk_on_dir": -1},
    "Copper/Gold": {"tickers": ["CPER", "GLD"], "ratio": True,  "risk_on_dir": +1},
    "HYG/TLT":    {"tickers": ["HYG", "TLT"],  "ratio": True,  "risk_on_dir": +1},
}

ZSCORE_WINDOW  = 252   # rolling window for z-score
MOM_FAST       = 20    # fast momentum window (days)
MOM_SLOW       = 60    # slow momentum window (days)
LOOKBACK_YEARS = 3     # history to fetch


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_closes(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Download adjusted close prices for a list of tickers."""
    raw = yf.download(
        list(tickers),
        period=f"{LOOKBACK_YEARS}y",
        interval="1d",
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


def _momentum_score(series: pd.Series) -> pd.Series:
    """Normalised momentum: fast ROC minus slow ROC, z-scored."""
    roc_fast = series.pct_change(MOM_FAST)
    roc_slow = series.pct_change(MOM_SLOW)
    raw = roc_fast - roc_slow
    return _rolling_zscore(raw, ZSCORE_WINDOW)


def _build_indicator_series() -> pd.DataFrame:
    """Return DataFrame with one column per indicator (raw price/ratio)."""
    all_tickers = list({t for v in INDICATORS.values() for t in v["tickers"]})
    closes = _fetch_closes(tuple(all_tickers))
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

    return pd.DataFrame(series).dropna(how="all")


def _compute_signals(raw: pd.DataFrame) -> pd.DataFrame:
    """
    For each indicator compute z-score and momentum, then align direction so
    positive = risk-on contribution.  Returns composite and per-indicator scores.
    """
    z_scores  = {}
    mom_scores = {}
    composites = {}

    for name, cfg in INDICATORS.items():
        if name not in raw.columns:
            continue
        s   = raw[name]
        z   = _rolling_zscore(s, ZSCORE_WINDOW)
        mom = _momentum_score(s)
        d   = cfg["risk_on_dir"]

        z_scores[name]   = z   * d
        mom_scores[name] = mom * d
        composites[name] = (z * d + mom * d) / 2  # equal blend

    df_z   = pd.DataFrame(z_scores)
    df_mom = pd.DataFrame(mom_scores)
    df_comp = pd.DataFrame(composites)

    composite = df_comp.mean(axis=1)   # equal-weight across indicators

    out = pd.DataFrame({"composite": composite})
    for col in df_z.columns:
        out[f"z_{col}"]   = df_z[col]
        out[f"mom_{col}"] = df_mom[col]
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
    """
    Sort GMM components by mean and assign Risk-Off / Neutral / Risk-On labels.
    (Lowest mean = most risk-off)
    """
    order = np.argsort(gmm.means_.flatten())
    labels = {}
    names  = ["Risk-Off", "Neutral", "Risk-On"]
    for rank, comp_idx in enumerate(order):
        labels[comp_idx] = names[rank]
    return labels


# ── Public API ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_regime_data() -> dict:
    """
    Returns:
        regime        : str  — current regime label
        probabilities : dict — {label: probability}
        composite_now : float
        z_scores_now  : dict — {indicator: z-score}
        mom_scores_now: dict — {indicator: momentum score}
        history       : pd.DataFrame — full time series (composite + regime)
    """
    raw = _build_indicator_series()
    if raw.empty:
        return {}

    signals = _compute_signals(raw)
    if signals.empty or signals["composite"].dropna().empty:
        return {}

    gmm         = _fit_gmm(signals["composite"])
    label_map   = _label_regimes(gmm)
    comp_series = signals["composite"].dropna()

    X        = comp_series.values.reshape(-1, 1)
    labels   = gmm.predict(X)
    probs    = gmm.predict_proba(X)

    history = pd.DataFrame({
        "date":      comp_series.index,
        "composite": comp_series.values,
        "regime":    [label_map[l] for l in labels],
    }).set_index("date")

    # Current (last row)
    current_label = history["regime"].iloc[-1]
    current_probs = {label_map[i]: round(float(probs[-1, i]), 3)
                     for i in range(gmm.n_components)}
    composite_now = float(comp_series.iloc[-1])

    z_now   = {k.replace("z_", ""): float(signals[k].iloc[-1])
               for k in signals.columns if k.startswith("z_")}
    mom_now = {k.replace("mom_", ""): float(signals[k].iloc[-1])
               for k in signals.columns if k.startswith("mom_")}

    return {
        "regime":         current_label,
        "probabilities":  current_probs,
        "composite_now":  composite_now,
        "z_scores_now":   z_now,
        "mom_scores_now": mom_now,
        "history":        history,
        "signals":        signals,
    }


REGIME_COLORS = {
    "Risk-On":  "#16a34a",
    "Neutral":  "#f59e0b",
    "Risk-Off": "#dc2626",
}
