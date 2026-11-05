from pybit.unified_trading import HTTP
import pandas as pd
from datetime import datetime, timedelta

# Initialize session
session = HTTP(testnet=False)
symbol = "BTCUSDT"

print("=" * 60)
print("TESTING BYBIT FUNDAMENTALS ENDPOINTS")
print("=" * 60)

# ----------------------------------------------------------------------
# 1. Open Interest
print("\n1. OPEN INTEREST")
resp_oi = session.get_open_interest(
    category="linear",
    symbol=symbol,
    intervalTime="1h",
    limit=5
)
print("Raw response:", resp_oi)
if resp_oi.get("retCode") == 0:
    data = resp_oi["result"]["list"]
    print("Sample data:", data[:2])
else:
    print("Error:", resp_oi.get("retMsg"))

# ----------------------------------------------------------------------
# 2. Funding Rate History
print("\n2. FUNDING RATE HISTORY")
resp_fr = session.get_funding_rate_history(
    category="linear",
    symbol=symbol,
    limit=5
)
print("Raw response:", resp_fr)
if resp_fr.get("retCode") == 0:
    data = resp_fr["result"]["list"]
    print("Sample data:", data[:2])
else:
    print("Error:", resp_fr.get("retMsg"))

# ----------------------------------------------------------------------
# 3. Long/Short Ratio
print("\n3. LONG/SHORT RATIO")
resp_ls = session.get_long_short_ratio(
    category="linear",
    symbol=symbol,
    period="1h",
    limit=5
)
print("Raw response:", resp_ls)
if resp_ls.get("retCode") == 0:
    data = resp_ls["result"]["list"]
    print("Sample data:", data[:2])
else:
    print("Error:", resp_ls.get("retMsg"))

print("\n" + "=" * 60)
print("Test complete. Check the raw responses above.")