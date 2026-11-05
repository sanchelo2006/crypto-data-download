"""
Exchange data fetcher factory module
"""

import time
import requests
from datetime import datetime
import pandas as pd
import config
from logger import ErrorLogger
from coinbase_fetcher import CoinbaseDataFetcher

# Try to import Bybit
try:
    from pybit.unified_trading import HTTP
    BYBIT_AVAILABLE = True
except ImportError:
    BYBIT_AVAILABLE = False
    print("Warning: pybit not installed. Bybit support disabled.")


class BybitDataFetcher:
    """Fetch OHLCV data from Bybit API (Primary Exchange)"""
    
    def __init__(self, logger=None):
        if not BYBIT_AVAILABLE:
            raise ImportError("pybit library not installed. Run: pip install pybit")
        
        self.session = HTTP(testnet=False)
        self.logger = logger if logger is not None else ErrorLogger()
    
    def validate_symbol(self, symbol: str, category: str = "spot") -> tuple:
        """Validate Bybit symbol format"""
        symbol_upper = symbol.upper()
        
        # Check if ends with valid quote currency
        for quote in config.VALID_QUOTE_CURRENCIES:
            if symbol_upper.endswith(quote):
                return True, f"✓ Valid Bybit symbol: {symbol_upper}", symbol_upper[:-len(quote)], quote
        
        return False, f"✗ Invalid symbol format. Use BTCUSDT, ETHUSDT", None, None
    
    def fetch_ohlcv(self, symbol: str, interval: str, start_date: datetime,
                    end_date: datetime, category: str = "spot",
                    progress_callback=None) -> pd.DataFrame:
        """
        Fetch OHLCV data from Bybit with batch processing
        """
        
        # Map timeframe to Bybit format
        bybit_interval = config.BYBIT_TIMEFRAME_MAP.get(interval, interval)
        interval_seconds = config.INTERVAL_SECONDS.get(interval, 3600)
        interval_ms = interval_seconds * 1000
        
        # Convert dates to milliseconds timestamps
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)
        
        all_candles = []
        current_end = end_timestamp
        batch_count = 0
        max_retries = config.API_RETRY_COUNT
        
        print(f"\nStarting Bybit batch fetch from {start_date} to {end_date}")
        print(f"Symbol: {symbol}, Category: {category}")
        
        # Calculate total candles needed for progress
        total_needed = int((end_timestamp - start_timestamp) / interval_ms) + 100
        
        while current_end > start_timestamp:
            batch_count += 1
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Calculate remaining candles
                    remaining_ms = current_end - start_timestamp
                    estimated_candles = int(remaining_ms / interval_ms) + 10
                    fetch_limit = min(200, estimated_candles)
                    
                    # Fetch kline data
                    response = self.session.get_kline(
                        category=category,
                        symbol=symbol,
                        interval=bybit_interval,
                        end=current_end,
                        limit=fetch_limit
                    )
                    
                    if response["retCode"] == 0:
                        candles = response["result"]["list"]
                        
                        if not candles:
                            current_end = start_timestamp
                            break
                        
                        all_candles.extend(candles)
                        
                        # Get oldest candle timestamp
                        oldest_timestamp = int(candles[-1][0])
                        current_end = oldest_timestamp - 1
                        
                        # Update progress
                        if progress_callback:
                            total_fetched = len(all_candles)
                            progress = min(100, int(total_fetched / total_needed * 100))
                            progress_callback(progress, total_fetched, total_needed)
                        
                        # Check if we've reached the start
                        if oldest_timestamp <= start_timestamp:
                            current_end = start_timestamp
                            break
                        
                        time.sleep(0.2)
                        break
                        
                    else:
                        retry_count += 1
                        error_msg = f"Bybit API Error (attempt {retry_count}): {response.get('retMsg', 'Unknown')}"
                        print(error_msg)
                        
                        if retry_count >= max_retries:
                            if self.logger:
                                self.logger.log_error(error_msg, response)
                            return None
                        time.sleep(1)
                        
                except Exception as e:
                    retry_count += 1
                    print(f"Exception in batch {batch_count}: {str(e)}")
                    
                    if retry_count >= max_retries:
                        if self.logger:
                            self.logger.log_exception(e, f"fetching data from Bybit for {symbol}")
                        return None
                    time.sleep(1)
        
        if not all_candles:
            return None
        
        # Create DataFrame
        df = pd.DataFrame(all_candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # Convert data types
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = df[col].astype(float)
        
        # Clean and sort
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Filter to requested range
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        print(f"Total candles fetched from Bybit: {len(df)}")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    
    def get_public_trading_records(self, category: str, symbol: str, limit: int = 500) -> pd.DataFrame:
        try:
            response = self.session.get_public_trade_history(
                category=category,
                symbol=symbol,
                limit=limit
            )
            if response["retCode"] != 0:
                self.logger.log_error(f"Trading records API error: {response}")
                return pd.DataFrame()
            data = response["result"]["list"]
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            # Поиск колонки с временем
            time_candidates = ['execTime', 'tradeTime', 'timestamp', 'time']
            time_col = None
            for col in time_candidates:
                if col in df.columns:
                    time_col = col
                    break
            if time_col:
                df['timestamp'] = pd.to_datetime(df[time_col].astype(int), unit='ms', errors='coerce')
            else:
                df['timestamp'] = pd.NaT
            # Удаляем строки с некорректной меткой времени
            df = df.dropna(subset=['timestamp'])
            if df.empty:
                return pd.DataFrame()
            df.rename(columns={
                'price': 'price',
                'size': 'volume',
                'side': 'side'
            }, inplace=True)
            df = df[['timestamp', 'price', 'volume', 'side']]
            df['price'] = df['price'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
        except Exception as e:
            self.logger.log_exception(e, "get_public_trading_records")
            return pd.DataFrame()

    def get_orderbook(self, category: str, symbol: str, limit: int = 25) -> dict:
        """
        Получить стакан ордеров.
        :param category: spot, linear, inverse, option
        :param symbol: например BTCUSDT
        :param limit: глубина стакана (для спота и фьючерсов до 1000, для опционов до 25)
        :return: словарь с результатом API
        """
        try:
            response = self.session.get_orderbook(
                category=category,
                symbol=symbol,
                limit=limit
            )
            if response["retCode"] != 0:
                self.logger.log_error(f"Orderbook API error: {response}")
                return {}
            return response.get("result", {})
        except Exception as e:
            self.logger.log_exception(e, "get_orderbook")
            return {}

class ExchangeFactory:
    """Factory class to get the appropriate exchange fetcher"""
    
    @staticmethod
    def get_fetcher(exchange: str, logger=None):
        """Return the appropriate exchange fetcher"""
        if exchange == config.EXCHANGE_BYBIT:
            if not BYBIT_AVAILABLE:
                raise ImportError("Bybit support requires pybit library.\nInstall with: pip install pybit")
            return BybitDataFetcher(logger)
        elif exchange == config.EXCHANGE_COINBASE:
            return CoinbaseDataFetcher(logger)
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")
    
    @staticmethod
    def validate_symbol(exchange: str, symbol: str, category: str = "spot") -> tuple:
        """Validate symbol for specific exchange"""
        if exchange == config.EXCHANGE_BYBIT:
            fetcher = BybitDataFetcher()
            return fetcher.validate_symbol(symbol, category)
        elif exchange == config.EXCHANGE_COINBASE:
            fetcher = CoinbaseDataFetcher()
            return fetcher.validate_symbol(symbol, category)
        else:
            return False, f"Unsupported exchange: {exchange}", None, None
    
    @staticmethod
    def get_exchange_info(exchange: str) -> dict:
        """Get information about an exchange"""
        return config.EXCHANGES.get(exchange, {})
    
    @staticmethod
    def get_supported_timeframes(exchange: str) -> list:
        """Get supported timeframes"""
        return list(config.INTERVAL_SECONDS.keys())


# Simple functions
def get_fetcher(exchange=config.DEFAULT_EXCHANGE, logger=None):
    """Get exchange fetcher instance"""
    return ExchangeFactory.get_fetcher(exchange, logger)


def test_connection(exchange=config.DEFAULT_EXCHANGE, logger=None) -> tuple:
    """Test connection to exchange"""
    fetcher = get_fetcher(exchange, logger)
    
    try:
        if exchange == config.EXCHANGE_BYBIT:
            # Test Bybit connection
            response = fetcher.session.get_kline(
                category="spot",
                symbol="BTCUSDT",
                interval="1",
                limit=1
            )
            if response.get("retCode") == 0:
                return True, "Connected to Bybit successfully", None
            else:
                return False, f"Bybit API error: {response.get('retMsg', 'Unknown')}", None
                
        elif exchange == config.EXCHANGE_COINBASE:
            # Test Coinbase connection
            import requests
            response = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data.get('price', 'unknown')
                return True, f"Connected to Coinbase - BTC: ${price}", None
            else:
                return False, "Cannot connect to Coinbase", None
                
    except Exception as e:
        return False, f"Connection error: {str(e)}", None