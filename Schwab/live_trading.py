import requests
import time
import math
from datetime import datetime
from dotenv import load_dotenv
import os

# 模擬交易相關
from auth import get_valid_access_token
from order import place_order, get_account_hash

# 加載環境變量
load_dotenv()

# 常量配置
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("錯誤: 未配置 FINNHUB_API_KEY。請在 .env 文件中設置該值。")
    exit(1)

BASE_URL = "https://api.schwabapi.com/trader/v1/"
SYMBOL = "TSLA"
BUY_AMOUNT = 500
STOP_LOSS = 500
MAX_TRADES = 3  # 最大交易次數
SIMULATED = False  # 模擬交易開關

# 初始化交易次數
trade_count = 0

def log_to_file(message):
    """將日誌記錄到文件中，同時輸出到控制台。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    with open("trade_log.txt", "a") as log_file:
        log_file.write(formatted_message + "\n")
    print(formatted_message)

def get_stock_price(api_key, symbol):
    """
    使用 Finnhub API 獲取即時股票價格。
    :param api_key: Finnhub API 密鑰
    :param symbol: 股票代號
    """
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("c")  # 即時價格字段 "c"
    except requests.exceptions.RequestException as e:
        print(f"查詢 {symbol} 價格時發生錯誤: {e}")
        return None


def get_positions_and_cash(base_url, headers, finnhub_api_key):
    """
    查詢帳戶持倉及現金餘額，返回結構化數據供交易策略使用。
    """
    params = {'fields': 'positions'}
    response = requests.get(f'{base_url}/accounts', headers=headers, params=params)

    if response.status_code == 200:
        accounts_data = response.json()
        total_cash_balance = 0.0
        holdings = []

        for account in accounts_data:
            account_info = account.get('securitiesAccount', {})
            cash_balance = account_info.get('currentBalances', {}).get('cashBalance', 0.0)
            total_cash_balance += cash_balance

            positions = account_info.get('positions', [])
            for position in positions:
                symbol = position['instrument'].get('symbol', None)
                quantity = position.get('longQuantity', 0.0)
                average_price = position.get('averagePrice', 0.0)
                current_price = get_stock_price(finnhub_api_key, symbol)

                if symbol and quantity > 0:
                    holdings.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "average_price": average_price,
                        "current_price": current_price,
                        "market_value": quantity * current_price if current_price else 0.0,
                        "profit_percent": ((current_price - average_price) / average_price * 100) if average_price > 0 else None
                    })

        return total_cash_balance, holdings
    else:
        print("查詢帳戶及持倉失敗")
        print(f"錯誤代碼: {response.status_code}")
        print(response.text)
        return 0.0, []

def get_account_cash_and_holdings(base_url, headers):
    """查詢帳戶現金餘額和持倉資料。"""
    url = f"{base_url}/accounts"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        accounts_data = response.json()
        total_cash_balance = 0.0
        holdings = []

        for account in accounts_data:
            account_info = account.get('securitiesAccount', {})
            cash_balance = account_info.get('currentBalances', {}).get('cashBalance', 0.0)
            total_cash_balance += cash_balance
            account_holdings = account_info.get('positions', [])
            for position in account_holdings:
                holdings.append({
                    "symbol": position['instrument'].get('symbol', '未知股票'),
                    "quantity": position.get('longQuantity', 0),
                    "average_price": position.get('averagePrice', 0.0),
                })

        return total_cash_balance, holdings
    except requests.exceptions.RequestException as e:
        log_to_file(f"查詢帳戶資料時發生錯誤: {e}")
        return 0.0, []

def place_order_simulated(base_url, headers, account_hash, symbol, quantity, price):
    """模擬下單功能，用於測試環境。"""
    if SIMULATED:
        log_to_file(f"[模擬交易] 下單指令：Symbol={symbol}, Shares={quantity}, Price=${price:.2f}")
        return {"status": "simulated", "symbol": symbol, "quantity": quantity, "price": price}
    else:
        return place_order(base_url, headers, account_hash, symbol, quantity, price)

def can_execute_trade(required_cash, cash_balance, trade_count):
    """確認是否允許執行交易。"""
    if trade_count >= MAX_TRADES:
        log_to_file("達到最大交易次數限制，停止交易。")
        return False
    if required_cash > cash_balance:
        log_to_file(f"現金不足，無法交易。需要 ${required_cash:.2f}，現金餘額 ${cash_balance:.2f}。")
        return False
    return True

def live_trade_strategy(base_url, headers, account_hash, finnhub_api_key, symbol):
    """基於即時更新的持倉和現金數據進行交易。"""
    global trade_count
    log_to_file("實時交易策略啟動，開始監控價格變動。")
    try:
        while True:
            # 每次檢查都更新最新現金和持倉數據
            cash, holdings = get_positions_and_cash(base_url, headers, finnhub_api_key)
            log_to_file(f"更新後的現金餘額: ${cash:.2f}")
            # log_to_file(f"持倉數據: {holdings}")

            current_price = get_stock_price(finnhub_api_key, symbol)
            if current_price is None:
                log_to_file(f"無法獲取 {symbol} 當前價格，跳過此次檢查。")
                time.sleep(30)
                continue

            log_to_file(f"檢查價格: {symbol}, 當前價格 ${current_price:.2f}")

            # 檢查是否有目標股票的持倉
            symbol_holdings = next((h for h in holdings if h['symbol'].lower() == symbol.lower()), None)
            if symbol_holdings:
                # log_to_file(f"檢測到持倉: {symbol_holdings}")
                quantity = symbol_holdings['quantity']
                entry_price = symbol_holdings['average_price']
                stop_loss_price = entry_price - (STOP_LOSS / quantity)
                target_price = entry_price * 1.05

                # 加碼邏輯
                if current_price >= target_price:
                    shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
                    required_cash = shares_to_buy * current_price

                    if can_execute_trade(required_cash, cash, trade_count):
                        log_to_file(f"觸發加碼條件: 當前價格 ${current_price:.2f}, 買入 {shares_to_buy} 股")
                        place_order_simulated(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
                        trade_count += 1
                        cash -= required_cash
                        quantity += shares_to_buy
                        entry_price = ((entry_price * (quantity - shares_to_buy)) + (current_price * shares_to_buy)) / quantity
                        log_to_file(f"加碼完成: 持倉 {quantity} 股, 平均成本 ${entry_price:.2f}, 現金餘額 ${cash:.2f}")
                    else:
                        log_to_file("加碼條件滿足，但交易條件不符。")

                # 止損邏輯
                elif current_price <= stop_loss_price:
                    log_to_file(f"觸發止損條件: 當前價格 ${current_price:.2f}, 賣出 {quantity} 股")
                    place_order_simulated(base_url, headers, account_hash, symbol, -quantity, current_price)
                    cash += quantity * current_price
                    holdings.remove(symbol_holdings)
                    log_to_file(f"止損完成: 當前現金餘額 ${cash:.2f}")

            log_to_file("等待 30 秒進行下一次檢查...")
            time.sleep(30)

    except KeyboardInterrupt:
        log_to_file("交易策略手動終止。")
        # log_to_file(f"最終現金餘額 ${cash:.2f}, 最終持倉: {holdings}")

if __name__ == "__main__":
    # 確保環境變量設置正確
    load_dotenv()
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
    if not FINNHUB_API_KEY:
        print("錯誤: 未配置 FINNHUB_API_KEY")
        exit(1)

    base_url = "https://api.schwabapi.com/trader/v1/"
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(base_url, headers)  # 獲取帳戶標識

    # 使用新的函數初始化現金和持倉數據
    print("初始化帳戶數據...")
    cash, holdings = get_positions_and_cash(base_url, headers, FINNHUB_API_KEY)
    print(f"現金餘額: ${cash:.2f}")
    print("持倉數據:")
    for holding in holdings:
        print(f"股票代號: {holding['symbol']}, 持股數量: {holding['quantity']}, 平均成本: ${holding['average_price']:.2f}")

    # 啟動交易模式
    print("\n請選擇當前狀態:")
    print("1: 沒有訂單，執行首次下單")
    print("2: 跳過下單，直接進入價格監控")
    choice = input("輸入選項 (1 或 2): ")

    if choice == "1":
        # 首次下單
        symbol = input("請輸入首次下單的股票代號: ").upper()
        current_price = get_stock_price(FINNHUB_API_KEY, symbol)
        if current_price is None:
            print("無法獲取股票價格，無法執行首次下單。")
            exit(1)

        shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
        required_cash = shares_to_buy * current_price

        if cash >= required_cash:
            print(f"執行首次買入: {shares_to_buy} 股，價格 ${current_price:.2f}")
            place_order_simulated(base_url, headers, account_hash, symbol, shares_to_buy, current_price)
            holdings.append({
                "symbol": symbol,
                "quantity": shares_to_buy,
                "average_price": current_price,
            })
            cash -= required_cash
            print("首次下單完成，進入價格監控模式...")
            live_trade_strategy(base_url, headers, account_hash, FINNHUB_API_KEY, symbol)
        else:
            print(f"現金不足，無法購買股票。需要 ${required_cash:.2f}，現金餘額 ${cash:.2f}。")
            exit(1)

    elif choice == "2":
        # 跳過首次下單，直接進入價格監控
        symbol = input("請輸入需要監控的股票代號: ").upper()
        print("跳過首次下單，直接進入價格監控模式。")
        live_trade_strategy(base_url, headers, account_hash, FINNHUB_API_KEY, symbol)

    else:
        print("無效選項，請重新運行腳本並選擇 1 或 2。")
        exit(1)
