import requests
import math
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# 加載環境變量
load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL = "https://api.schwabapi.com/trader/v1/"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 常量
BUY_AMOUNT = 500
STOP_LOSS_PERCENT = 0.95  # 止損比例
ADD_PERCENT = 1.05  # 加碼比例
CHECK_INTERVAL = 30  # 檢查間隔（秒）

def log_to_file(message, log_type="INFO"):
    """日誌記錄功能"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{log_type}] {message}"
    with open("trade_log.txt", "a") as log_file:
        log_file.write(formatted_message + "\n")
    print(formatted_message)


def send_telegram_notification(message):
    """發送 Telegram 通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log_to_file("未配置 Telegram 通知參數，跳過通知。", "WARNING")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_file(f"通知已發送: {message}")
    except requests.RequestException as e:
        log_to_file(f"通知發送失敗: {e}", "ERROR")


def get_stock_price(symbol):
    """透過 Finnhub API 獲取即時股票價格"""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("c")  # 即時價格字段 "c"
    except requests.RequestException as e:
        log_to_file(f"獲取 {symbol} 價格失敗: {e}", "ERROR")
        return None


def place_order(base_url, headers, account_hash, symbol, quantity, price, action):
    """執行真實下單功能"""
    order = {
        "account_hash": account_hash,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "action": action  # "BUY" 或 "SELL"
    }
    try:
        url = f"{base_url}accounts/{account_hash}/orders"
        log_to_file(f"發送請求至 {url}，請求內容: {order}")
        response = requests.post(url, headers=headers, json=order)
        response.raise_for_status()
        log_to_file(f"{action} 下單成功: {quantity} 股 {symbol} @ ${price:.2f}")
        return response.json()
    except requests.RequestException as e:
        log_to_file(f"{action} 下單失敗: {e}, 返回內容: {e.response.text if e.response else '無內容'}", "ERROR")
        return None


def live_trade_strategy(base_url, headers, account_hash, symbol, buy_amount, stop_loss_percent, add_percent):
    """即時交易策略，僅執行實際交易"""
    log_to_file(f"啟動交易策略，監控 {symbol} 價格...")
    cash = buy_amount  # 初始現金
    holdings = 0  # 初始持倉
    avg_price = 0  # 平均價格

    try:
        while True:
            current_price = get_stock_price(symbol)
            if current_price is None:
                time.sleep(CHECK_INTERVAL)
                continue

            log_to_file(f"目前價格: ${current_price:.2f}")

            # 初次買入
            if holdings == 0:
                shares_to_buy = math.floor(cash / current_price)
                avg_price = current_price
                holdings = shares_to_buy
                cash -= shares_to_buy * current_price

                place_order(base_url, headers, account_hash, symbol, shares_to_buy, avg_price, "BUY")
                log_to_file(f"首次買入 {shares_to_buy} 股 {symbol} @ ${avg_price:.2f}")

            # 止損邏輯
            stop_loss_price = avg_price * stop_loss_percent
            if current_price <= stop_loss_price:
                log_to_file(f"觸發止損條件: 當前價格 ${current_price:.2f} <= 止損價格 ${stop_loss_price:.2f}")
                place_order(base_url, headers, account_hash, symbol, holdings, current_price, "SELL")
                cash += holdings * current_price
                log_to_file(f"賣出 {holdings} 股 {symbol}，現金餘額 ${cash:.2f}")
                holdings = 0
                break

            # 加碼邏輯
            if current_price >= avg_price * add_percent and cash >= buy_amount:
                shares_to_buy = math.floor(buy_amount / current_price)
                avg_price = (avg_price * holdings + current_price * shares_to_buy) / (holdings + shares_to_buy)
                holdings += shares_to_buy
                cash -= shares_to_buy * current_price

                place_order(base_url, headers, account_hash, symbol, shares_to_buy, current_price, "BUY")
                log_to_file(f"加碼買入 {shares_to_buy} 股 {symbol}，新平均價格 ${avg_price:.2f}")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        log_to_file("策略被手動中止")
        log_to_file(f"最終現金餘額: ${cash:.2f}, 最終持倉: {holdings} 股")


if __name__ == "__main__":
    # 初始化帳戶與認證
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    ACCOUNT_HASH = os.getenv("ACCOUNT_HASH")

    HEADERS = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    SYMBOL = "TQQQ"  # 設定目標股票代號
    live_trade_strategy(BASE_URL, HEADERS, ACCOUNT_HASH, SYMBOL, BUY_AMOUNT, STOP_LOSS_PERCENT, ADD_PERCENT)
