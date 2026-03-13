"""
Global Markets Dashboard - Configuration
"""

INDICES = {
    "US": {
        "S&P 500": "^GSPC",
        "NASDAQ 100": "^NDX",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
    },
    "Europe": {
        "FTSE 100": "^FTSE",
        "DAX": "^GDAXI",
        "CAC 40": "^FCHI",
        "Euro Stoxx 50": "^STOXX50E",
        "MIB": "FTSEMIB.MI",
    },
    "Asia": {
        "Nikkei 225": "^N225",
        "Hang Seng": "^HSI",
    },
}

YIELDS = {
    "US 1M": "^IRX",
    "US 5Y": "^FVX",
    "US 10Y": "^TNX",
    "US 30Y": "^TYX",
    "DE 10Y": "^TNX",   # Proxy; real: use FRED or euronext
    "UK 10Y": "^TNX",   # Proxy
    "JP 10Y": "^TNX",   # Proxy
}

# Real yield symbols available in yfinance
YIELD_SYMBOLS = {
    "US 5Y": "^FVX",
    "US 10Y": "^TNX",
    "US 30Y": "^TYX",
}

COMMODITIES = {
    "Energy": {
        "WTI Crude": "CL=F",
        "Brent Crude": "BZ=F",
        "Natural Gas": "NG=F",
        "Heating Oil": "HO=F",
        "RBOB Gas": "RB=F",
    },
    "Precious Metals": {
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Platinum": "PL=F",
        "Palladium": "PA=F",
    },
    "Base Metals": {
        "Copper": "HG=F",
        "Aluminum": "ALI=F",
    },
    "Agricultural": {
        "Wheat": "ZW=F",
        "Corn": "ZC=F",
    },
}

CURRENCIES = {
    "Majors": {
        "DXY (Dollar Index)": "DX-Y.NYB",
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "USD/CHF": "USDCHF=X",
        "AUD/USD": "AUDUSD=X",
        "NZD/USD": "NZDUSD=X",
        "USD/CAD": "USDCAD=X",
    },
    "Emerging": {
        "USD/CNY": "USDCNY=X",
        "USD/BRL": "USDBRL=X",
        "USD/INR": "USDINR=X",
        "USD/TRY": "USDTRY=X",
        "USD/MXN": "USDMXN=X",
        "USD/KRW": "USDKRW=X",
        "USD/ZAR": "USDZAR=X",
        "USD/RUB": "USDRUB=X",
    },
}

CRYPTO = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "BNB": "BNB-USD",
    "Solana": "SOL-USD",
    "XRP": "XRP-USD",
    "Cardano": "ADA-USD",
    "Avalanche": "AVAX-USD",
    "Dogecoin": "DOGE-USD",
}

ETF_UNIVERSE = {
    "US Equity": {
        "SPY": {"name": "SPDR S&P 500", "benchmark": "^GSPC"},
        "QQQ": {"name": "Invesco NASDAQ 100", "benchmark": "^NDX"},
        "IWM": {"name": "iShares Russell 2000", "benchmark": "^RUT"},
        "VTI": {"name": "Vanguard Total Market", "benchmark": "^GSPC"},
        "VOO": {"name": "Vanguard S&P 500", "benchmark": "^GSPC"},
        "DIA": {"name": "SPDR Dow Jones", "benchmark": "^DJI"},
        "IVV": {"name": "iShares S&P 500", "benchmark": "^GSPC"},
    },
    "International": {
        "EFA": {"name": "iShares MSCI EAFE", "benchmark": "^STOXX50E"},
        "EEM": {"name": "iShares MSCI EM", "benchmark": "^HSI"},
        "VEA": {"name": "Vanguard Dev ex-US", "benchmark": "^FTSE"},
        "VWO": {"name": "Vanguard EM", "benchmark": "^HSI"},
        "IEMG": {"name": "iShares Core EM", "benchmark": "^HSI"},
        "EWJ": {"name": "iShares MSCI Japan", "benchmark": "^N225"},
        "FXI": {"name": "iShares China Large", "benchmark": "^HSI"},
        "EWZ": {"name": "iShares Brazil", "benchmark": "^BVSP"},
        "INDA": {"name": "iShares India", "benchmark": "^BSESN"},
    },
    "Fixed Income": {
        "TLT": {"name": "iShares 20+ Yr Treasury", "benchmark": "^TYX"},
        "IEF": {"name": "iShares 7-10 Yr Treasury", "benchmark": "^TNX"},
        "SHY": {"name": "iShares 1-3 Yr Treasury", "benchmark": "^IRX"},
        "AGG": {"name": "iShares Core Bond", "benchmark": "^TNX"},
        "BND": {"name": "Vanguard Total Bond", "benchmark": "^TNX"},
        "HYG": {"name": "iShares High Yield", "benchmark": "^TNX"},
        "LQD": {"name": "iShares Corp Bond", "benchmark": "^TNX"},
        "TIP": {"name": "iShares TIPS Bond", "benchmark": "^TNX"},
        "EMB": {"name": "iShares EM Bond", "benchmark": "^TNX"},
    },
    "Commodities": {
        "GLD":  {"name": "SPDR Gold Shares",       "benchmark": "GC=F"},
        "IAU":  {"name": "iShares Gold Trust",      "benchmark": "GC=F"},
        "GLDM": {"name": "SPDR Gold MiniShares",    "benchmark": "GC=F"},
        "SLV":  {"name": "iShares Silver Trust",    "benchmark": "SI=F"},
        "USO":  {"name": "US Oil Fund",             "benchmark": "CL=F"},
        "UNG":  {"name": "US Natural Gas Fund",     "benchmark": "NG=F"},
        "PDBC": {"name": "Invesco Commodity",       "benchmark": "CL=F"},
        "GSG":  {"name": "iShares Commodity",       "benchmark": "CL=F"},
        "CPER": {"name": "US Copper Index",         "benchmark": "HG=F"},
    },
    "Sector": {
        "XLK": {"name": "Technology", "benchmark": "^GSPC"},
        "XLF": {"name": "Financials", "benchmark": "^GSPC"},
        "XLE": {"name": "Energy", "benchmark": "^GSPC"},
        "XLV": {"name": "Healthcare", "benchmark": "^GSPC"},
        "XLI": {"name": "Industrials", "benchmark": "^GSPC"},
        "XLY": {"name": "Consumer Disc.", "benchmark": "^GSPC"},
        "XLP": {"name": "Consumer Staples", "benchmark": "^GSPC"},
        "XLRE": {"name": "Real Estate", "benchmark": "^GSPC"},
        "XLB": {"name": "Materials", "benchmark": "^GSPC"},
        "XLU": {"name": "Utilities", "benchmark": "^GSPC"},
        "XLC": {"name": "Communication", "benchmark": "^GSPC"},
    },
    "Crypto": {
        "IBIT":  {"name": "iShares Bitcoin Trust",   "benchmark": "BTC-USD"},
        "FBTC":  {"name": "Fidelity Bitcoin ETF",    "benchmark": "BTC-USD"},
        "BITB":  {"name": "Bitwise Bitcoin ETF",     "benchmark": "BTC-USD"},
        "ETHA":  {"name": "iShares Ethereum Trust",  "benchmark": "ETH-USD"},
        "FETH":  {"name": "Fidelity Ethereum ETF",   "benchmark": "ETH-USD"},
        "BITQ":  {"name": "Bitwise Crypto Industry", "benchmark": "BTC-USD"},
        "BLOK":  {"name": "Amplify Blockchain",      "benchmark": "BTC-USD"},
        "FDIG":  {"name": "Fidelity Crypto Industry","benchmark": "BTC-USD"},
        "DAPP":  {"name": "VanEck Digital Transform","benchmark": "BTC-USD"},
        "BKCH":  {"name": "Global X Blockchain",     "benchmark": "BTC-USD"},
    },
    "Private Credit": {
        "BKLN":  {"name": "Invesco Senior Loan ETF",     "benchmark": "^TNX"},
        "SRLN":  {"name": "SPDR Blackstone Senior Loan", "benchmark": "^TNX"},
        "JAAA":  {"name": "Janus Henderson AAA CLO",     "benchmark": "^TNX"},
        "CLOI":  {"name": "VanEck CLO ETF",              "benchmark": "^TNX"},
    },
    "Thematic": {
        "ARKK": {"name": "ARK Innovation", "benchmark": "^NDX"},
        "ARKG": {"name": "ARK Genomic Rev.", "benchmark": "^NDX"},
        "ICLN": {"name": "Clean Energy", "benchmark": "^GSPC"},
        "SOXX": {"name": "Semiconductor", "benchmark": "^NDX"},
        "IBB": {"name": "Biotech", "benchmark": "^GSPC"},
        "KBWB": {"name": "Bank ETF", "benchmark": "^GSPC"},
        "VNQ": {"name": "Real Estate REIT", "benchmark": "^GSPC"},
        "GDX": {"name": "Gold Miners", "benchmark": "GC=F"},
        "GDXJ": {"name": "Junior Gold Miners", "benchmark": "GC=F"},
        "JETS": {"name": "Airlines", "benchmark": "^GSPC"},
    },
}

SENTIMENT_SYMBOLS = {
    "VIX": "^VIX",
    "VIX9D": "^VIX9D",
    "VVIX": "^VVIX",
    "MOVE": "^TNX",   # MOVE index proxy (bond vol)
    "Gold/S&P Ratio": ["GC=F", "^GSPC"],
    "Oil/Gold Ratio": ["CL=F", "GC=F"],
    "TED Spread": ["^IRX"],
    "Risk On/Off": ["EEM", "TLT"],
}

CACHE_TTL_QUOTES = 120   # 2 min for fast quotes
CACHE_TTL_HISTORY = 600  # 10 min for historical data
CACHE_TTL_ETF = 300      # 5 min for ETF data
AUTO_REFRESH_SECS = 120
