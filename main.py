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
ALERT_COUNT = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}

# === FILTERED COINS (mocked for now) ===
COINS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT",
    "ADA/USDT", "AVAX/USDT", "LINK/USDT", "MATIC/USDT", "TRX/USDT",
    "LTC/USDT", "HBAR/USDT", "BCH/USDT", "XLM/USDT", "TON/USDT", "NEAR/USDT"
]

# === SIGNAL GENERATOR ===
def generate_signal(coin):
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

        # Reset daily count
        if ALERT_COUNT["date"] != today:
            ALERT_COUNT["date"] = today
            ALERT_COUNT["count"] = 0
            SIGNAL_MEMORY.clear()
            print("[RESET] Daily counter and memory cleared.")

        for coin in COINS:
            signal = generate_signal(coin)
            if not signal:
                continue

            # Avoid over-alerting
            if ALERT_COUNT["count"] >= MAX_ALERTS_PER_DAY:
                print("[SKIP] Daily alert limit reached.")
                break

            prev = SIGNAL_MEMORY.get(coin)
            if prev == signal["type"]:
                continue  # Same signal already sent

            # Update memory and send alert
            SIGNAL_MEMORY[coin] = signal["type"]
            message = format_msg(signal)
            send_telegram(message)
            ALERT_COUNT["count"] += 1
            print(f"[ALERT] {signal['type'].title()} - {coin}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_agent()
