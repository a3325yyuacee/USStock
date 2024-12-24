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
BUY_AMOUNT = 200
STOP_LOSS = 200
MAX_TRADES = 3  # 最大交易次數
SIMULATED = False  # 模擬交易開關

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if not BOT_TOKEN or not CHAT_ID:
    print("警告: 未配置 Telegram 通知參數，將跳過通知功能。")

# 初始化交易次數
trade_count = 0
# 初始化 Token 過期時間
token_expiry = datetime.now() + timedelta(minutes=30)
last_add_price = 0  # 記錄最後一次加碼時的價格
last_order_time = datetime.min  # 初始化為最小時間
cooldown_seconds = 60  # 設置冷卻時間為 60 秒



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

def get_stock_price(api_key, symbol, retries=3):
    """
    使用 Finnhub API 獲取即時股票價格，支持重試機制。
    """
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("c")  # 即時價格字段 "c"
        except requests.exceptions.RequestException as e:
            log_to_file(f"查詢 {symbol} 價格時發生錯誤: {e}")
            if attempt < retries - 1:
                log_to_file(f"重試第 {attempt + 1} 次...")
                time.sleep(2)  # 等待 2 秒後重試
            else:
                log_to_file(f"多次重試失敗，無法獲取 {symbol} 的價格。", "ERROR")
                return None

def get_positions_and_cash(BASE_URL, headers, finnhub_api_key):
    """
    查詢帳戶持倉及現金餘額，返回結構化數據供交易策略使用。
    """
    params = {'fields': 'positions'}
    response = requests.get(f'{BASE_URL}/accounts', headers=headers, params=params)

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
                if current_price is not None and average_price > 0:
                    profit_percent = ((current_price - average_price) / average_price * 100)
                else:
                    profit_percent = None

                if symbol and quantity > 0:
                    holdings.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "average_price": average_price,
                        "current_price": current_price,
                        "market_value": quantity * current_price if current_price else 0.0,
                        "profit_percent": profit_percent
                    })

        log_to_file(f"成功獲取帳戶數據: 現金餘額 ${total_cash_balance:.2f}")
        return total_cash_balance, holdings
    else:
        log_to_file(f"查詢帳戶及持倉失敗，錯誤代碼: {response.status_code}, 錯誤信息: {response.text}", "ERROR")
        return 0.0, []

def place_order_simulated(BASE_URL, headers, account_hash, symbol, quantity, price):
    """模擬下單功能，用於測試環境。"""
    if SIMULATED:
        log_to_file(f"[模擬交易] 下單指令：Symbol={symbol}, Shares={quantity}, Price=${price:.2f}")
        return {"status": "simulated", "symbol": symbol, "quantity": quantity, "price": price}
    else:
        return place_order(BASE_URL, headers, account_hash, symbol, quantity, price)

def can_execute_trade(required_cash, cash_balance, trade_count):
    """確認是否允許執行交易。"""
    if trade_count >= MAX_TRADES:
        log_to_file("達到最大交易次數限制，停止交易。")
        return False
    if required_cash > cash_balance:
        log_to_file(f"現金不足，無法交易。需要 ${required_cash:.2f}，現金餘額 ${cash_balance:.2f}。")
        return False
    return True


def live_trade_strategy(BASE_URL, headers, account_hash, finnhub_api_key, symbol):
    """
    單一股票的實時交易策略
    """
    global last_order_time  # 聲明全局變量

    log_to_file(f"開始監控股票: {symbol}")
    highest_price = 0
    stop_loss_price = 0
    dynamic_stop_loss_pct = 0.05  # 動態回撤比例 (5%)
    minimum_profit_threshold = 0.02  # 最小盈利門檻 (2%)
    use_moving_stop_loss = False

    # 用來檢查價格是否未變動
    previous_prices = []  # 保存最近 3 次價格
    try:
        while True:
            # **刷新 Token**
            refresh_access_token_periodically(headers)

            # 獲取現金與持倉數據
            cash, holdings = get_positions_and_cash(BASE_URL, headers, finnhub_api_key)

            # 找到目標股票的持倉
            symbol_holdings = next((h for h in holdings if h['symbol'].lower() == symbol.lower()), None)
            if not symbol_holdings:
                log_to_file(f"未找到 {symbol} 的持倉數據，跳過此次檢查。")
                time.sleep(30)
                continue

            # 提取持倉數據
            quantity = symbol_holdings['quantity']
            entry_price = symbol_holdings['average_price']
            # 設置加碼目標價格和止損條件
            target_add_price = entry_price * 1.05  # 5% 加碼

            # 判斷是否啟用移動止損
            if quantity * entry_price > 2 * BUY_AMOUNT:
                use_moving_stop_loss = True
                log_to_file(f"持倉成本超過兩次交易金額，切換至移動止損模式。")
            else:
                use_moving_stop_loss = False
                log_to_file(f"仍使用固定止損模式。")

            # 獲取當前股票價格
            current_price = get_stock_price(finnhub_api_key, symbol)
            if current_price is None:
                log_to_file(f"無法獲取 {symbol} 的即時價格，跳過此次檢查。")
                time.sleep(30)
                continue

            # **檢查價格是否未變動 3 次**
            previous_prices.append(current_price)
            if len(previous_prices) > 3:
                previous_prices.pop(0)
            if len(set(previous_prices)) == 1:  # 如果最近 3 次價格相同
                log_to_file(f"{symbol} 價格連續 3 次未變動，跳過此次檢查。")
                time.sleep(5)
                continue

            log_to_file(f"持倉數量: {quantity}, 平均成本: ${entry_price:.2f}")
            log_to_file(f"{symbol} 當前價格: ${current_price:.2f}")
            log_to_file(f"加碼目標價格: ${target_add_price:.2f}")

            # 更新移動止損
            if use_moving_stop_loss:
                if current_price > highest_price:
                    highest_price = current_price
                    stop_loss_price = max(
                        highest_price * (1 - dynamic_stop_loss_pct),  # 最高價回撤比例
                        entry_price * (1 + minimum_profit_threshold)  # 保證最低盈利
                    )
                    log_to_file(f"新高價: ${highest_price:.2f}，更新移動止損點: ${stop_loss_price:.2f}")
                else:
                    log_to_file(f"當前價格未創新高，移動止損點保持為: ${stop_loss_price:.2f}")
            else:
                # 固定止損邏輯
                stop_loss_price = entry_price - (STOP_LOSS / quantity)
                log_to_file(f"固定止損點: ${stop_loss_price:.2f}")

            # 判斷止損條件
            if current_price <= stop_loss_price:
                log_to_file(f"觸發止損條件，賣出持倉: {symbol}")
                result = place_order(BASE_URL, headers, account_hash, symbol, quantity, current_price,
                                     action="SELL")
                if result.get("status") == "success":
                    log_to_file(f"止損成功，賣出 {quantity} 股 {symbol} @ ${current_price:.2f}")
                else:
                    log_to_file(f"止損失敗: {result.get('error')}", "ERROR")
                break

            # **判斷加碼條件**
            if current_price >= target_add_price and (datetime.now() - last_order_time).seconds > cooldown_seconds:
                log_to_file(f"觸發加碼條件，嘗試買入: {symbol}")
                shares_to_buy = math.ceil(BUY_AMOUNT / current_price)
                result = place_order(BASE_URL, headers, account_hash, symbol, shares_to_buy, current_price,
                                     action="BUY")
                if result.get("status") == "success":
                    log_to_file(f"加碼成功，買入 {shares_to_buy} 股 {symbol} @ ${current_price:.2f}")
                    last_order_time = datetime.now()
                    # 更新平均成本與止損點
                    total_cost = (quantity * entry_price) + (shares_to_buy * current_price)
                    quantity += shares_to_buy
                    entry_price = total_cost / quantity
                    stop_loss_price = max(
                        highest_price * (1 - dynamic_stop_loss_pct),
                        entry_price * (1 + minimum_profit_threshold)
                    )
                    log_to_file(f"加碼後新止損點為: ${stop_loss_price:.2f}")
                else:
                    log_to_file(f"加碼失敗: {result.get('error')}", "ERROR")

            log_to_file("等待下一次價格檢查...")
            time.sleep(30)

    except KeyboardInterrupt:
        log_to_file("策略被手動中止。")


def send_telegram_notification(message, BOT_TOKEN, CHAT_ID, log_type="INFO"):
    """
    使用 Telegram 發送通知，並記錄到日誌。
    :param message: 發送的消息內容
    :param bot_token: Telegram Bot 的 API Token
    :param chat_id: 接收消息的聊天 ID
    :param log_type: 日誌類型，例如 "INFO", "ERROR", "TRADE"
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_file(f"通知已發送: {message}", log_type)
    except requests.exceptions.RequestException as e:
        log_to_file(f"通知發送失敗: {e}", "ERROR")


def refresh_access_token_periodically(headers):
    """
    自動每 30 分鐘刷新一次 Access Token，支持重試並增加詳細日誌。
    """
    global access_token
    global token_expiry

    if datetime.now() >= token_expiry:
        log_to_file("Access Token 即將過期，嘗試刷新...")

        for attempt in range(3):  # 最多重試 3 次
            try:
                # 嘗試獲取新 Token
                access_token = get_valid_access_token()
                if access_token:
                    # 更新 Headers 和 Token 過期時間
                    headers['Authorization'] = f'Bearer {access_token}'
                    token_expiry = datetime.now() + timedelta(minutes=30)

                    # 驗證保存是否成功
                    with open(TOKEN_FILE, "r") as f:
                        tokens = json.load(f)
                        if tokens.get("access_token") == access_token:
                            log_to_file(f"Access Token 刷新成功並保存 (重試次數: {attempt + 1})。")
                            return
                        else:
                            log_to_file("Access Token 刷新成功但保存到文件失敗，檢查文件操作。", "ERROR")
                else:
                    log_to_file(f"Access Token 刷新失敗，無法獲得新 Token。重試次數: {attempt + 1}", "ERROR")

            except Exception as e:
                # 捕獲刷新過程中的異常
                log_to_file(f"Access Token 刷新過程中發生異常: {str(e)} (重試次數: {attempt + 1})", "ERROR")

            # 重試之間增加短暫延遲
            time.sleep(5)

        # 最終失敗處理
        log_to_file("Access Token 刷新最終失敗，程序將繼續嘗試使用現有 Token，但可能出現錯誤。", "ERROR")


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
    send_telegram_notification("交易腳本已啟動", BOT_TOKEN, CHAT_ID)

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