import requests
import json
from auth import get_valid_access_token
from datetime import datetime, timedelta



def get_account_hash(base_url, headers):
    """
    查詢加密帳號值 (hashValue)
    """
    response = requests.get(f'{base_url}/accounts/accountNumbers', headers=headers)
    if response.status_code == 200:
        linked_accounts = response.json()
        print("已成功取得加密帳號：")
        # print(json.dumps(linked_accounts, indent=4))
        return linked_accounts[0].get('hashValue')
    else:
        print("無法取得加密帳號")
        print(response.text)
        exit(1)
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

def place_order(base_url, headers, account_hash, symbol, quantity, price, action="BUY"):
    """
    通用下單功能，支持買入 (BUY) 或賣出 (SELL)。
    """
    order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "price": str(price),
        "orderLegCollection": [
            {
                "instruction": action,  # BUY 或 SELL
                "quantity": abs(quantity),  # 確保數量為正
                "instrument": {
                    "symbol": symbol,
                    "assetType": "EQUITY"
                }
            }
        ]
    }

    response = requests.post(
        f'{base_url}/accounts/{account_hash}/orders',
        headers={**headers, "Content-Type": "application/json"},
        json=order
    )

    if response.status_code == 201:
        log_to_file(f"下單成功: {action} {quantity} 股 {symbol} @ ${price:.2f}")
        return {"status": "success", "order_id": response.headers.get('location', '/').split('/')[-1]}
    else:
        log_to_file(f"下單失敗: {response.text}", "ERROR")
        return {"status": "error", "error": response.text}


def check_order_status(base_url, headers, account_hash, order_id):
    """
    查詢訂單狀態
    """
    response = requests.get(
        f"{base_url}/accounts/{account_hash}/orders/{order_id}",
        headers=headers
    )
    if response.status_code == 200:
        order_status = response.json()
        
        # 提取關鍵資訊
        # print("\n訂單詳情：")
        print(f"訂單編號：{order_status.get('orderId')}")
        print(f"訂單狀態：{order_status.get('status')}")
        print(f"股票代號：{order_status['orderLegCollection'][0]['instrument']['symbol']}")
        print(f"買入/賣出：{order_status['orderLegCollection'][0]['instruction']}")
        print(f"訂單數量：{order_status.get('quantity')}")
        print(f"已成交數量：{order_status.get('filledQuantity')}")
        print(f"剩餘數量：{order_status.get('remainingQuantity')}")
        print(f"價格：{order_status.get('price')}")
        # print(f"進入時間：{order_status.get('enteredTime')}")
        # print(f"關閉時間：{order_status.get('closeTime')}")
        # print(f"取消狀態：{'是' if order_status.get('cancelable') else '否'}")
        # print(f"可編輯狀態：{'是' if order_status.get('editable') else '否'}")
        # print(f"詳細描述：{order_status.get('statusDescription')}")
        
        # 返回 JSON 作為調試用
        return order_status
    else:
        print("查詢訂單狀態失敗")
        print(response.text)
        exit(1)

def get_all_orders(base_url, headers, max_results=100, status=None, from_date=None, to_date=None, symbol=None, min_qty=None, max_qty=None):
    """
    查詢所有帳戶的訂單，支援多種篩選條件
    """
    # from_date = format_date(from_date)
    # to_date = format_date(to_date)

    params = {
        "maxResults": max_results,
        "fromEnteredTime": from_date,
        "toEnteredTime": to_date,
    }
    if status:
        params["status"] = status

    response = requests.get(
        f"{base_url}/orders",
        headers=headers,
        params=params
    )

    if response.status_code == 200:
        orders = response.json()
        if not orders:
            print("查詢條件下無符合的訂單。請嘗試調整條件。")
            return []

        print("\n所有訂單：")
        for order in orders:
            # 進一步篩選和打印訂單
            order_symbol = order['orderLegCollection'][0]['instrument']['symbol']
            if symbol and order_symbol != symbol:
                continue

            print(f"訂單編號：{order.get('orderId')}")
            print(f"狀態：{order.get('status')}")
            print(f"股票代號：{order_symbol}")
            print(f"數量：{order.get('quantity')}")
            print(f"價格：{order.get('price')}")
            print(f"進入時間：{order.get('enteredTime')}")
            print(f"狀態描述：{order.get('statusDescription')}")
            print("-" * 40)
        return orders
    else:
        print("查詢全部訂單失敗")
        print(response.text)
        return []



if __name__ == "__main__":
    # 設置基礎 URL 和取得有效的 access_token
    base_url = "https://api.schwabapi.com/trader/v1/"
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    # 查詢帳戶的加密哈希值
    account_hash = get_account_hash(base_url, headers)

    # 主操作流程
    while True:
        print("\n選擇操作：")
        print("1. 下單")
        print("2. 查詢訂單狀態")
        print("3. 查詢所有訂單")
        print("4. 離開")
        choice = input("請輸入選項：")
        
        if choice == "1":
            # 下單操作
            print("請輸入下單條件：")
            symbol = input("股票代號：")
            try:
                quantity = int(input("買入數量："))
            except ValueError:
                print("買入數量應為整數，請重新執行程式")
                continue
            try:
                price = float(input("下單價格："))
            except ValueError:
                print("下單價格應為數字，請重新執行程式")
                continue
            order_id = place_order(base_url, headers, account_hash, symbol, quantity, price)
            print(f"已成功下單，訂單編號：{order_id}")

        elif choice == "2":
            # 查詢訂單狀態
            order_id = input("請輸入要查詢的訂單編號：")
            order_details = check_order_status(base_url, headers, account_hash, order_id)

        elif choice == "3":
            # 查詢全部訂單
            print("\n查詢所有訂單：")
            status = input("輸入訂單狀態過濾條件（如 FILLED, CANCELED，或按 Enter 跳過）：")
            symbol = input("輸入股票代號過濾條件（如 AAPL，或按 Enter 跳過）：")
            try:
                from_date = input("開始日期 (格式: yyyy-MM-dd，例如 2024-11-20) 或按 Enter 預設：")
                to_date = input("結束日期 (格式: yyyy-MM-dd，例如 2024-11-27) 或按 Enter 預設：")
                min_qty = input("輸入最小數量過濾條件（或按 Enter 跳過）：")
                max_qty = input("輸入最大數量過濾條件（或按 Enter 跳過）：")

                # 將最小和最大數量轉為數字類型
                min_qty = int(min_qty) if min_qty else None
                max_qty = int(max_qty) if max_qty else None

                # 查詢訂單
                orders = get_all_orders(
                    base_url,
                    headers,
                    status=status or None,
                    from_date=from_date or None,
                    to_date=to_date or None,
                    symbol=symbol or None,
                    min_qty=min_qty,
                    max_qty=max_qty
                )
            except Exception as e:
                print(f"查詢過程中出現錯誤：{e}")

        elif choice == "4":
            print("已退出程式")
            break

        else:
            print("無效選項，請重新選擇")