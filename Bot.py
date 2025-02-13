import ccxt
import requests
import telebot
import pandas as pd
import os
import time

# 🔹 Load Binance API Keys Securely from Environment Variables
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# 🔹 Initialize Binance API
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET_KEY,
    'rateLimit': 1200,
    'enableRateLimit': True
})

# 🔹 Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🔹 Strategy Parameters
PAIR = "ETH/USDT"
TRADE_REWARD = 0.035  # 3.5% Take Profit
TRADE_RISK = 0.01  # 1% Stop Loss
TIMEFRAME = "15m"  # 15-minute candles to spread trades throughout the day
LOOKBACK = 100  # Number of candles to analyze
TRADES_PER_DAY = 4  # Fixed at 4 trades per day

# 🔹 Function to Fetch Market Data
def fetch_market_data():
    try:
        ohlcv = exchange.fetch_ohlcv(PAIR, timeframe=TIMEFRAME, limit=LOOKBACK)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        return f"Error fetching market data: {e}"

# 🔹 Detect Trading Signal
def check_trade_signal(df):
    latest = df.iloc[-1]
    if latest['close'] > df['close'].rolling(20).mean().iloc[-1]:
        return "LONG"
    elif latest['close'] < df['close'].rolling(20).mean().iloc[-1]:
        return "SHORT"
    return "No Signal"

# 🔹 Send Signal to Telegram
def send_telegram_signal(signal, entry_price):
    if signal == "No Signal":
        return

    take_profit = round(entry_price * (1 + TRADE_REWARD), 2)
    stop_loss = round(entry_price * (1 - TRADE_RISK), 2) if signal == "LONG" else round(entry_price * (1 + TRADE_RISK), 2)
    
    message_text = f"""
📢 **New Trade Signal!**  
🔹 Pair: {PAIR}  
🔹 Type: {signal}  
🔹 Entry: {entry_price}  
🔹 Take Profit: {take_profit}  
🔹 Stop Loss: {stop_loss}  
#ETHUSDT #AutoSignal
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message_text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

# 🔹 Continuous Trade Signal Generation (4 Trades Per Day, No Execution)
def continuous_trading():
    daily_trades = 0
    while True:
        df = fetch_market_data()
        if isinstance(df, str):
            print(df)
            continue
        signal = check_trade_signal(df)
        if signal != "No Signal" and daily_trades < TRADES_PER_DAY:
            entry_price = df['close'].iloc[-1]
            send_telegram_signal(signal, entry_price)
            daily_trades += 1
        if daily_trades >= TRADES_PER_DAY:
            daily_trades = 0
            time.sleep(86400)  # Pause until the next trading day
        else:
            time.sleep(3600)  # Wait 1 hour before next check

# 🔹 Start Telegram Bot and Continuous Trading
import threading
threading.Thread(target=continuous_trading).start()
bot.polling()


from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

