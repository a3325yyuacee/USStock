import requests
import time
import math
from datetime import datetime, timedelta
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
# 初始化 Token 過期時間
token_expiry = datetime.now() + timedelta(minutes=30)


def log_to_file(message, log_type="INFO"):
    """
    改進的日誌記錄函數。
    :param message: 日誌消息
    :param log_type: 日誌類型，例如 "INFO", "ERROR", "TRADE"
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{log_type}] {message}"
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

def is_valid_price(current_price, entry_price=None, max_multiplier=10):
    """
    檢查價格是否在合理範圍內：
    - 價格應為正數。
    - 價格不應超過平均成本的 max_multiplier 倍（默認 10 倍）。

    :param current_price: 當前價格
    :param entry_price: 平均成本價（可選）
    :param max_multiplier: 平均成本價的最大倍數
    :return: True 表示價格有效，False 表示價格異常
    """
    if current_price <= 0:
        return False
    if entry_price and current_price > entry_price * max_multiplier:
        return False
    return True

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

        log_to_file(f"成功獲取帳戶數據: 現金餘額 ${total_cash_balance:.2f}, 持倉數量 {len(holdings)}")
        return total_cash_balance, holdings
    else:
        log_to_file(f"查詢帳戶及持倉失敗，錯誤代碼: {response.status_code}, 錯誤信息: {response.text}", "ERROR")
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
    """實時交易策略，根據市值動態切換固定止損與移動止損。"""
    global trade_count
    log_to_file("實時交易策略啟動，開始監控價格變動。")

    try:
        # 初始化變數
        highest_price = 0  # 記錄股票的最高價
        stop_loss_price = 0  # 當前止損點
        use_moving_stop_loss = False  # 是否使用移動止損
        
        while True:
            # 自動刷新 Token
            refresh_access_token_periodically(headers)
            
            # 每次檢查都更新最新現金和持倉數據
            cash, holdings = get_positions_and_cash(base_url, headers, finnhub_api_key)
            log_to_file(f"更新後的現金餘額: ${cash:.2f}")

            current_price = get_stock_price(finnhub_api_key, symbol)
            if current_price is None:
                log_to_file(f"無法獲取 {symbol} 當前價格，跳過此次檢查。")
                time.sleep(30)
                continue

            # 檢查是否有目標股票的持倉
            symbol_holdings = next((h for h in holdings if h['symbol'].lower() == symbol.lower()), None)
            if symbol_holdings:
                quantity = symbol_holdings['quantity']
                entry_price = symbol_holdings['average_price']
                current_market_value = current_price * quantity  # 計算市值
                
                # 判斷是否切換為移動止損
                if current_market_value > 1000 and not use_moving_stop_loss:
                    use_moving_stop_loss = True
                    log_to_file(f"市值超過 $1000，切換至移動止損模式。")
                
                # 更新止損點
                if use_moving_stop_loss:
                    # 移動止損點邏輯
                    if current_price > highest_price:
                        highest_price = current_price
                        stop_loss_price = highest_price * 0.9  # 移動止損點為最高價的 90%
                        log_to_file(f"新高價: ${highest_price:.2f}，止損點更新為: ${stop_loss_price:.2f}")
                else:
                    # 固定止損點邏輯
                    stop_loss_price = entry_price - (500 / quantity)
                    log_to_file(f"固定止損點設定為: ${stop_loss_price:.2f}")

                # 檢查止損條件
                if current_price <= stop_loss_price:
                    log_to_file(f"觸發止損條件: 當前價格 ${current_price:.2f} <= 止損點 ${stop_loss_price:.2f}")
                    place_order_simulated(base_url, headers, account_hash, symbol, -quantity, current_price)
                    cash += quantity * current_price
                    holdings.remove(symbol_holdings)
                    log_to_file(f"止損完成: 當前現金餘額 ${cash:.2f}")
                    send_telegram_notification(f"止損觸發：賣出 {quantity} 股 {symbol}，價格 ${current_price:.2f}", bot_token, chat_id, "TRADE")
                    break  # 停止策略執行，因為持倉已清空

            else:
                # 無持倉情況，跳過
                log_to_file(f"未找到 {symbol} 的持倉數據，跳過此次檢查。")
                time.sleep(30)
                continue

            log_to_file("等待 30 秒進行下一次檢查...")
            time.sleep(30)

    except KeyboardInterrupt:
        log_to_file("交易策略手動終止。")
        log_to_file(f"最終現金餘額: ${cash:.2f}, 最終持倉: {holdings}")
        send_telegram_notification(f"交易策略終止：現金餘額 ${cash:.2f}，持倉數量 {len(holdings)}", bot_token, chat_id, "INFO")


def send_telegram_notification(message, bot_token, chat_id, log_type="INFO"):
    """
    使用 Telegram 發送通知，並記錄到日誌。
    :param message: 發送的消息內容
    :param bot_token: Telegram Bot 的 API Token
    :param chat_id: 接收消息的聊天 ID
    :param log_type: 日誌類型，例如 "INFO", "ERROR", "TRADE"
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_file(f"通知已發送: {message}", log_type)
    except requests.exceptions.RequestException as e:
        log_to_file(f"通知發送失敗: {e}", "ERROR")

def refresh_access_token_periodically(headers):
    """
    自動每 30 分鐘刷新一次 Access Token。
    """
    global access_token
    global token_expiry

    if datetime.now() >= token_expiry:
        log_to_file("Access Token 即將過期，正在刷新...")
        access_token = get_valid_access_token()  # 使用原有的函數獲取新的 Access Token
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
            token_expiry = datetime.now() + timedelta(minutes=30)
            log_to_file("Access Token 刷新成功。")
        else:
            log_to_file("刷新 Access Token 失敗，請檢查憑證或網絡連線。", "ERROR")
            exit(1)


if __name__ == "__main__":

    # 確保環境變量設置正確
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
    if not FINNHUB_API_KEY:
        print("錯誤: 未配置 FINNHUB_API_KEY")
        exit(1)

    base_url = "https://api.schwabapi.com/trader/v1/"
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(base_url, headers)  # 獲取帳戶標識

    # 初始化
    send_telegram_notification("交易腳本已啟動", bot_token, chat_id)

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
