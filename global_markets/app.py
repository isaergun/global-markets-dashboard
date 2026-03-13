"""
Global Markets Dashboard  —  Professional Edition
Run: streamlit run global_markets/app.py
"""

import streamlit as st
import streamlit.components.v1 as stc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timezone
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Global Markets",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── local imports ──────────────────────────────────────────────────────────────
from config import (
    INDICES, YIELD_SYMBOLS, COMMODITIES, CURRENCIES,
    CRYPTO, ETF_UNIVERSE, AUTO_REFRESH_SECS,
)
from data.market_data import (
    get_quote, get_bulk_quotes, get_history, get_multi_history,
    compute_etf_flow_proxy, get_yield_curve, get_us_yield_history, get_fred_series,
    get_japan_yield_curve, get_performance_summary,
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.main { background-color: #f4f5f7 !important; }

/* ── Remove Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 4rem; max-width: 1600px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f0f0f3; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }

/* ════════════════════════════════
   HEADER
════════════════════════════════ */
.dash-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 0 24px 0;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 24px;
}
.dash-title {
    font-size: 22px;
    font-weight: 800;
    color: #1a1d2e;
    letter-spacing: -0.6px;
}
.dash-subtitle {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 3px;
    font-family: 'JetBrains Mono', monospace;
}
.market-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 11px;
    color: #16a34a;
    font-weight: 600;
}
.market-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.85); }
}

/* ════════════════════════════════
   HERO METRIC CARDS  (top bar)
════════════════════════════════ */
.hero-card {
    background: #ffffff;
    border: 1px solid #e9eaec;
    border-radius: 14px;
    padding: 16px 18px 14px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s, transform 0.15s;
}
.hero-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transform: translateY(-1px);
}
.hero-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 14px 14px 0 0;
}
.hero-card.pos::before { background: linear-gradient(90deg, #22c55e 0%, #86efac 100%); }
.hero-card.neg::before { background: linear-gradient(90deg, #ef4444 0%, #fca5a5 100%); }
.hero-card.neu::before { background: linear-gradient(90deg, #7c3aed 0%, #c4b5fd 100%); }

.hero-label {
    font-size: 10px;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 7px;
}
.hero-price {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.4px;
    line-height: 1.2;
}
.hero-change {
    font-size: 11px;
    font-weight: 600;
    margin-top: 5px;
    font-family: 'JetBrains Mono', monospace;
}
.pos { color: #16a34a; }
.neg { color: #dc2626; }
.neu { color: #7c3aed; }

/* ════════════════════════════════
   SECTION HEADERS
════════════════════════════════ */
.sec-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 28px 0 16px;
}
.sec-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #e5e7eb 0%, transparent 100%);
}
.sec-title {
    font-size: 11px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    white-space: nowrap;
}

/* ════════════════════════════════
   STAT CARDS  (small)
════════════════════════════════ */
.stat-card {
    background: #ffffff;
    border: 1px solid #e9eaec;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 4px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s, transform 0.12s;
}
.stat-card:hover {
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    transform: translateY(-1px);
}
.stat-card-sel {
    border: 2px solid #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important;
}
/* Crypto card click wrapper */
.crypto-card-wrap {
    position: relative;
    margin: 4px 0;
}
.crypto-card-wrap .stat-card {
    margin: 0;
}
.crypto-card-wrap [data-testid="stButton"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    z-index: 10;
}
.crypto-card-wrap [data-testid="stButton"] button {
    width: 100%;
    height: 100%;
    cursor: pointer;
}
.stat-label {
    font-size: 10px;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
    font-weight: 700;
}
.stat-value {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.3px;
}
.stat-delta {
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    margin-top: 4px;
}

/* ════════════════════════════════
   TABS  — pill style
════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    background-color: #ebebf0 !important;
    padding: 5px !important;
    border-radius: 12px !important;
    border: none !important;
    margin-bottom: 24px !important;
}
button[role="tab"] {
    background-color: transparent !important;
    border-radius: 9px !important;
    padding: 8px 20px !important;
    border: none !important;
    color: #6b7280 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    transition: all 0.15s !important;
    font-family: 'Inter', sans-serif !important;
}
button[role="tab"]:hover {
    color: #1a1d2e !important;
    background-color: rgba(255,255,255,0.6) !important;
}
button[role="tab"][aria-selected="true"] {
    background-color: #ffffff !important;
    color: #7c3aed !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ════════════════════════════════
   TABLES
════════════════════════════════ */
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #e9eaec !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

/* ════════════════════════════════
   SELECT / INPUT
════════════════════════════════ */
.stSelectbox > div > div {
    background: #ffffff !important;
    border-color: #e5e7eb !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}

/* ════════════════════════════════
   FOOTER
════════════════════════════════ */
.dash-footer {
    text-align: center;
    color: #d1d5db;
    font-size: 10px;
    border-top: 1px solid #e5e7eb;
    padding-top: 16px;
    margin-top: 40px;
    letter-spacing: 0.04em;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TRADINGVIEW CHARTS
# ══════════════════════════════════════════════════════════════════════════════
# Yahoo Finance → TradingView symbol mapping
_TV_SYM = {
    # Indices — CAPITALCOM CFD (free, no subscription)
    "^GSPC":     "CAPITALCOM:US500",  "^DJI":  "CAPITALCOM:US30",
    "^NDX":      "CAPITALCOM:US100",  "^IXIC": "CAPITALCOM:US100",
    "^RUT":      "FOREXCOM:US2000",   "^VIX":  "CAPITALCOM:VIX",
    "^FTSE":     "CAPITALCOM:UK100",  "^GDAXI":"CAPITALCOM:DE40",
    "^FCHI":     "CAPITALCOM:FR40",   "^STOXX50E":"CAPITALCOM:EU50",
    "FTSEMIB.MI":"CAPITALCOM:IT40",
    "^N225":     "FOREXCOM:JP225",    "^HSI":  "FOREXCOM:HK50",
    # Rates — keep TVC (these work)
    "^TNX": "TVC:US10Y",    "^TYX": "TVC:US30Y",
    "^FVX": "TVC:US05Y",    "^IRX": "TVC:US03MY",
    # Commodities — TVC (precious metals + crude) + CAPITALCOM (rest)
    "GC=F": "TVC:GOLD",              "SI=F": "TVC:SILVER",
    "PL=F": "TVC:PLATINUM",          "PA=F": "TVC:PALLADIUM",
    "CL=F": "TVC:USOIL",             "BZ=F": "TVC:UKOIL",
    "NG=F": "CAPITALCOM:NATURALGAS", "HO=F": "CAPITALCOM:HEATINGOIL",
    "RB=F": "CAPITALCOM:GASOLINE",   "HG=F": "CAPITALCOM:COPPER",
    "ALI=F":"PEPPERSTONE:ALUMINIUM",  "ZW=F": "CAPITALCOM:WHEAT",
    "ZC=F": "CAPITALCOM:CORN",        "ZS=F": "OANDA:SOYBEANS_USD",
    "KC=F": "OANDA:COFFEE_USD",       "SB=F": "OANDA:SUGAR_USD",
    "CT=F": "OANDA:COTTON_USD",
    # Crypto
    "BTC-USD":  "BINANCE:BTCUSDT",  "ETH-USD":  "BINANCE:ETHUSDT",
    "BNB-USD":  "BINANCE:BNBUSDT",  "SOL-USD":  "BINANCE:SOLUSDT",
    "XRP-USD":  "BINANCE:XRPUSDT",  "ADA-USD":  "BINANCE:ADAUSDT",
    "AVAX-USD": "BINANCE:AVAXUSDT", "DOGE-USD": "BINANCE:DOGEUSDT",
    # FX — majors
    "EURUSD=X": "FX:EURUSD",  "GBPUSD=X": "FX:GBPUSD",
    "USDJPY=X": "FX:USDJPY",  "USDCHF=X": "FX:USDCHF",
    "AUDUSD=X": "FX:AUDUSD",  "NZDUSD=X": "FX:NZDUSD",
    "USDCAD=X": "FX:USDCAD",
    # FX — emerging
    "USDCNY=X": "FX_IDC:USDCNY", "USDBRL=X": "FX_IDC:USDBRL",
    "USDINR=X": "FX_IDC:USDINR", "USDTRY=X": "FX_IDC:USDTRY",
    "USDMXN=X": "FX_IDC:USDMXN","USDKRW=X": "FX_IDC:USDKRW",
    "USDZAR=X": "FX_IDC:USDZAR","USDRUB=X": "FX_IDC:USDRUB",
    # DXY
    "DX-Y.NYB": "CAPITALCOM:DXY",
    # ETFs (select common ones)
    "SPY": "AMEX:SPY",   "QQQ": "NASDAQ:QQQ",  "IWM": "AMEX:IWM",
    "GLD": "AMEX:GLD",   "SLV": "AMEX:SLV",    "USO": "AMEX:USO",
    "IBIT": "NASDAQ:IBIT","FBTC": "NASDAQ:FBTC","ETHA": "NASDAQ:ETHA",
    # Alt Asset Managers
    "BX":   "NYSE:BX",    "BLK":  "NYSE:BLK",   "OWL":  "NYSE:OWL",
    "APO":  "NYSE:APO",   "KKR":  "NYSE:KKR",   "ARES": "NYSE:ARES",
    "CG":   "NASDAQ:CG",
    # BDCs
    "ARCC": "NASDAQ:ARCC", "OBDC": "NYSE:OBDC",  "BXSL": "NYSE:BXSL",
    "FSK":  "NYSE:FSK",    "MAIN": "NYSE:MAIN",   "HTGC": "NYSE:HTGC",
    "GBDC": "NASDAQ:GBDC",
    # Senior Loans & CLOs (NYSE Arca → AMEX in TradingView)
    "BKLN": "AMEX:BKLN", "SRLN": "AMEX:SRLN",
    "JAAA": "AMEX:JAAA", "CLOI": "AMEX:CLOI",
}

def tv_chart(yf_symbol: str, height: int = 380, interval: str = "D",
             style: str = "1") -> None:
    """
    Embed a TradingView Advanced Chart for the given Yahoo Finance symbol.
    style: "1"=candles, "2"=line, "3"=mountain/area
    """
    tv_sym = _TV_SYM.get(yf_symbol, yf_symbol)
    cid = f"tv_{abs(hash(yf_symbol))}"
    html = f"""
    <div id="{cid}" style="height:{height}px;border-radius:12px;overflow:hidden;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
      "container_id": "{cid}",
      "width":  "100%",
      "height": {height},
      "symbol": "{tv_sym}",
      "interval": "{interval}",
      "timezone": "Etc/UTC",
      "theme": "light",
      "style": "{style}",
      "locale": "en",
      "hide_side_toolbar": true,
      "allow_symbol_change": false,
      "save_image": false,
      "hide_top_toolbar": false,
      "withdateranges": true,
      "details": false
    }});
    </script>
    """
    stc.html(html, height=height + 8, scrolling=False)


_BINANCE_WS = {
    "BTC-USD": "btcusdt", "ETH-USD": "ethusdt", "BNB-USD": "bnbusdt",
    "SOL-USD": "solusdt", "XRP-USD": "xrpusdt", "ADA-USD": "adausdt",
    "AVAX-USD": "avaxusdt", "DOGE-USD": "dogeusdt",
}

def crypto_live_cards(selected_sym: str, crypto_map: dict) -> None:
    """
    Render 8 clickable crypto price cards with live Binance WebSocket prices.
    Clicking a card navigates the parent Streamlit frame to ?crypto=SYM.
    """
    streams = "/".join(
        f"{_BINANCE_WS[s]}@miniTicker"
        for s in crypto_map.values() if s in _BINANCE_WS
    )
    cards = ""
    for name, sym in crypto_map.items():
        ws_sym = _BINANCE_WS.get(sym)
        if not ws_sym:
            continue
        sel = (sym == selected_sym)
        bdr = ("2px solid #7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.12);"
               if sel else "1px solid #e9eaec;")
        cards += f"""
        <div class="cc" style="border:{bdr}" onclick="nav('{sym}')">
          <div class="cl">{name}</div>
          <div class="cp" id="p_{ws_sym}">—</div>
          <div class="cd" id="d_{ws_sym}">—</div>
        </div>"""

    html = f"""<!DOCTYPE html><html><head><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:transparent;padding:4px 2px}}
.g{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.cc{{background:#fff;border-radius:12px;padding:13px 15px;
    box-shadow:0 1px 3px rgba(0,0,0,.05);cursor:pointer;
    transition:box-shadow .15s,transform .12s;user-select:none}}
.cc:hover{{box-shadow:0 4px 10px rgba(0,0,0,.09);transform:translateY(-1px)}}
.cl{{font-size:10px;color:#9ca3af;text-transform:uppercase;
    letter-spacing:.5px;margin-bottom:5px}}
.cp{{font-size:16px;font-weight:700;color:#1a1a2e;
    letter-spacing:-.3px;margin-bottom:2px}}
.cd{{font-size:11px;font-family:monospace;color:#6b7280}}
</style></head><body>
<div class="g">{cards}</div>
<script>
function nav(sym){{
  var url=(window.parent.location.pathname||'/')+'?crypto='+sym;
  try{{window.parent.location.href=url;return;}}catch(e){{}}
  try{{window.open(url,'_top');}}catch(e){{}}
}}
var ws=new WebSocket('wss://stream.binance.com:9443/stream?streams={streams}');
ws.onmessage=function(e){{
  var d=JSON.parse(e.data).data;
  if(!d||!d.s)return;
  var s=d.s.toLowerCase();
  var p=parseFloat(d.c),o=parseFloat(d.o),pct=o>0?(p-o)/o*100:0;
  var pEl=document.getElementById('p_'+s);
  var dEl=document.getElementById('d_'+s);
  if(!pEl||!dEl)return;
  var ps;
  if(p>=10000)ps=p.toLocaleString('en-US',{{maximumFractionDigits:0}});
  else if(p>=1)ps=p.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
  else if(p>=0.01)ps=p.toFixed(4);
  else ps=p.toFixed(6);
  pEl.textContent='$'+ps;
  var a=pct>=0?'▲':'▼',sg=pct>=0?'+':'';
  dEl.textContent=a+' '+sg+pct.toFixed(2)+'%';
  dEl.style.color=pct>=0?'#16a34a':'#dc2626';
}};
ws.onerror=function(){{}};
</script></body></html>"""
    stc.html(html, height=192, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt_price(v, dec=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v:,.{dec}f}"
    if abs(v) >= 1:
        return f"{v:.{dec}f}"
    if abs(v) >= 0.01:
        return f"{v:.4f}"
    if abs(v) >= 0.000001:
        return f"{v:.6f}"
    return f"{v:.8f}"

def fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def fmt_flow(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    sign = "+" if v >= 0 else ""
    if abs(v) >= 1e9: return f"{sign}{v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"{sign}{v/1e6:.1f}M"
    return f"{sign}{v/1e3:.0f}K"

def fmt_vol(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if v >= 1e9: return f"{v/1e9:.1f}B"
    if v >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"

def pct_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "color:#9ca3af"
    return "color:#16a34a;font-weight:600" if v > 0 else ("color:#dc2626;font-weight:600" if v < 0 else "color:#9ca3af")

def card_class(v):
    if v is None: return "neu"
    return "pos" if v >= 0 else "neg"

def hero_card(label, price, pct=None):
    cc = card_class(pct)
    if pct is not None:
        arrow = "▲" if pct >= 0 else "▼"
        sign  = "+" if pct >= 0 else ""
        delta = f'<div class="hero-change {cc}">{arrow} {sign}{pct:.2f}%</div>'
    else:
        delta = ""
    st.markdown(f"""
    <div class="hero-card {cc}">
      <div class="hero-label">{label}</div>
      <div class="hero-price">{price}</div>
      {delta}
    </div>""", unsafe_allow_html=True)

def stat_card(label, value, delta=None):
    if delta is not None:
        arrow = "▲" if delta >= 0 else "▼"
        sign  = "+" if delta >= 0 else ""
        cc    = "pos" if delta >= 0 else "neg"
        d_html = f'<div class="stat-delta {cc}">{arrow} {sign}{delta:.2f}%</div>'
    else:
        d_html = ""
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
      {d_html}
    </div>""", unsafe_allow_html=True)

def section(title):
    st.markdown(f"""
    <div class="sec-header">
      <span class="sec-title">{title}</span>
      <div class="sec-line"></div>
    </div>""", unsafe_allow_html=True)

# ── Chart theme  (light / fintech) ────────────────────────────────────────────
CHART_BG   = "rgba(0,0,0,0)"
GRID_COLOR = "#f0f0f3"
AXIS_COLOR = "#e5e7eb"
TICK_COLOR = "#9ca3af"
PURPLE     = "#7c3aed"

PALETTE = [PURPLE, "#2563eb","#0891b2","#16a34a","#d97706","#dc2626","#db2777","#059669"]

def base_layout(height=280, margin=None):
    m = margin or dict(l=4, r=4, t=28, b=4)
    return dict(
        height=height,
        margin=m,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family="Inter", color=TICK_COLOR, size=10),
        xaxis=dict(showgrid=False, color=TICK_COLOR, zeroline=False,
                   tickfont=dict(size=9, color=TICK_COLOR),
                   linecolor=AXIS_COLOR),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, color=TICK_COLOR,
                   zeroline=False, tickfont=dict(size=9, color=TICK_COLOR),
                   linecolor=AXIS_COLOR),
        showlegend=False,
        hovermode="x unified",
    )

def sparkline(hist_df, color="#4a90e2", height=90):
    """Tiny area sparkline."""
    if hist_df is None or hist_df.empty:
        return None
    y = hist_df["Close"].dropna().values
    if len(y) < 2:
        return None
    x = list(range(len(y)))
    fill_color = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)"
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=fill_color,
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=height, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig

def line_chart(hist_df, col="Close", title="", color="#4a90e2", height=260, yformat=None):
    if hist_df is None or hist_df.empty:
        return None
    df = hist_df.reset_index()
    df.columns = [str(c) for c in df.columns]
    date_col = df.columns[0]
    y = df[col].dropna()
    fill = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)"
    fig = go.Figure(go.Scatter(
        x=df[date_col], y=y,
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=fill,
        hovertemplate=f"%{{y:.2f}}<extra></extra>",
    ))
    layout = base_layout(height)
    layout["title"] = dict(text=title, font=dict(size=11, color="#6b7494"), x=0)
    if yformat:
        layout["yaxis"]["ticksuffix"] = yformat
    pad = (y.max() - y.min()) * 0.05 if y.max() != y.min() else y.mean() * 0.02
    layout["yaxis"]["range"] = [float(y.min() - pad), float(y.max() + pad)]
    fig.update_layout(**layout)
    return fig

def candle_chart(hist_df, title="", height=340):
    if hist_df is None or hist_df.empty:
        return None
    df = hist_df.reset_index()
    df.columns = [str(c) for c in df.columns]
    date_col = df.columns[0]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.72, 0.28], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(
        x=df[date_col], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color="#16a34a", width=1), fillcolor="rgba(22,163,74,0.75)"),
        decreasing=dict(line=dict(color="#dc2626", width=1), fillcolor="rgba(220,38,38,0.75)"),
        name="", showlegend=False,
    ), row=1, col=1)
    vol_colors = ["#16a34a" if c >= o else "#dc2626"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df[date_col], y=df["Volume"],
        marker_color=vol_colors, marker_opacity=0.6,
        showlegend=False,
    ), row=2, col=1)

    layout = base_layout(height, margin=dict(l=4, r=4, t=30, b=4))
    layout["title"] = dict(text=title, font=dict(size=11, color="#6b7494"), x=0)
    layout["xaxis_rangeslider_visible"] = False
    layout["xaxis2"] = dict(showgrid=False, color=TICK_COLOR, zeroline=False,
                             tickfont=dict(size=9, color=TICK_COLOR))
    layout["yaxis2"] = dict(showgrid=True, gridcolor=GRID_COLOR, color=TICK_COLOR,
                             zeroline=False, tickfont=dict(size=9))
    fig.update_layout(**layout)
    return fig

def style_df(df: pd.DataFrame, pct_cols=None, flow_cols=None):
    """Apply color styling to a performance DataFrame."""
    if pct_cols is None:
        pct_cols = [c for c in ["1D %","5D %","1M %","YTD %"] if c in df.columns]
    if flow_cols is None:
        flow_cols = [c for c in ["Flow 1D","Flow 5D","Flow 1M"] if c in df.columns]

    formatters = {}
    for c in pct_cols:
        formatters[c] = fmt_pct
    for c in flow_cols:
        formatters[c] = fmt_flow
    if "Price" in df.columns:
        def _fmt_price_cell(v):
            if pd.isna(v): return "—"
            if abs(v) >= 1_000: return f"{v:,.2f}"
            if abs(v) >= 1:     return f"{v:.2f}"
            if abs(v) >= 0.01:  return f"{v:.4f}"
            if abs(v) >= 0.000001: return f"{v:.6f}"
            return f"{v:.8f}"
        formatters["Price"] = _fmt_price_cell
    if "Volume" in df.columns:
        formatters["Volume"] = fmt_vol
    if "Rel. Vol." in df.columns:
        formatters["Rel. Vol."] = lambda v: f"{v:.2f}x" if not pd.isna(v) else "—"

    styled = df.style.format(formatters, na_rep="—")
    for col in pct_cols:
        styled = styled.applymap(pct_color, subset=[col])
    for col in flow_cols:
        styled = styled.applymap(
            lambda v: "color:#16a34a;font-weight:600" if not pd.isna(v) and v > 0
                      else ("color:#dc2626;font-weight:600" if not pd.isna(v) and v < 0 else "color:#9ca3af"),
            subset=[col]
        )
    styled = styled.set_properties(**{
        "background-color": "#ffffff",
        "color": "#111827",
        "border-color": "#f3f4f6",
        "font-size": "12px",
        "font-family": "Inter, sans-serif",
    })
    styled = styled.set_table_styles([
        {"selector": "th", "props": [
            ("background-color", "#f9fafb"),
            ("color", "#6b7280"),
            ("font-size", "10px"),
            ("font-weight", "700"),
            ("text-transform", "uppercase"),
            ("letter-spacing", "0.08em"),
            ("border-color", "#e5e7eb"),
            ("font-family", "Inter, sans-serif"),
        ]},
        {"selector": "tr:hover td", "props": [("background-color", "#faf5ff")]},
    ])
    return styled


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
now = datetime.now(timezone.utc)
weekday = now.weekday()   # 0=Mon … 6=Sun
hour    = now.hour
us_open = (weekday < 5) and (13 <= hour < 21)   # ~NYSE hours UTC
badge_color = "#16a34a" if us_open else "#f59e0b"
badge_label = "US Markets Open" if us_open else "Markets Closed"

st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="dash-title">🌍 Global Markets Dashboard</div>
    <div class="dash-subtitle">{now.strftime('%A, %d %B %Y  •  %H:%M UTC')}</div>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <div class="market-badge" style="border-color:rgba(240,180,41,0.3);color:{badge_color};background:rgba(240,180,41,0.08)">
      <div class="market-dot" style="background:{badge_color};box-shadow:0 0 6px {badge_color}"></div>
      {badge_label}
    </div>
    <div style="font-size:11px;color:#2d3142;font-family:'JetBrains Mono',monospace;">
      ↻ {AUTO_REFRESH_SECS}s
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HERO BAR
# ══════════════════════════════════════════════════════════════════════════════
HERO = {
    "S&P 500": ("^GSPC", 2),
    "NASDAQ 100": ("^NDX", 2),
    "VIX": ("^VIX", 2),
    "DXY": ("DX-Y.NYB", 3),
    "Gold": ("GC=F", 2),
    "WTI": ("CL=F", 2),
    "10Y Yield": ("^TNX", 3),
    "BTC/USD": ("BTC-USD", 0),
}

with st.spinner(""):
    hero_q = get_bulk_quotes([v[0] for v in HERO.values()])

st.markdown("""
<div style="font-size:10px;color:#2d3142;text-transform:uppercase;letter-spacing:0.12em;
            margin-bottom:8px;font-weight:600;">
  📊 &nbsp; Market Snapshot
</div>
""", unsafe_allow_html=True)

hero_cols = st.columns(len(HERO))
for i, (label, (sym, dec)) in enumerate(HERO.items()):
    q = hero_q.get(sym)
    with hero_cols[i]:
        if q:
            hero_card(label, fmt_price(q["price"], dec), q.get("pct_change"))
        else:
            hero_card(label, "—")

st.markdown("""
<div style="margin:20px 0 4px;font-size:10px;color:#2d3142;text-transform:uppercase;
            letter-spacing:0.12em;font-weight:600;">
  🗂 &nbsp; Sections — click a tab below
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📈  Equities",
    "💵  ETF Flows",
    "🏦  Fixed Income",
    "🛢  Commodities",
    "💱  Currencies",
    "₿   Crypto",
    "🧠  Sentiment",
    "💰  Private Credit",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUITIES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:

    # ── Heatmap + region nav ────────────────────────────────────────────────
    all_idx = {n: s for r in INDICES.values() for n, s in r.items()}
    idx_q = get_bulk_quotes(list(all_idx.values()))

    # Treemap heatmap
    section("Global Index Heatmap")
    heat_rows = []
    for region, items in INDICES.items():
        for name, sym in items.items():
            q = idx_q.get(sym)
            if q and q.get("pct_change") is not None:
                heat_rows.append({"Region": region, "Index": name,
                                   "chg": round(float(q["pct_change"]), 2),
                                   "price": q["price"]})

    if heat_rows:
        df_h = pd.DataFrame(heat_rows)
        # Custom discrete color: dark red → dark → dark green
        scale = [
            [0.0,  "#fef2f2"], [0.2, "#fca5a5"],
            [0.4,  "#f9fafb"],
            [0.6,  "#bbf7d0"], [1.0, "#16a34a"],
        ]
        fig_heat = px.treemap(
            df_h, path=["Region","Index"],
            values=[1]*len(df_h),
            color="chg",
            color_continuous_scale=scale,
            color_continuous_midpoint=0,
            custom_data=["chg","price","Index"],
        )
        fig_heat.update_traces(
            hovertemplate="<b>%{customdata[2]}</b><br>%{customdata[1]:,.2f}<br>%{customdata[0]:+.2f}%<extra></extra>",
            texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}%",
            textfont=dict(size=12, family="Inter"),
            marker=dict(line=dict(width=2, color="#f4f5f7")),
        )
        fig_heat.update_layout(
            height=340, margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor=CHART_BG,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ── Region tabs ─────────────────────────────────────────────────────────
    reg_tabs = st.tabs(list(INDICES.keys()))
    for ri, (region, items) in enumerate(INDICES.items()):
        _sk = f"idx_chart_{ri}"
        if _sk not in st.session_state:
            st.session_state[_sk] = list(items.values())[0]

        with reg_tabs[ri]:
            cols = st.columns(min(5, len(items)))
            for i, (name, sym) in enumerate(items.items()):
                q = idx_q.get(sym)
                with cols[i % 5]:
                    stat_card(name, fmt_price(q["price"]) if q else "—",
                              q.get("pct_change") if q else None)

            _dd_col, _ = st.columns([1, 3])
            with _dd_col:
                _names = list(items.keys())
                _sel   = next((n for n, s in items.items()
                               if s == st.session_state[_sk]), _names[0])
                _pick  = st.selectbox("Chart", _names, index=_names.index(_sel),
                                      key=f"idx_dd_{ri}", label_visibility="collapsed")
                if items[_pick] != st.session_state[_sk]:
                    st.session_state[_sk] = items[_pick]
                    st.rerun()

            _csym = st.session_state[_sk]
            if _csym in _TV_SYM:
                tv_chart(_csym, height=420, interval="D")

    # ── Equity ETF Performance ───────────────────────────────────────────────
    section("Equity ETF Performance")
    eq_etf_tabs = st.tabs(["US Equity", "International", "Thematic"])
    with eq_etf_tabs[0]:
        us_etf_map = {v["name"]: k for k, v in ETF_UNIVERSE["US Equity"].items()}
        df_us_etf = get_performance_summary(us_etf_map)
        if not df_us_etf.empty:
            show_eq = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_us_etf.columns]
            st.dataframe(style_df(df_us_etf[show_eq]), use_container_width=True, hide_index=True)
    with eq_etf_tabs[1]:
        intl_etf_map = {v["name"]: k for k, v in ETF_UNIVERSE["International"].items()}
        df_intl_etf = get_performance_summary(intl_etf_map)
        if not df_intl_etf.empty:
            show_eq = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_intl_etf.columns]
            st.dataframe(style_df(df_intl_etf[show_eq]), use_container_width=True, hide_index=True)
    with eq_etf_tabs[2]:
        theme_etf_map = {v["name"]: k for k, v in ETF_UNIVERSE["Thematic"].items()}
        df_theme_etf = get_performance_summary(theme_etf_map)
        if not df_theme_etf.empty:
            show_eq = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_theme_etf.columns]
            st.dataframe(style_df(df_theme_etf[show_eq]), use_container_width=True, hide_index=True)

    # ── Sector rotation ──────────────────────────────────────────────────────
    section("S&P 500 Sector Rotation")
    SECTOR_MAP = {v["name"]: k for k, v in ETF_UNIVERSE["Sector"].items()}
    df_sec = get_performance_summary(SECTOR_MAP)

    if not df_sec.empty:
        df_sec2 = df_sec.dropna(subset=["1D %"]).sort_values("1D %")
        colors = ["#16a34a" if v >= 0 else "#dc2626" for v in df_sec2["1D %"]]

        fig_sec = go.Figure(go.Bar(
            x=df_sec2["1D %"], y=df_sec2["Name"],
            orientation="h",
            marker=dict(color=colors, opacity=0.85,
                        line=dict(width=0)),
            text=[fmt_pct(v) for v in df_sec2["1D %"]],
            textfont=dict(size=10, color="#8891a5", family="JetBrains Mono"),
            textposition="outside",
            hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
        ))
        layout = base_layout(320, margin=dict(l=4, r=70, t=4, b=4))
        layout["xaxis"]["ticksuffix"] = "%"
        layout["yaxis"]["tickfont"] = dict(size=11, color="#8891a5")
        layout["bargap"] = 0.35
        fig_sec.update_layout(**layout)
        st.plotly_chart(fig_sec, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ETF FLOWS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    section("ETF Flow Analysis")
    st.markdown(
        "<p style='font-size:11px;color:#2d3142;margin:-10px 0 12px'>"
        "Flow Proxy = (Volume − 20D Avg) × Price × sign(Return) &nbsp;|&nbsp; "
        "Positive = estimated net inflow pressure, Negative = outflow pressure."
        "</p>", unsafe_allow_html=True,
    )

    etf_cat = st.selectbox("Category", list(ETF_UNIVERSE.keys()), key="etf_cat",
                            label_visibility="collapsed")
    tickers  = list(ETF_UNIVERSE[etf_cat].keys())
    etf_names = {t: ETF_UNIVERSE[etf_cat][t]["name"] for t in tickers}

    rows = []
    with st.spinner("Loading ETF data…"):
        for tk in tickers:
            fd   = compute_etf_flow_proxy(tk)
            if not fd:
                continue
            rows.append({
                "Ticker": tk, "Name": etf_names.get(tk,""),
                "Price": fd.get("price"), "1D %": fd.get("perf_1d"),
                "5D %": fd.get("perf_5d"), "1M %": fd.get("perf_1mo"),
                "YTD %": fd.get("perf_ytd"),
                "Volume": fd.get("volume"), "Rel. Vol.": fd.get("rel_volume"),
                "Flow 5D": fd.get("flow_proxy_5d"), "Flow 1M": fd.get("flow_proxy_1mo"),
            })

    if rows:
        df_etf = pd.DataFrame(rows)

        # ── Summary cards ──────────────────────────────────────────────────
        c2, c3, c4 = st.columns(3)
        valid_flow = df_etf["Flow 5D"].dropna()
        with c2:
            if len(valid_flow):
                tk = df_etf.loc[df_etf["Flow 5D"].idxmax(), "Ticker"]
                stat_card(f"Top Inflow  [{tk}]",
                          fmt_flow(df_etf["Flow 5D"].max()),
                          df_etf.loc[df_etf["Flow 5D"].idxmax(), "1D %"])
        with c3:
            if len(valid_flow):
                tk = df_etf.loc[df_etf["Flow 5D"].idxmin(), "Ticker"]
                stat_card(f"Top Outflow  [{tk}]",
                          fmt_flow(df_etf["Flow 5D"].min()),
                          df_etf.loc[df_etf["Flow 5D"].idxmin(), "1D %"])
        with c4:
            if df_etf["1D %"].notna().any():
                tk = df_etf.loc[df_etf["1D %"].idxmax(), "Ticker"]
                stat_card(f"Best Today  [{tk}]",
                          fmt_price(df_etf.loc[df_etf["1D %"].idxmax(), "Price"]),
                          df_etf["1D %"].max())

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Flow + RelVol side-by-side ─────────────────────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            section("5-Day Flow Proxy")
            df_fl = df_etf.dropna(subset=["Flow 5D"]).sort_values("Flow 5D")
            bar_c = ["#16a34a" if v >= 0 else "#dc2626" for v in df_fl["Flow 5D"]]
            fig_fl = go.Figure(go.Bar(
                x=df_fl["Flow 5D"], y=df_fl["Ticker"],
                orientation="h", marker=dict(color=bar_c, opacity=0.85, line=dict(width=0)),
                text=[fmt_flow(v) for v in df_fl["Flow 5D"]],
                textfont=dict(size=9, color="#6b7494", family="JetBrains Mono"),
                textposition="outside",
                hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
            ))
            layout_fl = base_layout(max(280, len(df_fl)*30), dict(l=4,r=70,t=4,b=4))
            layout_fl["bargap"] = 0.3
            fig_fl.update_layout(**layout_fl)
            st.plotly_chart(fig_fl, use_container_width=True)

        with col_b:
            section("Relative Volume (vs 20D Avg)")
            df_rv = df_etf.dropna(subset=["Rel. Vol."]).sort_values("Rel. Vol.")
            rv_c  = ["#f59e0b" if v >= 2 else PALETTE[0] for v in df_rv["Rel. Vol."]]
            fig_rv = go.Figure(go.Bar(
                x=df_rv["Rel. Vol."], y=df_rv["Ticker"],
                orientation="h", marker=dict(color=rv_c, opacity=0.85, line=dict(width=0)),
                text=[f"{v:.1f}×" for v in df_rv["Rel. Vol."]],
                textfont=dict(size=9, color="#6b7494", family="JetBrains Mono"),
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f}×<extra></extra>",
            ))
            fig_rv.add_vline(x=1.0, line_dash="dot", line_color="#2d3142", opacity=0.8)
            layout_rv = base_layout(max(280, len(df_rv)*30), dict(l=4,r=60,t=4,b=4))
            layout_rv["xaxis"]["ticksuffix"] = "×"
            layout_rv["bargap"] = 0.3
            fig_rv.update_layout(**layout_rv)
            st.plotly_chart(fig_rv, use_container_width=True)

        # ── Full table ─────────────────────────────────────────────────────
        section("Full ETF Table")
        show_cols = [c for c in ["Ticker","Name","Price","1D %","5D %","1M %",
                                  "YTD %","Rel. Vol.","Flow 5D","Flow 1M"] if c in df_etf.columns]
        st.dataframe(style_df(df_etf[show_cols]), use_container_width=True, hide_index=True)

        # ── Deep Dive ─────────────────────────────────────────────────────
        section("ETF Deep Dive")
        sel = st.selectbox("Select ETF", tickers, key="etf_deep", label_visibility="collapsed")
        fd2 = compute_etf_flow_proxy(sel)
        if fd2 and "flow_history" in fd2:
            fh = fd2["flow_history"].reset_index()
            fh.columns = [str(c) for c in fh.columns]
            dc = fh.columns[0]

            m2,m3,m4 = st.columns(3)
            with m2: stat_card("Rel. Vol.", f"{fd2.get('rel_volume',0):.2f}×")
            with m3: stat_card("Flow 5D", fmt_flow(fd2.get("flow_proxy_5d")), None)
            with m4: stat_card("Flow 1M", fmt_flow(fd2.get("flow_proxy_1mo")), None)

            fig_dd = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                   subplot_titles=["Price","Volume vs 20D Avg","Flow Proxy"],
                                   vertical_spacing=0.07, row_heights=[0.42,0.28,0.30])
            _close = fh["Close"].dropna()
            _pad = (_close.max() - _close.min()) * 0.05 if _close.max() != _close.min() else _close.mean() * 0.02
            fig_dd.add_trace(go.Scatter(
                x=fh[dc], y=fh["Close"], mode="lines",
                line=dict(color=PALETTE[0], width=2),
                fill="tozeroy", fillcolor="rgba(74,144,226,0.07)",
            ), row=1, col=1)
            fig_dd.update_yaxes(range=[float(_close.min()-_pad), float(_close.max()+_pad)], row=1, col=1)
            fig_dd.add_trace(go.Bar(
                x=fh[dc], y=fh["Volume"],
                marker=dict(color=PALETTE[0], opacity=0.5, line=dict(width=0)),
            ), row=2, col=1)
            fig_dd.add_trace(go.Scatter(
                x=fh[dc], y=fh["avg_vol_20d"],
                mode="lines", line=dict(color="#f59e0b", dash="dot", width=1.5),
            ), row=2, col=1)
            flow_c = ["#16a34a" if v >= 0 else "#dc2626" for v in fh["flow_proxy"].fillna(0)]
            fig_dd.add_trace(go.Bar(
                x=fh[dc], y=fh["flow_proxy"],
                marker=dict(color=flow_c, opacity=0.8, line=dict(width=0)),
            ), row=3, col=1)
            for r in [1,2,3]:
                fig_dd.update_xaxes(showgrid=False, color=TICK_COLOR, zeroline=False,
                                     tickfont=dict(size=9,color=TICK_COLOR), row=r, col=1)
                fig_dd.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, color=TICK_COLOR,
                                     tickfont=dict(size=9), zeroline=False, row=r, col=1)
            fig_dd.update_layout(height=480, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                                  margin=dict(l=4,r=4,t=30,b=4), showlegend=False,
                                  hovermode="x unified",
                                  font=dict(color=TICK_COLOR, size=10))
            st.plotly_chart(fig_dd, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FIXED INCOME
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    fi_tabs = st.tabs(["🇺🇸 United States", "🇯🇵 Japan"])

    # ── US Fixed Income ──────────────────────────────────────────────────────
    with fi_tabs[0]:
        section("US Treasury Yield Curve")
        yc_data = get_yield_curve()
        yld_q   = get_bulk_quotes(list(YIELD_SYMBOLS.values()))

        if yc_data is not None:
            fig_yc = go.Figure()
            fig_yc.add_trace(go.Scatter(
                x=yc_data["maturity"], y=yc_data["yield"],
                mode="lines+markers",
                line=dict(color=PALETTE[0], width=2.5),
                marker=dict(size=9, color=PALETTE[0],
                            line=dict(color="#f4f5f7", width=2)),
                fill="tozeroy", fillcolor="rgba(74,144,226,0.07)",
                hovertemplate="%{x}: %{y:.3f}%<extra></extra>",
            ))
            layout_yc = base_layout(280)
            layout_yc["yaxis"]["ticksuffix"] = "%"
            layout_yc["yaxis"]["title"] = dict(text="Yield (%)", font=dict(size=10, color=TICK_COLOR))
            fig_yc.update_layout(**layout_yc)
            st.plotly_chart(fig_yc, use_container_width=True)

        yc2y = float(yc_data[yc_data["maturity"] == "2Y"]["yield"].iloc[0]) if yc_data is not None and "2Y" in yc_data["maturity"].values else None
        _h2y_short = get_us_yield_history("2Y", lookback_days=5)
        _2y_chg = float((_h2y_short.iloc[-1] - _h2y_short.iloc[-2]) / _h2y_short.iloc[-2] * 100) if _h2y_short is not None and len(_h2y_short) >= 2 else None
        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1: stat_card("US 2Y", f"{yc2y:.3f}%" if yc2y else "—", _2y_chg)
        for (label, sym), col in zip(YIELD_SYMBOLS.items(), [kc2, kc3, kc4]):
            q = yld_q.get(sym)
            with col: stat_card(label, f"{q['price']:.3f}%" if q else "—",
                                q.get("pct_change") if q else None)

        section("2Y / 10Y Yields & Spread (Inversion Watch)")
        h2y  = get_us_yield_history("2Y",  lookback_days=365)
        h10y = get_us_yield_history("10Y", lookback_days=365)
        if h2y is not None and h10y is not None:
            combined = pd.DataFrame({"2Y": h2y, "10Y": h10y}).dropna()
            combined["Spread"] = combined["10Y"] - combined["2Y"]
            fig_sp2 = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                subplot_titles=["2Y Treasury Yield", "10Y Treasury Yield", "10Y – 2Y Spread"],
                vertical_spacing=0.07, row_heights=[0.33, 0.33, 0.34],
            )
            fig_sp2.add_trace(go.Scatter(
                x=combined.index, y=combined["2Y"], mode="lines",
                line=dict(color=PALETTE[1], width=2),
                hovertemplate="%{x|%Y-%m-%d}: %{y:.3f}%<extra>2Y</extra>",
            ), row=1, col=1)
            fig_sp2.add_trace(go.Scatter(
                x=combined.index, y=combined["10Y"], mode="lines",
                line=dict(color=PALETTE[0], width=2),
                hovertemplate="%{x|%Y-%m-%d}: %{y:.3f}%<extra>10Y</extra>",
            ), row=2, col=1)
            sp_colors = ["#16a34a" if v >= 0 else "#dc2626" for v in combined["Spread"]]
            fig_sp2.add_trace(go.Bar(
                x=combined.index, y=combined["Spread"],
                marker=dict(color=sp_colors, opacity=0.8, line=dict(width=0)),
                hovertemplate="%{x|%Y-%m-%d}: %{y:.3f}%<extra>10Y–2Y</extra>",
            ), row=3, col=1)
            fig_sp2.add_hline(y=0, line_dash="dot", line_color="#2d3142", opacity=0.8, row=3, col=1)
            for r in [1, 2, 3]:
                fig_sp2.update_xaxes(showgrid=False, color=TICK_COLOR, zeroline=False,
                                     tickfont=dict(size=9, color=TICK_COLOR), row=r, col=1)
                fig_sp2.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, color=TICK_COLOR,
                                     tickfont=dict(size=9), zeroline=False,
                                     ticksuffix="%", row=r, col=1)
            fig_sp2.update_layout(
                height=520, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                margin=dict(l=4, r=4, t=30, b=4), showlegend=False,
                hovermode="x unified", font=dict(color=TICK_COLOR, size=10),
            )
            st.plotly_chart(fig_sp2, use_container_width=True)

        section("Bond ETF Performance")
        bond_map = {v["name"]: k for k, v in ETF_UNIVERSE["Fixed Income"].items()}
        df_bonds = get_performance_summary(bond_map)
        if not df_bonds.empty:
            show = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_bonds.columns]
            st.dataframe(style_df(df_bonds[show]), use_container_width=True, hide_index=True)

    # ── Japan Fixed Income ───────────────────────────────────────────────────
    with fi_tabs[1]:
        jp_yields, _jp_hist, _jp_source = get_japan_yield_curve()

        # ── Yield curve chart ────────────────────────────────────────────────
        section("JGB Yield Curve")
        tenor_order = ["3M", "2Y", "5Y", "10Y", "20Y", "30Y"]
        x_labels = [t for t in tenor_order if t in jp_yields]
        y_vals   = [jp_yields[t] for t in x_labels]

        if x_labels:
            fig_jyc = go.Figure()
            fig_jyc.add_trace(go.Scatter(
                x=x_labels, y=y_vals,
                mode="lines+markers",
                line=dict(color="#e11d48", width=2.5),
                marker=dict(size=9, color="#e11d48",
                            line=dict(color="#f4f5f7", width=2)),
                fill="tozeroy", fillcolor="rgba(225,29,72,0.07)",
                hovertemplate="%{x}: %{y:.3f}%<extra></extra>",
            ))
            layout_jyc = base_layout(280)
            layout_jyc["yaxis"]["ticksuffix"] = "%"
            layout_jyc["yaxis"]["title"] = dict(text="Yield (%)", font=dict(size=10, color=TICK_COLOR))
            fig_jyc.update_layout(**layout_jyc)
            st.plotly_chart(fig_jyc, use_container_width=True, key="jp_yc_chart")

            jcols = st.columns(len(x_labels))
            for col, tenor in zip(jcols, x_labels):
                with col: stat_card(f"JGB {tenor}", f"{jp_yields[tenor]:.3f}%")

        # ── Japan bond ETF performance ────────────────────────────────────────
        section("Japan Bond ETF Performance")
        jp_etf_map = {"iShares Japan Govt Bond ETF (TSE)": "1482.T"}
        df_jp_bonds = get_performance_summary(jp_etf_map)
        if not df_jp_bonds.empty:
            show_jp = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_jp_bonds.columns]
            st.dataframe(style_df(df_jp_bonds[show_jp]), use_container_width=True, hide_index=True)
        st.caption("1482.T trades in JPY on Tokyo Stock Exchange. Price moves inversely to JGB yields.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    comm_tabs = st.tabs(list(COMMODITIES.keys()) + ["📊 All"])

    _COMM_ETF_MAP = {
        "Energy":          {"US Oil Fund": "USO", "US Natural Gas Fund": "UNG",
                            "Invesco Commodity": "PDBC", "iShares Commodity": "GSG"},
        "Precious Metals": {"SPDR Gold Shares": "GLD", "iShares Silver Trust": "SLV",
                            "Gold Miners ETF": "GDX", "Junior Gold Miners": "GDXJ"},
        "Base Metals":     {"US Copper Index": "CPER", "Invesco Commodity": "PDBC"},
        "Agricultural":    {"Invesco Commodity": "PDBC", "iShares Commodity": "GSG"},
        "Softs":           {"Invesco Commodity": "PDBC", "iShares Commodity": "GSG"},
    }

    for ci, (cat, items) in enumerate(COMMODITIES.items()):
        _sk = f"comm_chart_{ci}"
        if _sk not in st.session_state:
            st.session_state[_sk] = list(items.values())[0]

        with comm_tabs[ci]:
            section(cat)
            cq = get_bulk_quotes(list(items.values()))

            cols = st.columns(min(5, len(items)))
            for i, (name, sym) in enumerate(items.items()):
                q = cq.get(sym)
                with cols[i % 5]:
                    stat_card(name, fmt_price(q["price"]) if q else "—",
                              q.get("pct_change") if q else None)

            _dd_col, _ = st.columns([1, 3])
            with _dd_col:
                _names = list(items.keys())
                _sel   = next((n for n, s in items.items()
                               if s == st.session_state[_sk]), _names[0])
                _pick  = st.selectbox("Chart", _names, index=_names.index(_sel),
                                      key=f"comm_dd_{ci}", label_visibility="collapsed")
                if items[_pick] != st.session_state[_sk]:
                    st.session_state[_sk] = items[_pick]
                    st.rerun()

            _csym = st.session_state[_sk]
            if _csym in _TV_SYM:
                tv_chart(_csym, height=420)

            etf_map_c = _COMM_ETF_MAP.get(cat)
            if etf_map_c:
                section(f"{cat} — Related ETFs")
                df_cetf = get_performance_summary(etf_map_c)
                if not df_cetf.empty:
                    show_c = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_cetf.columns]
                    st.dataframe(style_df(df_cetf[show_c]), use_container_width=True, hide_index=True)

    with comm_tabs[-1]:
        section("All Commodities")
        all_c = {n: s for cat, items in COMMODITIES.items() for n, s in items.items()}
        df_all = get_performance_summary(all_c)
        if not df_all.empty:
            show = [c for c in ["Name","Price","1D %","5D %","1M %","YTD %"] if c in df_all.columns]
            st.dataframe(style_df(df_all[show]), use_container_width=True, hide_index=True)
        section("All Commodity ETFs")
        all_comm_etfs = {v["name"]: k for k, v in ETF_UNIVERSE["Commodities"].items()}
        df_all_cetf = get_performance_summary(all_comm_etfs)
        if not df_all_cetf.empty:
            show_ac = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_all_cetf.columns]
            st.dataframe(style_df(df_all_cetf[show_ac]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CURRENCIES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    fx_tabs = st.tabs(["Majors", "Emerging Markets", "📊 FX Heatmap"])

    for fi, (cat, items) in enumerate(CURRENCIES.items()):
        _sk = f"fx_chart_{fi}"
        if _sk not in st.session_state:
            st.session_state[_sk] = list(items.values())[0]

        with fx_tabs[fi]:
            section(cat)
            fq = get_bulk_quotes(list(items.values()))
            cols = st.columns(min(4, len(items)))
            for i, (name, sym) in enumerate(items.items()):
                q = fq.get(sym)
                dec = 4 if "/" in name and "USD" not in name[:3] else 3
                with cols[i % 4]:
                    stat_card(name, fmt_price(q["price"], dec) if q else "—",
                              q.get("pct_change") if q else None)

            _dd_col, _ = st.columns([1, 3])
            with _dd_col:
                _fx_names = list(items.keys())
                _fx_sel   = next((n for n, s in items.items()
                                  if s == st.session_state[_sk]), _fx_names[0])
                _fx_pick  = st.selectbox("Chart", _fx_names,
                                         index=_fx_names.index(_fx_sel),
                                         key=f"fx_dd_{fi}",
                                         label_visibility="collapsed")
                if items[_fx_pick] != st.session_state[_sk]:
                    st.session_state[_sk] = items[_fx_pick]
                    st.rerun()

            _chart_sym = st.session_state[_sk]
            if _chart_sym in _TV_SYM:
                tv_chart(_chart_sym, height=420, interval="D")

    with fx_tabs[-1]:
        section("FX vs USD — 1D % Change")
        all_fx = {n: s for cat, items in CURRENCIES.items() for n, s in items.items()}
        fqa = get_bulk_quotes(list(all_fx.values()))
        hrows = [{"Pair":n,"1D %":fqa[s]["pct_change"],"Price":fqa[s]["price"]}
                 for n,s in all_fx.items() if s in fqa and fqa[s].get("pct_change") is not None]
        if hrows:
            dfh = pd.DataFrame(hrows).sort_values("1D %")
            hc = ["#16a34a" if v>=0 else "#dc2626" for v in dfh["1D %"]]
            fig_fxh = go.Figure(go.Bar(
                x=dfh["1D %"], y=dfh["Pair"], orientation="h",
                marker=dict(color=hc, opacity=0.85, line=dict(width=0)),
                text=[fmt_pct(v) for v in dfh["1D %"]],
                textfont=dict(size=9,color="#6b7494",family="JetBrains Mono"),
                textposition="outside",
            ))
            layout_fxh = base_layout(max(380, len(dfh)*28), dict(l=4,r=70,t=4,b=4))
            layout_fxh["xaxis"]["ticksuffix"] = "%"
            layout_fxh["bargap"] = 0.3
            fig_fxh.update_layout(**layout_fxh)
            st.plotly_chart(fig_fxh, use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    if "crypto_chart_sym" not in st.session_state:
        st.session_state["crypto_chart_sym"] = "BTC-USD"
    sel_sym = st.session_state["crypto_chart_sym"]

    section("Crypto Markets")
    crypto_live_cards(sel_sym, CRYPTO)

    _dd_col, _ = st.columns([1, 3])
    with _dd_col:
        _names = list(CRYPTO.keys())
        _sel_name = next((n for n, s in CRYPTO.items() if s == sel_sym), "Bitcoin")
        _choice = st.selectbox("Chart", _names,
                               index=_names.index(_sel_name),
                               key="cr_dd", label_visibility="collapsed")
        if CRYPTO[_choice] != sel_sym:
            st.session_state["crypto_chart_sym"] = CRYPTO[_choice]
            st.rerun()

    tv_chart(sel_sym, height=440, interval="D")

    # ── Bitcoin & Ethereum Spot ETFs ──────────────────────────────────────────
    cr_etf_tabs = st.tabs(["₿ Bitcoin ETFs", "Ξ Ethereum ETFs"])

    _btc_etfs = {
        "iShares Bitcoin Trust (IBIT)":       "IBIT",
        "Fidelity Wise Origin Bitcoin (FBTC)": "FBTC",
        "Bitwise Bitcoin ETF (BITB)":          "BITB",
        "ARK 21Shares Bitcoin (ARKB)":         "ARKB",
        "Grayscale Bitcoin Trust (GBTC)":      "GBTC",
        "ProShares Bitcoin Futures (BITO)":    "BITO",
    }
    _eth_etfs = {
        "iShares Ethereum Trust (ETHA)":       "ETHA",
        "Fidelity Ethereum Fund (FETH)":       "FETH",
        "Bitwise Ethereum ETF (ETHW)":         "ETHW",
        "Grayscale Ethereum Trust (ETHE)":     "ETHE",
        "VanEck Ethereum ETF (ETHV)":          "ETHV",
    }

    with cr_etf_tabs[0]:
        df_btc_etf = get_performance_summary(_btc_etfs)
        if not df_btc_etf.empty:
            show_e = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_btc_etf.columns]
            st.dataframe(style_df(df_btc_etf[show_e]), use_container_width=True, hide_index=True)

    with cr_etf_tabs[1]:
        df_eth_etf = get_performance_summary(_eth_etfs)
        if not df_eth_etf.empty:
            show_e = [c for c in ["Name","Ticker","Price","1D %","Flow 1D","5D %","Flow 5D","1M %","YTD %"] if c in df_eth_etf.columns]
            st.dataframe(style_df(df_eth_etf[show_e]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    section("Market Sentiment Indicators")

    SENT = {"VIX": "^VIX", "VVIX": "^VVIX", "S&P 500":"^GSPC",
            "Gold":"GC=F", "WTI":"CL=F", "DXY":"DX-Y.NYB",
            "TLT (Safe)":"TLT", "HYG (Risk)":"HYG"}
    sq = get_bulk_quotes(list(SENT.values()))
    sc = st.columns(4)
    for i, (label, sym) in enumerate(SENT.items()):
        q = sq.get(sym)
        with sc[i % 4]:
            stat_card(label, fmt_price(q["price"]) if q else "—",
                      q.get("pct_change") if q else None)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # VIX Gauge
    vix_q = sq.get("^VIX")
    if vix_q and vix_q.get("price"):
        vv = vix_q["price"]
        labels = [(0,15,"Extreme Greed"),(15,20,"Greed"),(20,25,"Neutral"),
                  (25,35,"Fear"),(35,80,"Extreme Fear")]
        lvl = next((l for lo,hi,l in labels if lo<=vv<hi), "Extreme Fear")
        gauge_col = {"Extreme Greed":"#16a34a","Greed":"#4ade80",
                     "Neutral":"#f59e0b","Fear":"#f97316","Extreme Fear":"#dc2626"}[lvl]

        col_gauge, col_vix = st.columns([1,2])
        with col_gauge:
            section(f"VIX Gauge — {lvl}")
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=vv,
                delta={"reference": vix_q.get("prev_close", vv),
                       "valueformat":".2f",
                       "increasing":{"color":"#dc2626"},
                       "decreasing":{"color":"#16a34a"}},
                number={"font":{"size":36,"color":gauge_col,"family":"JetBrains Mono"},
                        "valueformat":".2f"},
                title={"text": f"<b>{lvl}</b>",
                       "font":{"size":13,"color":gauge_col}},
                gauge={
                    "axis":{"range":[0,80],"tickcolor":TICK_COLOR,
                             "tickfont":{"color":TICK_COLOR,"size":9}},
                    "bar":{"color":gauge_col,"thickness":0.25},
                    "bgcolor":"#f9fafb",
                    "bordercolor":"#f9fafb",
                    "steps":[
                        {"range":[0,15],  "color":"rgba(0,212,106,0.1)"},
                        {"range":[15,20], "color":"rgba(52,211,153,0.06)"},
                        {"range":[20,25], "color":"rgba(240,180,41,0.06)"},
                        {"range":[25,35], "color":"rgba(251,146,60,0.08)"},
                        {"range":[35,80], "color":"rgba(255,75,110,0.1)"},
                    ],
                    "threshold":{"line":{"color":"#e8eaf0","width":3},
                                 "thickness":0.8,"value":vv},
                },
            ))
            fig_g.update_layout(height=260, margin=dict(l=20,r=20,t=10,b=10),
                                 paper_bgcolor=CHART_BG,
                                 font=dict(color=TICK_COLOR, family="Inter"))
            st.plotly_chart(fig_g, use_container_width=True)

        with col_vix:
            section("VIX — 1 Year History")
            vix_h = get_history("^VIX","1y")
            if vix_h is not None:
                vdf = vix_h.reset_index(); vdf.columns=[str(c) for c in vdf.columns]
                dc = vdf.columns[0]
                fig_vh = go.Figure()
                # Zones
                for y0,y1,c in [(0,15,"rgba(0,212,106,0.04)"),
                                  (15,20,"rgba(52,211,153,0.02)"),
                                  (25,35,"rgba(251,146,60,0.04)"),
                                  (35,100,"rgba(255,75,110,0.06)")]:
                    fig_vh.add_hrect(y0=y0,y1=y1,fillcolor=c,line_width=0)
                fig_vh.add_trace(go.Scatter(
                    x=vdf[dc], y=vdf["Close"], mode="lines",
                    line=dict(color="#f59e0b",width=2),
                    fill="tozeroy", fillcolor="rgba(240,180,41,0.05)",
                    hovertemplate="VIX: %{y:.2f}<extra></extra>",
                ))
                fig_vh.add_hline(y=20, line_dash="dot", line_color="#2d3142",
                                  annotation_text="20", annotation_font_color=TICK_COLOR,
                                  annotation_font_size=9)
                layout_vh = base_layout(260)
                fig_vh.update_layout(**layout_vh)
                st.plotly_chart(fig_vh, use_container_width=True)

    # Risk-On / Risk-Off
    section("Risk-On / Risk-Off Ratio (EEM ÷ TLT)")
    eem_h = get_history("EEM","1y")
    tlt_h = get_history("TLT","1y")
    if eem_h is not None and tlt_h is not None:
        ratio = (eem_h["Close"] / tlt_h["Close"]).dropna()
        rdf = ratio.reset_index(); rdf.columns=["Date","Ratio"]
        col_r = "#16a34a" if rdf["Ratio"].iloc[-1] >= rdf["Ratio"].iloc[-2] else "#dc2626"
        fig_ro = line_chart(rdf, "Ratio", "EEM/TLT (Rising = Risk-On)", col_r, 220)
        if fig_ro: st.plotly_chart(fig_ro, use_container_width=True)

    # Gold / S&P
    section("Gold ÷ S&P 500 Ratio (Rising = Risk-Off / Safe Haven)")
    gold_h = get_history("GC=F","1y")
    spx_h  = get_history("^GSPC","1y")
    if gold_h is not None and spx_h is not None:
        gr = (gold_h["Close"] / spx_h["Close"]).dropna()
        gdf = gr.reset_index(); gdf.columns=["Date","Ratio"]
        col_g = "#16a34a" if gdf["Ratio"].iloc[-1] >= gdf["Ratio"].iloc[-2] else PALETTE[0]
        fig_gr = line_chart(gdf,"Ratio","Gold/S&P Ratio","#fbbf24",220)
        if fig_gr: st.plotly_chart(fig_gr, use_container_width=True)

    # Normalised YTD comparison
    section("YTD Normalised Performance (Base = 100)")
    COMPARE = {"S&P 500":"^GSPC","Gold":"GC=F","Bitcoin":"BTC-USD",
               "TLT (Bonds)":"TLT","DXY":"DX-Y.NYB","WTI Oil":"CL=F"}
    ch = get_multi_history(list(COMPARE.values()), "ytd")
    if ch is not None:
        fig_cmp = go.Figure()
        for i,(name,sym) in enumerate(COMPARE.items()):
            col = sym if sym in ch.columns else None
            if col is None: continue
            s = ch[col].dropna()
            if len(s) < 2: continue
            norm = s / s.iloc[0] * 100
            fig_cmp.add_trace(go.Scatter(
                x=norm.index, y=norm.values, mode="lines", name=name,
                line=dict(color=PALETTE[i%len(PALETTE)], width=2),
                hovertemplate=f"{name}: %{{y:.1f}}<extra></extra>",
            ))
        fig_cmp.add_hline(y=100, line_dash="dot", line_color="#2d3142", opacity=0.8)
        layout_cmp = base_layout(320)
        layout_cmp["showlegend"] = True
        layout_cmp["legend"] = dict(
            font=dict(color="#8891a5",size=10,family="Inter"),
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0.06)",
            borderwidth=1, x=0.01, y=0.99,
        )
        layout_cmp["yaxis"]["ticksuffix"] = ""
        fig_cmp.update_layout(**layout_cmp)
        st.plotly_chart(fig_cmp, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — PRIVATE CREDIT
# ══════════════════════════════════════════════════════════════════════════════
_AM_UNIVERSE = {
    "Blackstone":       "BX",
    "BlackRock":        "BLK",
    "Blue Owl Capital": "OWL",
    "Apollo":           "APO",
    "KKR":              "KKR",
    "Ares Management":  "ARES",
    "Carlyle Group":    "CG",
}
_BDC_UNIVERSE = {
    "Ares Capital":               "ARCC",
    "Blue Owl BDC":               "OBDC",
    "Blackstone Secured Lending": "BXSL",
    "FS KKR Capital":             "FSK",
    "Main Street Capital":        "MAIN",
    "Hercules Capital":           "HTGC",
    "Golub Capital BDC":          "GBDC",
}
_LOAN_CLO_UNIVERSE = {
    "Invesco Senior Loan ETF":     "BKLN",
    "SPDR Blackstone Senior Loan": "SRLN",
    "Janus Henderson AAA CLO":     "JAAA",
    "VanEck CLO ETF":              "CLOI",
}

with tabs[7]:
    pc_tabs = st.tabs(["🏢 Asset Managers", "📊 BDCs", "📉 Credit Spreads", "🏦 Senior Loans & CLOs", "📋 All"])

    # ── Asset Managers ────────────────────────────────────────────────────────
    with pc_tabs[0]:
        section("Alternative Asset Managers")
        am_q = get_bulk_quotes(list(_AM_UNIVERSE.values()))
        am_cols = st.columns(4)
        for i, (name, sym) in enumerate(_AM_UNIVERSE.items()):
            q = am_q.get(sym)
            with am_cols[i % 4]:
                stat_card(name, fmt_price(q["price"]) if q else "—",
                          q.get("pct_change") if q else None)

        _sk_am = "pc_am_chart"
        if _sk_am not in st.session_state:
            st.session_state[_sk_am] = list(_AM_UNIVERSE.values())[0]

        _am_dd_col, _ = st.columns([1, 3])
        with _am_dd_col:
            _am_names = list(_AM_UNIVERSE.keys())
            _am_sel   = next((n for n, s in _AM_UNIVERSE.items()
                              if s == st.session_state[_sk_am]), _am_names[0])
            _am_pick  = st.selectbox("Manager", _am_names, index=_am_names.index(_am_sel),
                                     key="am_dd", label_visibility="collapsed")
            if _AM_UNIVERSE[_am_pick] != st.session_state[_sk_am]:
                st.session_state[_sk_am] = _AM_UNIVERSE[_am_pick]
                st.rerun()

        tv_chart(st.session_state[_sk_am], height=400)

        section("Asset Manager Performance")
        df_am = get_performance_summary(_AM_UNIVERSE)
        if not df_am.empty:
            show_am = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                       if c in df_am.columns]
            st.dataframe(style_df(df_am[show_am]), use_container_width=True, hide_index=True)

        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:16px 20px;margin-top:4px;font-size:12px;color:#8891a5;line-height:1.8">
<b style="color:#c9d1e0;font-size:13px">📖 Why track asset managers here?</b><br><br>
These firms <b style="color:#c9d1e0">originate, manage, and deploy</b> the majority of global private credit capital.
Their stock prices serve as a real-time sentiment gauge for the private credit market —
rising prices signal strong fundraising, deal flow, and fee income, while a selloff often precedes a broader tightening in credit availability.
</div>
""", unsafe_allow_html=True)

    # ── BDCs ─────────────────────────────────────────────────────────────────
    with pc_tabs[1]:
        section("Business Development Companies")
        bdc_q = get_bulk_quotes(list(_BDC_UNIVERSE.values()))
        bdc_cols = st.columns(4)
        for i, (name, sym) in enumerate(_BDC_UNIVERSE.items()):
            q = bdc_q.get(sym)
            with bdc_cols[i % 4]:
                stat_card(name, fmt_price(q["price"]) if q else "—",
                          q.get("pct_change") if q else None)

        _sk_bdc = "pc_bdc_chart"
        if _sk_bdc not in st.session_state:
            st.session_state[_sk_bdc] = list(_BDC_UNIVERSE.values())[0]

        _bdc_dd_col, _ = st.columns([1, 3])
        with _bdc_dd_col:
            _bdc_names = list(_BDC_UNIVERSE.keys())
            _bdc_sel   = next((n for n, s in _BDC_UNIVERSE.items()
                               if s == st.session_state[_sk_bdc]), _bdc_names[0])
            _bdc_pick  = st.selectbox("BDC", _bdc_names, index=_bdc_names.index(_bdc_sel),
                                      key="bdc_dd", label_visibility="collapsed")
            if _BDC_UNIVERSE[_bdc_pick] != st.session_state[_sk_bdc]:
                st.session_state[_sk_bdc] = _BDC_UNIVERSE[_bdc_pick]
                st.rerun()

        tv_chart(st.session_state[_sk_bdc], height=400)

        section("BDC Performance")
        df_bdc = get_performance_summary(_BDC_UNIVERSE)
        if not df_bdc.empty:
            show_bdc = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                        if c in df_bdc.columns]
            st.dataframe(style_df(df_bdc[show_bdc]), use_container_width=True, hide_index=True)

        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:16px 20px;margin-top:4px;font-size:12px;color:#8891a5;line-height:1.8">
<b style="color:#c9d1e0;font-size:13px">📖 What is a BDC?</b><br><br>
Business Development Companies (BDCs) are <b style="color:#c9d1e0">publicly traded investment vehicles</b> that provide debt and equity financing
to middle-market companies — the same borrowers that private credit funds target.
They are required by law to distribute at least 90% of taxable income as dividends, making them
a <b style="color:#c9d1e0">high-yield, income-oriented</b> proxy for private credit returns.
</div>
""", unsafe_allow_html=True)

    # ── Credit Spreads ────────────────────────────────────────────────────────
    with pc_tabs[2]:
        section("Credit Spreads & Reference Rates")

        _cs_fred = {"HY OAS": "BAMLH0A0HYM2", "BBB OAS": "BAMLC0A4CBBB", "SOFR": "SOFR"}
        sp_cols = st.columns(3)
        for col, (label, sid) in zip(sp_cols, _cs_fred.items()):
            _s = get_fred_series(sid, lookback_days=5)
            val = float(_s.iloc[-1]) if _s is not None and len(_s) >= 1 else None
            chg = float((_s.iloc[-1] - _s.iloc[-2]) / _s.iloc[-2] * 100) \
                  if _s is not None and len(_s) >= 2 else None
            with col:
                stat_card(label, f"{val:.2f}%" if val is not None else "—", chg)

        hy_h   = get_fred_series("BAMLH0A0HYM2", lookback_days=365)
        bbb_h  = get_fred_series("BAMLC0A4CBBB", lookback_days=365)
        sofr_h = get_fred_series("SOFR",          lookback_days=365)

        if hy_h is not None and bbb_h is not None:
            fig_cr = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                subplot_titles=["HY OAS Spread (%)", "BBB OAS Spread (%)", "SOFR (%)"],
                vertical_spacing=0.07, row_heights=[0.34, 0.33, 0.33],
            )
            fig_cr.add_trace(go.Scatter(
                x=hy_h.index, y=hy_h, mode="lines",
                line=dict(color="#dc2626", width=2),
                hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}%<extra>HY OAS</extra>",
            ), row=1, col=1)
            fig_cr.add_trace(go.Scatter(
                x=bbb_h.index, y=bbb_h, mode="lines",
                line=dict(color="#f59e0b", width=2),
                hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}%<extra>BBB OAS</extra>",
            ), row=2, col=1)
            if sofr_h is not None:
                fig_cr.add_trace(go.Scatter(
                    x=sofr_h.index, y=sofr_h, mode="lines",
                    line=dict(color=PALETTE[0], width=2),
                    hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}%<extra>SOFR</extra>",
                ), row=3, col=1)
            for r in [1, 2, 3]:
                fig_cr.update_xaxes(showgrid=False, color=TICK_COLOR, zeroline=False,
                                    tickfont=dict(size=9, color=TICK_COLOR), row=r, col=1)
                fig_cr.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, color=TICK_COLOR,
                                    tickfont=dict(size=9), zeroline=False,
                                    ticksuffix="%", row=r, col=1)
            fig_cr.update_layout(
                height=520, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                margin=dict(l=4, r=4, t=30, b=4), showlegend=False,
                hovermode="x unified", font=dict(color=TICK_COLOR, size=10),
            )
            st.plotly_chart(fig_cr, use_container_width=True)

        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:16px 20px;margin-top:4px;font-size:12px;color:#8891a5;line-height:1.8">

<b style="color:#c9d1e0">HY OAS (High Yield Option-Adjusted Spread)</b><br>
The extra yield sub-investment grade bonds (BB and below) pay over US Treasuries. Private credit funds typically price slightly above this segment.
<b style="color:#dc2626">Spread widening</b> → risk-off, borrowers face higher funding costs, default fears rising.
<b style="color:#16a34a">Spread tightening</b> → risk appetite open, credit conditions easing, capital flowing into private credit.<br><br>

<b style="color:#c9d1e0">BBB OAS (Investment Grade — Bottom Rung)</b><br>
The lowest tier of investment grade — the segment private credit direct lending most directly competes with.
When BBB spreads widen, the gap between IG and HY narrows, creating opportunistic pricing for private lenders.
Historical thresholds: <b style="color:#f59e0b">&gt;150 bps</b> signals stress · <b style="color:#16a34a">&lt;100 bps</b> signals a tight / competitive environment.<br><br>

<b style="color:#c9d1e0">SOFR (Secured Overnight Financing Rate)</b><br>
Most private credit loans are structured as <b>SOFR + spread</b> (floating rate). As SOFR rises, interest income on existing portfolios increases automatically → higher NII for BDCs and private credit funds.
If SOFR declines, portfolio yields compress; combined with spread pressure on new deals, NII margins may narrow.
<b>Current context:</b> SOFR at ~4%+ is historically favorable for private credit returns.

</div>
""", unsafe_allow_html=True)

    # ── Senior Loans & CLOs ───────────────────────────────────────────────────
    with pc_tabs[3]:
        section("Senior Loans & CLOs")
        loan_q = get_bulk_quotes(list(_LOAN_CLO_UNIVERSE.values()))
        loan_cols = st.columns(len(_LOAN_CLO_UNIVERSE))
        for i, (name, sym) in enumerate(_LOAN_CLO_UNIVERSE.items()):
            q = loan_q.get(sym)
            with loan_cols[i]:
                stat_card(name, fmt_price(q["price"]) if q else "—",
                          q.get("pct_change") if q else None)

        _sk_loan = "pc_loan_chart"
        if _sk_loan not in st.session_state:
            st.session_state[_sk_loan] = list(_LOAN_CLO_UNIVERSE.values())[0]

        _loan_dd_col, _ = st.columns([1, 3])
        with _loan_dd_col:
            _loan_names = list(_LOAN_CLO_UNIVERSE.keys())
            _loan_sel   = next((n for n, s in _LOAN_CLO_UNIVERSE.items()
                                if s == st.session_state[_sk_loan]), _loan_names[0])
            _loan_pick  = st.selectbox("ETF", _loan_names, index=_loan_names.index(_loan_sel),
                                       key="loan_dd", label_visibility="collapsed")
            if _LOAN_CLO_UNIVERSE[_loan_pick] != st.session_state[_sk_loan]:
                st.session_state[_sk_loan] = _LOAN_CLO_UNIVERSE[_loan_pick]
                st.rerun()

        tv_chart(st.session_state[_sk_loan], height=400)

        section("Senior Loan & CLO ETF Performance")
        df_loan = get_performance_summary(_LOAN_CLO_UNIVERSE)
        if not df_loan.empty:
            show_loan = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                         if c in df_loan.columns]
            st.dataframe(style_df(df_loan[show_loan]), use_container_width=True, hide_index=True)

        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:16px 20px;margin-top:4px;font-size:12px;color:#8891a5;line-height:1.8">
<b style="color:#c9d1e0;font-size:13px">📖 Senior Loans & CLOs — what are they?</b><br><br>
<b style="color:#c9d1e0">Senior loans</b> (leveraged loans) are floating-rate, secured loans made to below-investment-grade companies —
structurally similar to what private credit funds originate, but syndicated and traded in public markets.
ETFs like BKLN and SRLN offer liquid exposure to this market and act as a <b style="color:#c9d1e0">real-time price discovery mechanism</b>
for private credit spreads, which are marked only quarterly.<br><br>
<b style="color:#c9d1e0">CLOs</b> (Collateralized Loan Obligations) repackage pools of leveraged loans into tranches.
AAA-rated CLO tranches (JAAA, CLOI) are among the highest-quality floating-rate instruments available —
their spread over SOFR reflects institutional demand for leveraged loan exposure with minimal credit risk.
Widening CLO AAA spreads are an early signal of stress in the broader leveraged finance market.
</div>
""", unsafe_allow_html=True)

    # ── All ───────────────────────────────────────────────────────────────────
    with pc_tabs[4]:
        section("All Asset Managers")
        df_all_am = get_performance_summary(_AM_UNIVERSE)
        if not df_all_am.empty:
            show_am = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                       if c in df_all_am.columns]
            st.dataframe(style_df(df_all_am[show_am]), use_container_width=True, hide_index=True)

        section("All BDCs")
        df_all_bdc = get_performance_summary(_BDC_UNIVERSE)
        if not df_all_bdc.empty:
            show_bdc = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                        if c in df_all_bdc.columns]
            st.dataframe(style_df(df_all_bdc[show_bdc]), use_container_width=True, hide_index=True)

        section("All Senior Loans & CLO ETFs")
        df_all_loan = get_performance_summary(_LOAN_CLO_UNIVERSE)
        if not df_all_loan.empty:
            show_al = [c for c in ["Name","Ticker","Price","1D %","5D %","1M %","YTD %","Rel. Vol."]
                       if c in df_all_loan.columns]
            st.dataframe(style_df(df_all_loan[show_al]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER + AUTO-REFRESH
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="dash-footer">
  DATA: Yahoo Finance (yfinance) &nbsp;·&nbsp;
  ETF Flow Proxy: Volume-based estimate, not official creation/redemption data &nbsp;·&nbsp;
  Auto-refresh: {AUTO_REFRESH_SECS}s &nbsp;·&nbsp;
  {now.strftime('%Y-%m-%d %H:%M UTC')}
</div>
""", unsafe_allow_html=True)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=AUTO_REFRESH_SECS * 1000, key="gmr")
except ImportError:
    pass
