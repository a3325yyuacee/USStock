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
        # print("成功獲取帳戶數據: ", accounts_data)

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


def get_account_positions(base_url, headers, account_hash, symbol):
    """
    獲取帳戶的當前持倉資訊
    """
    url = f"{base_url}/accounts/{account_hash}/positions"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        positions = response.json()
        for position in positions.get('securitiesAccount', {}).get('positions', []):
            if position['instrument']['symbol'] == symbol:
                quantity = position.get('longQuantity', 0)
                cost_price = position.get('averagePrice', 0)
                return quantity, cost_price
    return 0, 0


def check_positions(base_url, headers, account_hash, symbol, current_price, holdings, entry_price, stop_loss_price):
    """
    啟動時檢查持倉是否符合策略
    """
    if holdings > 0:
        print(f"檢查持倉: {holdings} 股，進場價格: ${entry_price:.2f}，當前價格: ${current_price:.2f}")

        # 如果價格低於止損價
        if current_price <= stop_loss_price:
            print(f"價格低於止損價 ${stop_loss_price:.2f}，執行平倉。")
            place_order(base_url, headers, account_hash, symbol, holdings, current_price)
            holdings = 0
            stop_loss_price = None

        # 如果價格高於加碼目標
        target_price = entry_price * 1.02
        if current_price >= target_price:
            print(f"價格高於加碼目標 ${target_price:.2f}，考慮加碼。")
            shares_to_buy = int(BUY_AMOUNT // current_price)
            if shares_to_buy >= 2:
                place_order(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
                holdings += shares_to_buy
                stop_loss_price = entry_price - (STOP_LOSS / holdings)

    return holdings, stop_loss_price


def live_trade_strategy(base_url, headers, account_hash, cash, symbol):
    """
    基於策略的實時交易，避免重複下單
    """
    # 啟動時檢查現有持倉和最近訂單
    holdings, entry_price = get_existing_positions(base_url, headers, account_hash, symbol)
    recent_order_price = get_recent_orders(base_url, headers, account_hash, symbol)

    stop_loss_price = entry_price - (STOP_LOSS / holdings) if holdings > 0 else None

    print("實時交易啟動，按 Ctrl+C 終止。")
    try:
        while True:
            current_price = get_stock_price(symbol)
            if current_price is None:
                print("無法獲取當前價格，跳過本次檢查。")
                time.sleep(30)
                continue

            print(f"[{datetime.now()}] {symbol} 當前價格: ${current_price:.2f}")

            # 如果無持倉，檢查是否需要初次買入
            if holdings == 0:
                shares_to_buy = math.ceil(BUY_AMOUNT / current_price)  # 確保至少購買滿足 $500 的股數
                required_cash = shares_to_buy * current_price

                if recent_order_price == current_price:
                    print(f"檢測到最近已下單價格為 ${recent_order_price:.2f}，跳過本次買入。")
                    continue

                if cash >= required_cash:
                    cash -= required_cash
                    holdings += shares_to_buy
                    entry_price = current_price
                    stop_loss_price = entry_price - (STOP_LOSS / holdings)

                    print(f"執行買入: {shares_to_buy} 股，價格 ${current_price:.2f}")
                    place_order(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
                else:
                    print(f"現金不足以購買至少 ${BUY_AMOUNT} 的股票（需要 ${required_cash:.2f}，現金餘額 ${cash:.2f}）。")

            # 如果已有持倉，檢查加倉條件
            elif holdings > 0:
                target_price = entry_price * 1.02  # 加碼目標價格
                if current_price >= target_price and (recent_order_price is None or current_price > recent_order_price):
                    shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
                    required_cash = shares_to_buy * current_price

                    if cash >= required_cash:
                        cash -= required_cash
                        holdings += shares_to_buy
                        stop_loss_price = entry_price - (STOP_LOSS / holdings)

                        print(f"執行加碼: {shares_to_buy} 股，價格 ${current_price:.2f}")
                        place_order(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
                    else:
                        print(f"現金不足以加碼購買 ${BUY_AMOUNT} 的股票（需要 ${required_cash:.2f}，現金餘額 ${cash:.2f}）。")

            print("等待 30 秒進行下一次檢查...")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n實時交易已手動終止。")
        print(f"最終現金餘額: ${cash:.2f}")
        print(f"最終持倉數量: {holdings} 股")
        print(f"最後價格: ${current_price:.2f}")
        if holdings > 0:
            print(f"持倉市值: ${holdings * current_price:.2f}")

def get_existing_positions(base_url, headers, account_hash, symbol):
    """
    檢查帳戶中是否已有指定股票的持倉
    """
    url = f"{base_url}/accounts/{account_hash}/positions"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        positions = response.json().get('securitiesAccount', {}).get('positions', [])
        print("現有持倉資料: ", positions)  # 調試用日誌，檢查 API 返回內容
        for position in positions:
            if position['instrument']['symbol'] == symbol:
                quantity = position.get('longQuantity', 0)
                average_price = position.get('averagePrice', 0)
                print(f"檢測到持倉: 股票={symbol}, 數量={quantity}, 平均價格=${average_price:.2f}")
                return quantity, average_price
    print("未檢測到與目標股票相關的持倉。")
    return 0, 0

def get_recent_orders(base_url, headers, account_hash, symbol):
    """
    檢查帳戶中是否已有針對指定股票的近期訂單
    """
    url = f"{base_url}/accounts/{account_hash}/orders"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        orders = response.json()
        print("最近訂單資料: ", orders)  # 調試用日誌，檢查 API 返回內容
        for order in orders:
            # 確認訂單是針對目標股票的
            if order['orderLegCollection'][0]['instrument']['symbol'] == symbol:
                status = order.get('status')
                price = float(order['price'])
                if status in ['FILLED', 'WORKING']:  # 已成交或正在執行
                    print(f"檢測到最近訂單: 股票={symbol}, 價格=${price:.2f}, 狀態={status}")
                    return price
    print("未檢測到與目標股票相關的訂單。")
    return None


if __name__ == "__main__":
    # 初始化 API 和帳戶資料
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(BASE_URL, headers)

    # 獲取現金餘額
    cash_balance = get_account_cash(BASE_URL, headers)
    print(f"總現金餘額: ${cash_balance:.2f}")

    # 檢查持倉
    current_price = get_stock_price(SYMBOL)
    holdings, entry_price = get_account_positions(BASE_URL, headers, account_hash, SYMBOL)
    stop_loss_price = entry_price - (STOP_LOSS / holdings) if holdings > 0 else None
    holdings, stop_loss_price = check_positions(BASE_URL, headers, account_hash, SYMBOL, current_price, holdings, entry_price, stop_loss_price)

    # 啟動實時交易策略
    live_trade_strategy(BASE_URL, headers, account_hash, cash_balance, SYMBOL)
