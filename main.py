import os
import time
import random
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = 1800  # 30 minutes
MAX_ALERTS_PER_DAY = 7

SIGNAL_MEMORY = {}
ALERT_COUNT = {}

def fetch_filtered_coins(limit=30):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        coins = []
        for coin in data:
            symbol = coin["symbol"].upper()
            name = coin["name"].lower()
            if symbol in ["USDT", "USDC"] or "/" in symbol or "wrapped" in name or symbol.startswith("W"):
                continue
            coins.append(symbol + "/USDT")
        return coins
    except Exception as e:
        print(f"[ERROR] Failed to fetch coin list: {e}")
        return ["BTC/USDT", "ETH/USDT"]

def generate_signal(coin):
    chance = random.random()
    if chance < 0.3:
        return None

    signal_type = "confirmed" if chance > 0.7 else "potential"
    direction = random.choice(["LONG", "SHORT"])
    price = round(random.uniform(1.0, 100.0), 2) * 100
    sl = round(price - price * 0.02, 2)
    tp1 = round(price + price * 0.015, 2)
    tp2 = round(price + price * 0.03, 2)
    tp3 = round(price + price * 0.045, 2)
    rr = round((tp2 - price) / (price - sl), 2)
    volume_spike = round(random.uniform(10, 70), 1)

    return {
        "coin": coin,
        "type": signal_type,
        "direction": direction,
        "entry": price,
        "stop": sl,
        "tp": [tp1, tp2, tp3],
        "rr": rr,
        "volume": volume_spike,
        "confidence": 96 if signal_type == "confirmed" else 70,
        "timeframe": "1H",
        "reason": "Mocked TA + Astro confluence"
    }

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")

def format_signal_msg(signal):
    date = datetime.now().strftime("%d %b %Y, %H:%M")
    if signal['type'] == "potential":
        return (
            f"⚠️ Potential {signal['direction']} Setup: {signal['coin']}\n\n"
            f"📌 Entry Zone: ${round(signal['entry'] * 0.995, 2)} – ${round(signal['entry'] * 1.005, 2)}\n"
            f"📊 Reason: {signal['reason']}\n"
            f"🧠 Confidence: {signal['confidence']}%\n"
            f"🔍 Status: Watching for confirmation\n"
            f"🕒 Timeframe: {signal['timeframe']}\n\n"
            f"#AIPirateTradeBot"
        )
    else:
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
            f"📆 Date: {date}\n\n"
            f"#AIPirateTradeBot #TradeSignals"
        )

def run_agent():
    print("[STARTED] Signal Agent running on Render...")
    while True:
        date = datetime.now().strftime("%Y-%m-%d")
        ALERT_COUNT.setdefault(date, 0)
        if ALERT_COUNT[date] >= MAX_ALERTS_PER_DAY:
            print(f"[LIMIT] Max {MAX_ALERTS_PER_DAY} signals sent for {date}. Waiting...")
            time.sleep(CHECK_INTERVAL)
            continue

        print(f"\n[CHECKING] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        coins = fetch_filtered_coins()
        for coin in coins:
            if ALERT_COUNT[date] >= MAX_ALERTS_PER_DAY:
                break

            signal = generate_signal(coin)
            if not signal:
                print(f"[NO SIGNAL] {coin}")
                continue

            prev = SIGNAL_MEMORY.get(coin)

            if signal['type'] == "potential" and prev != "potential":
                SIGNAL_MEMORY[coin] = "potential"
                send_telegram_message(format_signal_msg(signal))
                ALERT_COUNT[date] += 1
                print(f"[ALERT SENT] Potential - {coin}")

            elif signal['type'] == "confirmed" and prev != "confirmed":
                SIGNAL_MEMORY[coin] = "confirmed"
                send_telegram_message(format_signal_msg(signal))
                ALERT_COUNT[date] += 1
                print(f"[ALERT SENT] Confirmed - {coin}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_agent()
