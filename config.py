"""
Configuration constants for the Crypto Data Fetcher
"""

# Exchange types
EXCHANGE_BYBIT = "bybit"
EXCHANGE_COINBASE = "coinbase"

EXCHANGES = {
    EXCHANGE_BYBIT: {
        'name': 'Bybit',
        'description': 'International exchange, USDT prices (works globally)',
        'symbol_format': 'BTCUSDT, ETHUSDT',
        'example': 'BTCUSDT',
        'pairs': 'USDT pairs',
        'works_in_usa': False,
        'common_coins': [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT",
            "XRPUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT", "LINKUSDT",
            "LTCUSDT", "UNIUSDT", "ATOMUSDT", "ALGOUSDT", "FILUSDT",
            "ICPUSDT", "NEARUSDT", "VETUSDT", "SANDUSDT", "MANAUSDT",
            "AXSUSDT", "AAVEUSDT", "EOSUSDT", "XTZUSDT", "MKRUSDT",
            "COMPUSDT", "GRTUSDT", "ENJUSDT", "ZECUSDT", "BCHUSDT"
        ]
    },
    EXCHANGE_COINBASE: {
        'name': 'Coinbase',
        'description': 'USA-regulated exchange, USD prices (for USA users)',
        'symbol_format': 'BTC-USD, ETH-USD',
        'example': 'BTC-USD',
        'pairs': 'USD pairs',
        'works_in_usa': True,
        'common_coins': [
            "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOGE-USD",
            "XRP-USD", "DOT-USD", "AVAX-USD", "MATIC-USD", "LINK-USD",
            "LTC-USD", "UNI-USD", "ATOM-USD", "ALGO-USD", "FIL-USD",
            "ICP-USD", "NEAR-USD", "VET-USD", "SAND-USD", "MANA-USD",
            "AXS-USD", "AAVE-USD", "EOS-USD", "XTZ-USD", "MKR-USD",
            "COMP-USD", "GRT-USD", "ENJ-USD", "ZEC-USD", "BCH-USD"
        ]
    }
}

DEFAULT_EXCHANGE = EXCHANGE_BYBIT  # Bybit works globally

# Valid quote currencies for all exchanges
VALID_QUOTE_CURRENCIES = ["USDT", "USDC", "USD"]

# Exchange-specific quotes
BYBIT_QUOTES = ["USDT", "USDC"]
COINBASE_QUOTES = ["USD"]

# Interval in seconds for each timeframe
INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
    "1M": 2592000
}

# Timeframe mapping for Bybit
BYBIT_TIMEFRAME_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "1d": "D",
    "1w": "W",
    "1M": "M"
}

# API settings
API_MAX_LIMIT = 200
API_RETRY_COUNT = 3
API_RETRY_DELAY = 1
API_BATCH_DELAY = 0.2

# Logging settings
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 4

# Default values
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_MARKET = "spot"
DEFAULT_TIMEFRAME = "1h"
DEFAULT_DAYS_BACK = 30

# Technical indicator parameters
INDICATORS = {
    'RSI': {'period': 14},
    'ADX': {'period': 14},
    'EMA': {'fast': 21, 'slow': 50},
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'BB': {'period': 20, 'std': 2}
}

# GUI settings
WINDOW_WIDTH = 950
WINDOW_HEIGHT = 800
CONSOLE_HEIGHT = 12
PREVIEW_HEIGHT = 10

# Add timeframe warnings to config
TIMEFRAME_WARNINGS = {
    "1m": "⚠ 1-minute data limited to last 24 hours on Coinbase",
    "5m": "⚠ 5-minute data limited to last 7 days on Coinbase", 
    "15m": "⚠ 15-minute data limited to last 30 days on Coinbase",
    "30m": "⚠ 30-minute data may be limited on Coinbase",
    "1h": "✓ Up to 90 days of 1-hour data available",
    "4h": "✓ Up to 180 days of 4-hour data available",
    "1d": "✓ Up to 365 days of daily data available",
}