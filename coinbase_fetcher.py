"""
Coinbase API data fetcher - Works in USA, no VPN needed
"""

import requests
from datetime import datetime, timedelta
import pandas as pd
import time
import config
from logger import ErrorLogger

class CoinbaseDataFetcher:
    """Fetch OHLCV data from Coinbase API (USA-friendly)"""
    
    def __init__(self, logger=None):
        self.base_url = "https://api.exchange.coinbase.com"
        self.logger = logger if logger is not None else ErrorLogger()
        
        # Coinbase data limits per timeframe
        self.timeframe_limits = {
            "1m": {"max_hours": 24, "max_candles": 1440, "description": "Only last 24 hours (1440 candles)"},
            "5m": {"max_hours": 168, "max_candles": 2016, "description": "Only last 7 days (2016 candles)"},
            "15m": {"max_hours": 720, "max_candles": 2880, "description": "Only last 30 days (2880 candles)"},
            "1h": {"max_hours": 2160, "max_candles": 2160, "description": "Up to 90 days (2160 candles)"},
            "6h": {"max_hours": 4320, "max_candles": 720, "description": "Up to 180 days (720 candles)"},
            "1d": {"max_hours": 8760, "max_candles": 365, "description": "Up to 365 days (365 candles)"},
        }
    
    def validate_symbol(self, symbol: str, category: str = "spot") -> tuple:
        """Validate symbol format for Coinbase"""
        symbol_upper = symbol.upper()
        
        # Remove any dashes for checking
        clean_symbol = symbol_upper.replace("-", "")
        
        # Check if ends with valid quote currency
        for quote in ["USD", "USDT", "USDC"]:
            if clean_symbol.endswith(quote):
                base = clean_symbol[:-len(quote)]
                formatted = f"{base}-{quote}"
                return True, f"✓ Valid symbol: {formatted}", base, quote
        
        # Special handling for BTC-USD format
        if "-" in symbol_upper:
            parts = symbol_upper.split("-")
            if len(parts) == 2 and parts[1] in ["USD", "USDT", "USDC"]:
                return True, f"✓ Valid symbol: {symbol_upper}", parts[0], parts[1]
        
        return False, f"✗ Invalid symbol format. Use BTC-USD, ETH-USD", None, None
    
    def validate_date_range(self, start_date: datetime, end_date: datetime, interval: str) -> tuple:
        """
        Validate if date range is within Coinbase limits for the timeframe
        Returns (is_valid, message, adjusted_start_date)
        """
        # Get limit for this timeframe
        limit_info = self.timeframe_limits.get(interval, {"max_hours": 8760})
        max_hours = limit_info["max_hours"]
        
        # Calculate date range in hours
        hours = (end_date - start_date).total_seconds() / 3600
        
        if hours > max_hours:
            # Calculate adjusted start date
            adjusted_start = end_date - timedelta(hours=max_hours)
            return (False, 
                    f"❌ For {interval} timeframe, Coinbase only supports {limit_info['description']}\n\n"
                    f"Your range: {hours:.1f} hours\n"
                    f"Maximum allowed: {max_hours} hours\n\n"
                    f"Adjusting start date to: {adjusted_start.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Use a larger timeframe for longer periods.",
                    adjusted_start)
        
        return True, f"✓ Date range OK ({hours:.1f} hours, {limit_info['description']})", start_date
    
    def fetch_ohlcv(self, symbol: str, interval: str, start_date: datetime,
                    end_date: datetime, category: str = "spot",
                    progress_callback=None) -> pd.DataFrame:
        """
        Fetch OHLCV data from Coinbase with partial result saving on error
        """
        
        # Validate and possibly adjust date range
        is_valid, message, adjusted_start = self.validate_date_range(start_date, end_date, interval)
        
        if not is_valid:
            print(message)
            start_date = adjusted_start
            print(f"Using adjusted start date: {start_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Format symbol for Coinbase (BTC-USD)
        symbol_upper = symbol.upper()
        
        # If symbol is like BTCUSD, convert to BTC-USD
        if "-" not in symbol_upper:
            for quote in ["USD", "USDT", "USDC"]:
                if symbol_upper.endswith(quote):
                    base = symbol_upper[:-len(quote)]
                    coinbase_symbol = f"{base}-{quote}"
                    break
            else:
                coinbase_symbol = symbol_upper
        else:
            coinbase_symbol = symbol_upper
        
        # Map interval to granularity (seconds)
        granularity_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "6h": 21600,
            "1d": 86400,
        }
        
        granularity = granularity_map.get(interval, 3600)
        
        # Calculate number of candles needed
        interval_seconds = config.INTERVAL_SECONDS.get(interval, 3600)
        total_seconds = (end_date - start_date).total_seconds()
        total_candles_needed = int(total_seconds / interval_seconds) + 100
        
        all_candles = []
        failed_batch = None
        current_start = start_date
        batch_count = 0
        
        print(f"\n" + "="*60)
        print(f"Starting Coinbase fetch")
        print(f"Symbol: {symbol} -> {coinbase_symbol}")
        print(f"Timeframe: {interval} (granularity: {granularity} seconds)")
        print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"Total candles needed: ~{total_candles_needed}")
        print("="*60)
        
        # For 1m and 5m timeframes, fetch in smaller chunks
        if interval in ["1m", "5m"]:
            # Fetch in 1-hour chunks for 1m, 6-hour chunks for 5m
            if interval == "1m":
                chunk_hours = 1
            else:  # 5m
                chunk_hours = 6
            
            chunk_seconds = chunk_hours * 3600
            
            while current_start < end_date:
                batch_end = min(current_start + timedelta(seconds=chunk_seconds), end_date)
                batch_count += 1
                
                try:
                    url = f"{self.base_url}/products/{coinbase_symbol}/candles"
                    params = {
                        'granularity': granularity,
                        'start': current_start.isoformat(),
                        'end': batch_end.isoformat()
                    }
                    
                    print(f"Batch {batch_count}: {current_start.strftime('%Y-%m-%d %H:%M')} to {batch_end.strftime('%Y-%m-%d %H:%M')}")
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        candles = response.json()
                        
                        if candles:
                            for candle in candles:
                                all_candles.append({
                                    'timestamp': candle[0],
                                    'open': float(candle[3]),
                                    'high': float(candle[2]),
                                    'low': float(candle[1]),
                                    'close': float(candle[4]),
                                    'volume': float(candle[5]),
                                    'turnover': float(candle[5]) * float(candle[4])
                                })
                            print(f"  ✓ Fetched {len(candles)} candles (total: {len(all_candles)})")
                        else:
                            print(f"  ℹ No data for this period")
                        
                        # Update progress
                        if progress_callback:
                            total_fetched = len(all_candles)
                            progress = min(100, int(total_fetched / total_candles_needed * 100))
                            progress_callback(progress, total_fetched, total_candles_needed)
                        
                    elif response.status_code == 500:
                        failed_batch = batch_count
                        print(f"  ❌ Server Error (500) - Stopping at batch {batch_count}")
                        print(f"  Successfully fetched {len(all_candles)} candles before error.")
                        break
                        
                    elif response.status_code == 400:
                        error_text = response.text
                        print(f"  ❌ Bad Request (400): {error_text}")
                        print(f"  This usually means the date range is too large or symbol is invalid.")
                        print(f"  Successfully fetched {len(all_candles)} candles before error.")
                        break
                        
                    else:
                        print(f"  ❌ API Error {response.status_code}")
                        print(f"  Successfully fetched {len(all_candles)} candles before error.")
                        break
                    
                    current_start = batch_end
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"  ❌ Exception: {str(e)}")
                    print(f"  Successfully fetched {len(all_candles)} candles before error.")
                    break
                    
        else:
            # For larger timeframes, fetch in batches
            max_candles_per_batch = 300
            current_end = end_date
            batch_count = 0
            
            while current_end > start_date:
                batch_count += 1
                retry_count = 0
                
                while retry_count < 3:
                    try:
                        # Calculate start time for this batch
                        batch_start = max(start_date, current_end - timedelta(seconds=granularity * max_candles_per_batch))
                        
                        url = f"{self.base_url}/products/{coinbase_symbol}/candles"
                        params = {
                            'granularity': granularity,
                            'start': batch_start.isoformat(),
                            'end': current_end.isoformat()
                        }
                        
                        response = requests.get(url, params=params, timeout=30)
                        
                        if response.status_code == 200:
                            candles = response.json()
                            
                            if not candles:
                                current_end = start_date
                                break
                            
                            for candle in candles:
                                all_candles.append({
                                    'timestamp': candle[0],
                                    'open': float(candle[3]),
                                    'high': float(candle[2]),
                                    'low': float(candle[1]),
                                    'close': float(candle[4]),
                                    'volume': float(candle[5]),
                                    'turnover': float(candle[5]) * float(candle[4])
                                })
                            
                            # Update current_end to oldest candle time
                            if candles:
                                oldest_time = candles[-1][0]
                                current_end = datetime.fromtimestamp(oldest_time)
                            else:
                                current_end = start_date
                            
                            # Update progress
                            if progress_callback:
                                total_fetched = len(all_candles)
                                progress = min(100, int(total_fetched / total_candles_needed * 100))
                                progress_callback(progress, total_fetched, total_candles_needed)
                            
                            print(f"Batch {batch_count}: Fetched {len(candles)} candles (total: {len(all_candles)})")
                            time.sleep(0.2)
                            break
                            
                        elif response.status_code == 500:
                            print(f"❌ Server Error (500) - Stopping at batch {batch_count}")
                            print(f"Successfully fetched {len(all_candles)} candles before error.")
                            failed_batch = batch_count
                            break
                            
                        elif response.status_code == 400:
                            error_text = response.text
                            print(f"❌ Bad Request (400): {error_text}")
                            print(f"Successfully fetched {len(all_candles)} candles before error.")
                            failed_batch = batch_count
                            break
                            
                        else:
                            retry_count += 1
                            print(f"API Error {response.status_code}, attempt {retry_count}")
                            if retry_count >= 3:
                                print(f"Successfully fetched {len(all_candles)} candles before error.")
                                failed_batch = batch_count
                                break
                            time.sleep(1)
                            
                    except Exception as e:
                        retry_count += 1
                        print(f"Exception: {str(e)}, attempt {retry_count}")
                        if retry_count >= 3:
                            print(f"Successfully fetched {len(all_candles)} candles before error.")
                            failed_batch = batch_count
                            break
                        time.sleep(1)
                
                if failed_batch:
                    break
        
        if not all_candles:
            print("No candles fetched")
            return None
        
        # Create DataFrame from collected candles
        df = pd.DataFrame(all_candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='s')
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Remove duplicates if any
        df = df.drop_duplicates(subset=['timestamp'])
        
        # Filter to requested range
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        print(f"\n" + "="*60)
        
        if failed_batch:
            print(f"⚠ PARTIAL DATA FETCHED - Error at batch {failed_batch}")
            print(f"✓ Successfully fetched {len(df)} candles ({len(df)/total_candles_needed*100:.1f}% of requested)")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"\nNote: Some data could not be fetched due to server error.")
            print(f"You can try again with a smaller date range.")
        else:
            print(f"✓ Successfully fetched all {len(df)} candles")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"Data completeness: {len(df)}/{total_candles_needed} candles ({len(df)/total_candles_needed*100:.1f}%)")
        
        print("="*60)
        
        return df