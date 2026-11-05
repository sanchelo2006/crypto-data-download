# test_coinalyze.py
import os
import requests
from dotenv import load_dotenv

# Загружаем API-ключ из .env файла
load_dotenv()
API_KEY = os.getenv("COINALYZE_API_KEY")
if not API_KEY:
    raise ValueError("COINALYZE_API_KEY not found in .env file")

BASE_URL = "https://api.coinalyze.net/v1"

def test_exchanges():
    """1. Проверяем, какие биржи доступны."""
    print("\n--- 1. Checking available exchanges ---")
    url = f"{BASE_URL}/exchanges?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print("Available exchanges:")
        for item in data:
            print(f"  - {item}")
        return data
    except Exception as e:
        print(f"Error fetching exchanges: {e}")
        return []

def test_future_markets(exchange):
    """2. Для выбранной биржи получаем список доступных фьючерсных рынков."""
    print(f"\n--- 2. Fetching future markets for exchange: {exchange} ---")
    url = f"{BASE_URL}/future-markets"
    params = {
        "api_key": API_KEY,
        "exchange": exchange
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Found {len(data)} markets:")
        for i, market in enumerate(data[:20]):  # Показываем первые 20 для наглядности
            print(f"  {i+1}. {market}")
        if len(data) > 20:
            print(f"  ... and {len(data)-20} more.")
        return data
    except Exception as e:
        print(f"Error fetching future markets for {exchange}: {e}")
        return []

def test_liquidation_history(exchange, symbol, interval="1h", limit=10):
    """3. Пытаемся получить историю ликвидаций для конкретного символа."""
    print(f"\n--- 3. Testing liquidation history for {symbol} on {exchange} ---")
    url = f"{BASE_URL}/liquidation-history"
    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "limit": limit,
        "exchange": exchange,
        "source": "derivative"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data[0].get("history"):
                print(f"✅ SUCCESS! Data received for {symbol} on {exchange}. First record: {data[0]['history'][0]}")
                return True
            else:
                print(f"❌ FAILED: No history data for {symbol} on {exchange}")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    print("="*60)
    print("COINALYZE API TEST")
    print("="*60)

    # Шаг 1: Получаем список бирж
    exchanges = test_exchanges()
    if not exchanges:
        print("No exchanges found. Exiting.")
        return

    # Шаг 2: Выбираем биржу для теста (например, Bybit)
    target_exchange = "bybit"
    if target_exchange not in exchanges:
        print(f"Exchange '{target_exchange}' not in the list. Available: {exchanges}")
        # Попробуем взять первую из списка
        target_exchange = exchanges[0] if exchanges else None
        if not target_exchange:
            return
        print(f"Falling back to first available exchange: {target_exchange}")

    # Шаг 3: Получаем список рынков
    markets = test_future_markets(target_exchange)
    if not markets:
        print(f"No future markets found for {target_exchange}. Exiting.")
        return

    # Шаг 4: Тестируем историю ликвидаций для нескольких символов
    print("\n--- 4. Testing liquidation history for sampled symbols ---")
    # Тестируем первые 5 символов или меньше
    test_symbols = markets[:5]
    working_symbols = []
    for sym in test_symbols:
        if test_liquidation_history(target_exchange, sym):
            working_symbols.append(sym)

    # Шаг 5: Итоговый отчет
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    if working_symbols:
        print(f"✅ Found {len(working_symbols)} working symbols on {target_exchange}:")
        for sym in working_symbols:
            print(f"  - {sym}")
    else:
        print(f"❌ No working symbols found on {target_exchange}.")

if __name__ == "__main__":
    main()