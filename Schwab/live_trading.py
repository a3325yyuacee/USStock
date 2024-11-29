import requests
import time
import math
from datetime import datetime
from dotenv import load_dotenv
import os
from auth import get_valid_access_token
from order import place_order, get_account_hash

# 加載 .env 配置
load_dotenv()

# 配置常量
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("錯誤: 未配置 FINNHUB_API_KEY。請在 .env 文件中設置該值。")
    exit(1)

BASE_URL = "https://api.schwabapi.com/trader/v1/"
SYMBOL = "TSLA"  # 股票代號
BUY_AMOUNT = 500
STOP_LOSS = 500


def get_stock_price(symbol):
    """
    使用 Finnhub API 獲取即時股票價格
    """
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("c")  # 即時價格字段 "c"
    except requests.exceptions.RequestException as e:
        print(f"獲取 {symbol} 價格失敗: {e}")
        return None


def get_account_cash(base_url, headers):
    """
    從 API 查詢所有帳戶的現金餘額
    """
    url = f"{base_url}/accounts"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        accounts_data = response.json()
        total_cash_balance = 0.0
        for account in accounts_data:
            account_info = account.get('securitiesAccount', {})
            account_number = account_info.get('accountNumber', '未知帳號')
            cash_balance = account_info.get('currentBalances', {}).get('cashBalance', 0.0)

            print(f"帳號: {account_number}, 現金餘額: ${cash_balance:.2f}")
            total_cash_balance += cash_balance

        return total_cash_balance
    else:
        print(f"無法獲取帳戶數據，HTTP 狀態碼: {response.status_code}")
        print(f"響應內容: {response.text}")
        return 0.0


def live_trade_strategy(base_url, headers, account_hash, cash, symbol, holdings=0, entry_price=0, stop_loss_price=None):
    """
    基於策略的實時交易，避免重複下單
    """
    print("實時交易啟動，按 Ctrl+C 終止。")
    try:
        while True:
            current_price = get_stock_price(symbol)
            if current_price is None:
                print("無法獲取當前價格，跳過本次檢查。")
                time.sleep(30)
                continue

            print(f"[{datetime.now()}] {symbol} 當前價格: ${current_price:.2f}")

            # 如果已有持倉，檢查加碼條件或止損條件
            if holdings > 0:
                target_price = entry_price * 1.02  # 加碼目標價格
                stop_loss_price = entry_price - (STOP_LOSS / holdings)

                # 價格高於目標價格，加碼
                if current_price >= target_price:
                    shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
                    required_cash = shares_to_buy * current_price
                    if cash >= required_cash:
                        print(f"執行加碼: {shares_to_buy} 股，價格 ${current_price:.2f}")
                        place_order(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
                        holdings += shares_to_buy
                        cash -= required_cash
                        entry_price = ((entry_price * (holdings - shares_to_buy)) + (current_price * shares_to_buy)) / holdings
                        stop_loss_price = entry_price - (STOP_LOSS / holdings)
                    else:
                        print(f"現金不足，無法加碼，當前現金餘額 ${cash:.2f}")

                # 價格低於止損價格，平倉
                elif current_price <= stop_loss_price:
                    print(f"價格低於止損價格 ${stop_loss_price:.2f}，執行平倉。")
                    place_order(base_url, headers, account_hash, symbol, -holdings, current_price)  # 賣出所有持倉
                    cash += holdings * current_price
                    holdings = 0
                    entry_price = 0
                    stop_loss_price = None

            print("等待 30 秒進行下一次檢查...")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n實時交易已手動終止。")
        print(f"最終現金餘額: ${cash:.2f}")
        print(f"最終持倉數量: {holdings} 股")
        if holdings > 0:
            print(f"持倉市值: ${holdings * current_price:.2f}")


if __name__ == "__main__":
    # 初始化 API 和帳戶資料
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(BASE_URL, headers)

    # 獲取現金餘額
    cash_balance = get_account_cash(BASE_URL, headers)
    print(f"總現金餘額: ${cash_balance:.2f}")

    # 用戶選擇初始化模式
    print("請選擇當前狀態:")
    print("1: 現在無訂單，執行初始下單")
    print("2: 跳過下單，直接進入價格監控")
    choice = input("輸入選項 (1 或 2): ")

    holdings = 0
    entry_price = 0
    stop_loss_price = None

    if choice == "1":
        # 無訂單，執行首次下單
        current_price = get_stock_price(SYMBOL)
        if current_price is None:
            print("無法獲取股票價格，無法執行首次下單。")
            exit(1)

        shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
        required_cash = shares_to_buy * current_price

        if cash_balance >= required_cash:
            print(f"執行首次買入: {shares_to_buy} 股，價格 ${current_price:.2f}")
            place_order(BASE_URL, headers, account_hash, SYMBOL, shares_to_buy, current_price)
            cash_balance -= required_cash
            holdings = shares_to_buy
            entry_price = current_price
            stop_loss_price = entry_price - (STOP_LOSS / shares_to_buy)
            print("初始下單完成，進入價格監控...")
            live_trade_strategy(BASE_URL, headers, account_hash, cash_balance, SYMBOL, holdings, entry_price, stop_loss_price)
        else:
            print(f"現金不足，無法購買股票。需要 ${required_cash:.2f}，現金餘額 ${cash_balance:.2f}。")
            exit(1)

    elif choice == "2":
        # 跳過下單，直接進入價格監控
        print("直接進入價格監控模式，按照策略進行加碼或檢查止損。")
        holdings = int(input("請輸入當前持倉數量: "))
        entry_price = float(input("請輸入進場價格: "))
        stop_loss_price = entry_price - (STOP_LOSS / holdings)
        live_trade_strategy(BASE_URL, headers, account_hash, cash_balance, SYMBOL, holdings, entry_price, stop_loss_price)

    else:
        print("無效選項，請重新運行腳本並選擇 1 或 2。")
        exit(1)
