"""
Technical indicators calculation module
Matches Bybit's indicator calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

class TechnicalIndicators:
    """Calculate technical indicators for OHLCV data matching Bybit's implementation"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame
        
        Parameters:
        - df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        # Ensure data is sorted chronologically (oldest first)
        self.df = df.sort_values('timestamp').reset_index(drop=True).copy()
        self._validate_data()
        self._check_data_quality()
    
    def _validate_data(self):
        """Validate that required columns exist"""
        required_cols = ['open', 'high', 'low', 'close']
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
    
    def _check_data_quality(self):
        """Check if data is properly sorted"""
        if not self.df['timestamp'].is_monotonic_increasing:
            print("Warning: Data not sorted chronologically. Sorting...")
            self.df = self.df.sort_values('timestamp').reset_index(drop=True)
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """
        Calculate RSI using EMA method (matches Bybit)
        
        Note: First (period) values will be NaN because we need enough historical data
        """
        close = self.df['close']
        
        # Calculate price changes
        delta = close.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate EMA of gains and losses
        alpha = 1.0 / period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # First 'period' values should be NaN (not enough data)
        if len(rsi) > period:
            rsi.iloc[:period] = np.nan
        
        return rsi
    
    def calculate_adx(self, period: int = 14) -> pd.Series:
        """
        Calculate ADX using Wilder's smoothing (matches Bybit)
        
        Note: First (period*2) values will be NaN
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        # 1. Calculate True Range (TR)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 2. Calculate Directional Movements (+DM and -DM)
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = pd.Series(0.0, index=self.df.index)
        minus_dm = pd.Series(0.0, index=self.df.index)
        
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
        
        # 3. Apply Wilder's smoothing
        alpha = 1.0 / period
        tr_smooth = tr.ewm(alpha=alpha, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(alpha=alpha, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(alpha=alpha, adjust=False).mean()
        
        # 4. Calculate +DI and -DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # 5. Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # 6. Apply Wilder's smoothing to DX to get ADX
        adx = dx.ewm(alpha=alpha, adjust=False).mean()
        
        # First (period*2) values should be NaN
        if len(adx) > period * 2:
            adx.iloc[:period * 2] = np.nan
        
        return adx
    
    def calculate_ema(self, period: int = 50) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)
        
        Note: First 'period' values will be NaN
        """
        close = self.df['close']
        ema = close.ewm(span=period, adjust=False).mean()
        
        # First 'period' values should be NaN
        if len(ema) > period:
            ema.iloc[:period] = np.nan
        
        return ema
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Note: First 'slow' values will be NaN
        """
        close = self.df['close']
        
        # Calculate EMAs
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        # First 'slow' values should be NaN
        if len(macd_line) > slow:
            macd_line.iloc[:slow] = np.nan
            signal_line.iloc[:slow] = np.nan
            histogram.iloc[:slow] = np.nan
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, period: int = 20, num_std: int = 2) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Note: First 'period' values will be NaN
        """
        close = self.df['close']
        
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        
        # First 'period' values should be NaN
        if len(middle) > period:
            middle.iloc[:period] = np.nan
            upper.iloc[:period] = np.nan
            lower.iloc[:period] = np.nan
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def add_all_indicators(self, include_macd: bool = False, include_bb: bool = False) -> pd.DataFrame:
        """
        Add commonly used indicators to the DataFrame
        
        Returns DataFrame with added indicator columns
        """
        # Add basic indicators (these will have NaN at the beginning)
        self.df['RSI'] = self.calculate_rsi(period=14)
        self.df['ADX'] = self.calculate_adx(period=14)
        self.df['EMA_21'] = self.calculate_ema(period=21)
        self.df['EMA_50'] = self.calculate_ema(period=50)
        
        # Add MACD if requested
        if include_macd:
            macd = self.calculate_macd()
            self.df['MACD'] = macd['macd']
            self.df['MACD_Signal'] = macd['signal']
            self.df['MACD_Histogram'] = macd['histogram']
        
        # Add Bollinger Bands if requested
        if include_bb:
            bb = self.calculate_bollinger_bands()
            self.df['BB_Upper'] = bb['upper']
            self.df['BB_Middle'] = bb['middle']
            self.df['BB_Lower'] = bb['lower']
        
        return self.df
    
    def validate_indicator_data(self) -> Dict[str, int]:
        """
        Check how many valid values each indicator has
        Returns dictionary with indicator names and valid counts
        """
        results = {}
        
        if 'RSI' in self.df.columns:
            results['RSI'] = self.df['RSI'].notna().sum()
        if 'ADX' in self.df.columns:
            results['ADX'] = self.df['ADX'].notna().sum()
        if 'EMA_21' in self.df.columns:
            results['EMA_21'] = self.df['EMA_21'].notna().sum()
        if 'EMA_50' in self.df.columns:
            results['EMA_50'] = self.df['EMA_50'].notna().sum()
        if 'MACD' in self.df.columns:
            results['MACD'] = self.df['MACD'].notna().sum()
        
        return results
    
    def get_indicator_info(self) -> str:
        """Get information about indicator requirements"""
        info = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                    TECHNICAL INDICATOR REQUIREMENTS                        ║
╚═══════════════════════════════════════════════════════════════════════════╝

Indicators need historical data to calculate. The first N values will be NaN:

┌─────────────────┬──────────────┬──────────────────────────────────────────┐
│ Indicator       │ Period       │ First N Values NaN                       │
├─────────────────┼──────────────┼──────────────────────────────────────────┤
│ RSI             │ 14           │ First 14 candles                         │
│ ADX             │ 14           │ First 28 candles (needs 2x period)       │
│ EMA 21          │ 21           │ First 21 candles                         │
│ EMA 50          │ 50           │ First 50 candles                         │
│ MACD            │ 12/26/9      │ First 26 candles                         │
│ Bollinger Bands │ 20           │ First 20 candles                         │
└─────────────────┴──────────────┴──────────────────────────────────────────┘

IMPORTANT: 
- Values are calculated from OLDEST to NEWEST (chronological order)
- First rows will be NaN because there's not enough historical data
- To get valid indicator values for your target date range:
  
  Example: To get RSI for last 30 days of data:
    1. Fetch 44 days of data (30 + 14 lookback)
    2. Calculate indicators
    3. Filter to last 30 days
  
TIP: Always fetch more data than you need, then filter to your desired range.
"""
        return info