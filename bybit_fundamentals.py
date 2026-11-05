from pybit.unified_trading import HTTP
import pandas as pd
from datetime import datetime
import requests

class FearGreedFetcher:
    def __init__(self):
        pass

    def get_historical_data(self, start_time: int = None, end_time: int = None):
        """
        start_time / end_time – unix timestamp in milliseconds.
        Возвращает DataFrame с колонками timestamp, Fear_Greed_Value, Market_Sentiment.
        """
        url = "https://api.alternative.me/fng/?limit=0"
        try:
            resp = requests.get(url, timeout=10).json()
            data = resp.get("data", [])
            if not data:
                return pd.DataFrame()
            rows = []
            for item in data:
                ts_sec = int(item['timestamp'])
                dt = pd.to_datetime(ts_sec, unit='s')
                if start_time and dt.timestamp() * 1000 < start_time:
                    continue
                if end_time and dt.timestamp() * 1000 > end_time:
                    continue
                rows.append({
                    'timestamp': dt,
                    'Fear_Greed_Value': float(item['value']),
                    'Market_Sentiment': item['value_classification']
                })
            return pd.DataFrame(rows).sort_values('timestamp')
        except Exception as e:
            print(f"Fear & Greed error: {e}")
            return pd.DataFrame()

class BybitFundamentals:
    def __init__(self, testnet: bool = False):
        self.session = HTTP(testnet=testnet)
        self.fg_fetcher = FearGreedFetcher()

    def fetch_open_interest(self, symbol: str, interval: str = "1h", limit: int = 200):
        resp = self.session.get_open_interest(
            category="linear",
            symbol=symbol,
            intervalTime=interval,
            limit=limit
        )
        data = resp.get("result", {}).get("list", [])
        return self._list_to_df(data, "openInterest", ts_col="timestamp")

    def fetch_funding_rate(self, symbol: str, start_time: int = None, end_time: int = None, limit: int = 200):
        resp = self.session.get_funding_rate_history(
            category="linear",
            symbol=symbol,
            startTime=start_time,
            endTime=end_time,
            limit=limit
        )
        data = resp.get("result", {}).get("list", [])
        return self._list_to_df(data, "fundingRate", ts_col="fundingRateTimestamp")

    def fetch_ls_ratio(self, symbol: str, period: str = "1h", limit: int = 200):
        resp = self.session.get_long_short_ratio(
            category="linear",
            symbol=symbol,
            period=period,
            limit=limit
        )
        data = resp.get("result", {}).get("list", [])
        if not data:
            return pd.DataFrame()
        rows = []
        for item in data:
            buy = float(item.get("buyRatio", 0))
            sell = float(item.get("sellRatio", 0))
            ratio = buy / sell if sell != 0 else 0
            rows.append({
                "timestamp": int(item["timestamp"]),
                "longShortRatio": ratio
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df[["timestamp", "longShortRatio"]] if not df.empty else pd.DataFrame()

    def fetch_fear_greed(self, start_time: int = None, end_time: int = None):
        """Возвращает исторические данные Fear & Greed за указанный диапазон"""
        return self.fg_fetcher.get_historical_data(start_time, end_time)
    
    def _list_to_df(self, records, value_col, ts_col="timestamp"):
        if not records:
            return pd.DataFrame(columns=["timestamp", value_col])
        df = pd.DataFrame(records)
        if ts_col in df.columns:
            df["timestamp"] = pd.to_datetime(df[ts_col].astype(int), unit="ms")
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        else:
            return pd.DataFrame()
        if value_col not in df.columns:
            return pd.DataFrame()
        df[value_col] = df[value_col].astype(float)
        return df[["timestamp", value_col]].copy()

    def fetch_all_fundamentals(self, symbol: str, start_time: int = None, end_time: int = None,
                               interval: str = "1h", limit: int = 1000):
        oi_df = self.fetch_open_interest(symbol, interval, limit)
        funding_df = self.fetch_funding_rate(symbol, start_time, end_time, limit)
        ls_df = self.fetch_ls_ratio(symbol, interval, limit)
        fg_df = self.fetch_fear_greed(start_time, end_time)

        # Применяем фильтры по времени
        start_dt = pd.to_datetime(start_time, unit="ms") if start_time else None
        end_dt = pd.to_datetime(end_time, unit="ms") if end_time else None

        for df in [oi_df, funding_df, ls_df, fg_df]:
            if not df.empty:
                if start_dt:
                    df = df[df["timestamp"] >= start_dt]
                if end_dt:
                    df = df[df["timestamp"] <= end_dt]

        # Слияние
        merged = oi_df
        for other in [funding_df, ls_df, fg_df]:
            if not other.empty:
                merged = merged.merge(other, on="timestamp", how="outer")

        merged = merged.sort_values("timestamp").reset_index(drop=True)
        merged.rename(columns={
            "openInterest": "Open_Interest",
            "fundingRate": "Funding_Rate",
            "longShortRatio": "Long_Short_Ratio"
        }, inplace=True)
        # Приводим числовые колонки к float
        for col in ["Open_Interest", "Funding_Rate", "Long_Short_Ratio", "Fear_Greed_Value"]:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors='coerce')
        return merged