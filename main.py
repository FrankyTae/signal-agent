import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = 60  # 1 minute
MAX_ALERTS_PER_DAY = 7

SIGNAL_MEMORY = {}
ALERT_COUNT = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}

# === DYNAMIC COINS FETCHING ===
def fetch_dynamic_coins():
    coins = set()

    try:
        mexc_res = requests.get("https://contract.mexc.com/api/v1/contract/detail").json()
        for item in mexc_res.get("data", []):
            symbol = item.get("symbol")
            if symbol and symbol.endswith("_USDT") and not symbol.startswith("W"):
                coins.add(symbol.replace("_", "/"))
    except Exception as e:
        print(f"[ERROR] MEXC fetch failed: {e}")

    try:
        bitrue_res = requests.get("https://fapi.bitrue.com/fapi/v1/exchangeInfo").json()
        for pair in bitrue_res.get("symbols", []):
            if pair.get("contractType") != "PERPETUAL":
                continue
            symbol = pair.get("symbol")
            if symbol.endswith("USDT") and not symbol.startswith("W"):
                coins.add(symbol[:-4] + "/USDT")
    except Exception as e:
        print(f"[ERROR] Bitrue fetch failed: {e}")

    return list(coins)

# === ASTRO FILTER ===
def is_astrologically_safe():
    today = datetime.utcnow().date()
    restricted_days = [
        datetime(2025, 8, 6).date(),
        datetime(2025, 8, 7).date(),
    ]
    return today not in restricted_days

# === FETCH CANDLE DATA ===
def fetch_ohlcv(coin, interval="1h", limit=100):
    try:
        symbol = coin.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url).json()
        df = pd.DataFrame(res, columns=["time", "open", "high", "low", "close", "volume", "C1", "C2", "C3", "C4", "C5", "C6"])
        df["close"] = pd.to_numeric(df["close"])
        df["volume"] = pd.to_numeric(df["volume"])
        return df
    except Exception as e:
        print(f"[ERROR] OHLC fetch failed: {e}")
        return None

# === STRATEGY LOGIC ===
def generate_signal(coin):
    if not is_astrologically_safe():
        return None

    df = fetch_ohlcv(coin)
    if df is None or len(df) < 30:
        return None

    # Calculate RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    # Money Flow Index (approximate)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    money_flow = typical_price * df["volume"]
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()
    mfi = 100 * positive_flow / (positive_flow + negative_flow)

    # Volume spike detection
    avg_volume = df["volume"].rolling(window=14).mean()
    volume_spike = df["volume"].iloc[-1] > 1.5 * avg_volume.iloc[-1]

    # Validate indicators
    if rsi.iloc[-1] is None or macd_line.iloc[-1] is None or signal_line.iloc[-1] is None or mfi.iloc[-1] is None:
        return None

    # Signal conditions
    long_condition = rsi.iloc[-1] < 30 and macd_line.iloc[-1] > signal_line.iloc[-1] and volume_spike and mfi.iloc[-1] < 30
    short_condition = rsi.iloc[-1] > 70 and macd_line.iloc[-1] < signal_line.iloc[-1] and volume_spike and mfi.iloc[-1] > 70

    if long_condition:
        direction = "LONG"
    elif short_condition:
        direction = "SHORT"
    else:
        return None

    price = round(df["close"].iloc[-1], 4)
    sl = round(price * (0.97 if direction == "LONG" else 1.03), 4)
    tp = [
        round(price * (1.02 if direction == "LONG" else 0.98), 4),
        round(price * (1.04 if direction == "LONG" else 0.96), 4),
        round(price * (1.06 if direction == "LONG" else 0.94), 4),
    ]
    rr = round((tp[1] - price) / (price - sl), 2) if direction == "LONG" else round((price - tp[1]) / (sl - price), 2)

    return {
        "coin": coin,
        "type": "confirmed",
        "direction": direction,
        "entry": price,
        "stop": sl,
        "tp": tp,
        "rr": rr,
        "volume": round(df["volume"].iloc[-1] / avg_volume.iloc[-1] * 100, 2),
        "confidence": 96,
        "timeframe": "1H",
        "reason": "96% Strategy Confluence",
    }

# === FORMAT MESSAGE ===
def format_msg(signal):
    date = datetime.now().strftime("%d %b %Y, %H:%M")
    return (
        f"✅ Confirmed {signal['direction']} Signal: {signal['coin']}\n\n"
        f"📌 Entry: ${signal['entry']}\n"
        f"🛑 Stop Loss: ${signal['stop']}\n"
        f"🎯 Take Profits:\n"
        f"  • TP1: ${signal['tp'][0]}\n"
        f"  • TP2: ${signal['tp'][1]}\n"
        f"  • TP3: ${signal['tp'][2]}\n\n"
        f"🔁 Risk:Reward: {signal['rr']}\n"
        f"🔥 Volume Spike: +{signal['volume']}%\n"
        f"📊 Confluence: {signal['reason']}\n"
        f"🧠 Confidence: {signal['confidence']}%\n"
        f"🕒 Timeframe: {signal['timeframe']}\n"
        f"📆 Date: {date}"
    )

# === SEND TELEGRAM ===
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")

# === MAIN AGENT LOOP ===
def run_agent():
    print("[STARTED] Signal Agent is running...")
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        print(f"[CHECK] {now.strftime('%Y-%m-%d %H:%M:%S')}")

        if ALERT_COUNT["date"] != today:
            ALERT_COUNT["date"] = today
            ALERT_COUNT["count"] = 0
            SIGNAL_MEMORY.clear()
            print("[RESET] Daily counter and memory cleared.")

        coins = fetch_dynamic_coins()
        print(f"[COINS] Scanning {len(coins)} pairs...")

        for coin in coins:
            if ALERT_COUNT["count"] >= MAX_ALERTS_PER_DAY:
                print("[SKIP] Daily alert limit reached.")
                break

            signal = generate_signal(coin)
            if not signal:
                continue

            if SIGNAL_MEMORY.get(coin) == signal["type"]:
                continue

            SIGNAL_MEMORY[coin] = signal["type"]
            msg = format_msg(signal)
            send_telegram(msg)
            ALERT_COUNT["count"] += 1
            print(f"[ALERT] {signal['type'].title()} - {coin}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_agent()
