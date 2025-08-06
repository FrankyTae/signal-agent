import os
import time
import random
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = 60  # 1 minute
MAX_ALERTS_PER_DAY = 7

SIGNAL_MEMORY = {}
ALERT_COUNT = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}

# === DYNAMIC COINS FETCHING ===
def fetch_dynamic_coins():
    coins = set()

    # --- MEXC Futures ---
    try:
        mexc_res = requests.get("https://contract.mexc.com/api/v1/contract/detail").json()
        for item in mexc_res.get("data", []):
            symbol = item.get("symbol")
            if symbol and symbol.endswith("_USDT") and not symbol.startswith("W"):
                coins.add(symbol.replace("_", "/"))
    except Exception as e:
        print(f"[ERROR] MEXC fetch failed: {e}")

    # --- Bitrue Futures ---
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

# === SIGNAL GENERATOR (placeholder for 96% strategy) ===
def generate_signal(coin):
    # TODO: Replace with actual 96% success TA + Astro strategy logic
    chance = random.random()
    if chance < 0.4:
        return None
    signal_type = "confirmed" if chance > 0.7 else "potential"
    direction = random.choice(["LONG", "SHORT"])
    price = round(random.uniform(20, 100), 2)
    sl = round(price * 0.98, 2)
    tp = [round(price * 1.015, 2), round(price * 1.03, 2), round(price * 1.045, 2)]
    rr = round((tp[1] - price) / (price - sl), 2)
    volume = round(random.uniform(10, 70), 1)
    return {
        "coin": coin,
        "type": signal_type,
        "direction": direction,
        "entry": price,
        "stop": sl,
        "tp": tp,
        "rr": rr,
        "volume": volume,
        "confidence": 96 if signal_type == "confirmed" else 70,
        "timeframe": "1H",
        "reason": "TA + Astro confluence"
    }

# === FORMAT MESSAGE ===
def format_msg(signal):
    date = datetime.now().strftime("%d %b %Y, %H:%M")
    if signal["type"] == "potential":
        return (
            f"⚠️ Potential {signal['direction']} Setup: {signal['coin']}\n\n"
            f"📌 Entry Zone: ${round(signal['entry']*0.995, 2)} – ${round(signal['entry']*1.005, 2)}\n"
            f"📊 Reason: {signal['reason']}\n"
            f"🧠 Confidence: {signal['confidence']}%\n"
            f"🔍 Status: Watching for confirmation\n"
            f"🕒 Timeframe: {signal['timeframe']}\n"
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
            f"📆 Date: {date}"
        )

# === SEND TELEGRAM ===
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}

