import requests
import time
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# 模擬交易相關
from auth import get_valid_access_token
from order import place_order, get_account_hash
from live_trading import get_positions_and_cash, live_trade_strategy, get_stock_price

# 加載環境變量
load_dotenv()

# 常量配置
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("錯誤: 未配置 FINNHUB_API_KEY。請在 .env 文件中設置該值。")
    exit(1)

BASE_URL = "https://api.schwabapi.com/trader/v1/"
BUY_AMOUNT = 200
STOP_LOSS = 200
MAX_TRADES = 3  # 最大交易次數
SIMULATED = False  # 模擬交易開關

# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# if not BOT_TOKEN or not CHAT_ID:
#     print("警告: 未配置 Telegram 通知參數，將跳過通知功能。")

# 初始化交易次數
trade_count = 0
# 初始化 Token 過期時間
token_expiry = datetime.now() + timedelta(minutes=30)
last_add_price = 0  # 記錄最後一次加碼時的價格
last_order_time = datetime.min  # 初始化為最小時間
cooldown_seconds = 60  # 設置冷卻時間為 60 秒

if __name__ == "__main__":
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(BASE_URL, headers)  # 獲取帳戶標識
    if not access_token:
        print("錯誤: 無法獲取 Access Token。")
        exit(1)

    if not account_hash:
        print("錯誤: 無法獲取 Account Hash。")
        exit(1)

    # 初始化
    # send_telegram_notification("交易腳本已啟動", BOT_TOKEN, CHAT_ID)

    # 使用新的函數初始化現金和持倉數據
    print("初始化帳戶數據...")
    cash, holdings = get_positions_and_cash(BASE_URL, headers, FINNHUB_API_KEY)
    print(f"現金餘額: ${cash:.2f}")
    print("持倉數據:")
    for holding in holdings:
        print(f"股票代號: {holding['symbol']}, 持股數量: {holding['quantity']:.2f}, 平均成本: ${holding['average_price']:.2f}")
    if cash is None or holdings is None:
        print("錯誤: 獲取帳戶數據失敗。")
        exit(1)

    # 啟動交易模式
    print("\n請選擇當前狀態:")
    print("1: 沒有訂單，執行首次下單")
    print("2: 跳過下單，直接進入價格監控")
    choice = input("輸入選項 (1 或 2): ")

    if choice == "1":
        # 首次下單邏輯
        symbol = input("請輸入首次下單的股票代號: ").upper()
        current_price = get_stock_price(FINNHUB_API_KEY, symbol)

        if current_price is None:
            print("無法獲取股票價格，無法執行首次下單。")
            exit(1)

        shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
        print(f"準備下單: {shares_to_buy} 股，價格 ${current_price:.2f}")

        # 執行下單
        order_id = place_order(BASE_URL, headers, account_hash, symbol, shares_to_buy, current_price)
        if order_id:
            print(f"首次下單成功，訂單編號: {order_id}")
        else:
            print("首次下單失敗，請檢查問題。")

        # 下單後結束程式
        exit(0)

    elif choice == "2":
        # 跳過首次下單，直接進入價格監控
        symbol = input("請輸入需要監控的股票代號: ").upper()
        print("跳過首次下單，直接進入價格監控模式。")
        live_trade_strategy(BASE_URL, headers, account_hash, FINNHUB_API_KEY, symbol)

    else:
        print("無效選項，請重新運行腳本並選擇 1 或 2。")
        exit(1)