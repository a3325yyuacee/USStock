import requests
import time
import os
from tabulate import tabulate
from datetime import datetime, timedelta
from auth import get_valid_access_token, refresh_access_token


def clear_console():
    """
    清空控制台，避免在不支持 TERM 的環境中出錯
    """
    if os.name == 'nt':  # Windows
        os.system('cls')
    elif os.environ.get("TERM"):  # 有終端支持的其他環境
        os.system('clear')
    else:  # 不支持清理時
        print("\n" * 100)


def get_stock_price(api_key, symbol):
    """
    使用直接 HTTP 請求調用 Finnhub API 獲取即時股票價格
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


def display_positions_with_prices(base_url, headers, finnhub_api_key):
    """
    查詢帳戶持倉及股票當前價格，計算總市值和每隻股票的獲利百分比，並以表格形式輸出
    """
    params = {'fields': 'positions'}
    response = requests.get(f'{base_url}/accounts', headers=headers, params=params)

    if response.status_code == 200:
        accounts_data = response.json()
        total_market_value = 0  # 初始化總市值
        account_results = []  # 暫存每個帳戶的總市值資訊

        for account in accounts_data:
            account_info = account.get('securitiesAccount', {})
            account_number = account_info.get('accountNumber', '未知帳號')
            cash_balance = account_info.get('currentBalances', {}).get('cashBalance', 0.0)

            print(f"\n帳號: {account_number}")
            print(f"現金餘額: ${cash_balance:,.2f}")

            positions = account_info.get('positions', [])
            account_market_value = cash_balance  # 每個帳戶的總市值
            table_data = []  # 用於存儲表格資料

            if positions:
                for position in positions:
                    symbol = position['instrument'].get('symbol', '未知股票')
                    quantity = position.get('longQuantity', 0.0)
                    cost_price = position.get('averagePrice', 0.0)  # 持倉的平均成本價
                    current_price = get_stock_price(finnhub_api_key, symbol)

                    if current_price is not None:
                        current_market_value = quantity * current_price
                        profit_percent = ((current_price - cost_price) / cost_price) * 100 if cost_price > 0 else 0

                        account_market_value += current_market_value
                        table_data.append([
                            symbol, quantity, f"${cost_price:,.2f}", f"${current_price:,.2f}",
                            f"${current_market_value:,.2f}", f"{profit_percent:.2f}%"
                        ])
                    else:
                        table_data.append([
                            symbol, quantity, f"${cost_price:,.2f}", "無法獲取", "未知", "未知"
                        ])
                # 打印表格
                print(tabulate(
                    table_data,
                    headers=["股票代號", "持股數量", "成本價", "當前股價", "市值", "獲利百分比"],
                    tablefmt="grid"
                ))
            else:
                print("  此帳戶無持倉。")

            # 累計總市值
            total_market_value += account_market_value
            account_results.append([account_number, f"${cash_balance:,.2f}", f"${account_market_value:,.2f}"])

        # 打印帳戶總市值
        print("\n所有帳戶總市值：")
        print(tabulate(
            account_results,
            headers=["帳號", "現金餘額", "帳戶總市值"],
            tablefmt="grid"
        ))
        print(f"\n整體帳戶總市值：${total_market_value:,.2f}")

    else:
        print("查詢帳戶及持倉失敗")
        print(f"錯誤代碼: {response.status_code}")
        print(response.text)



if __name__ == "__main__":
    if not os.environ.get("TERM"):
        os.environ["TERM"] = "xterm"

    # 獲取 Finnhub API 金鑰
    finnhub_api_key = os.getenv("FINNHUB_API_KEY")
    if not finnhub_api_key:
        print("錯誤: 未在環境變量中找到 FINNHUB_API_KEY。請配置後重試。")
        exit(1)

    base_url = "https://api.schwabapi.com/trader/v1/"
    access_token = get_valid_access_token()  # 使用原本的方式獲取 Access Token
    headers = {'Authorization': f'Bearer {access_token}'}
    token_expiry = datetime.now() + timedelta(minutes=30)  # 假設 Token 有效期為 30 分鐘

    try:
        while True:
            # 如果 Token 即將過期，刷新 Token
            if datetime.now() >= token_expiry:
                print("Access Token 即將過期，正在刷新...")
                access_token = get_valid_access_token()  # 重新調用你的函數
                if access_token:
                    headers = {'Authorization': f'Bearer {access_token}'}
                    token_expiry = datetime.now() + timedelta(minutes=30)
                    print("Access Token 刷新成功。")
                else:
                    print("刷新 Access Token 失敗，請檢查憑證或網絡連線。")
                    break

            # 執行查詢和更新
            print("更新持倉及當前股價中...")
            display_positions_with_prices(base_url, headers, finnhub_api_key)
            print("\n下一次更新將在 30 秒後...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n程序已手動中止。")