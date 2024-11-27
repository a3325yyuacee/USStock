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

def place_order(base_url, headers, account_hash, symbol, quantity, price):
    """
    下單功能
    """
    order = {
        "orderType": "LIMIT",                # 限價單
        "session": "NORMAL",                 # 常規交易時段
        "duration": "DAY",                   # 當日有效
        "orderStrategyType": "SINGLE",       # 單筆交易
        "price": str(price),                 # 下單價格
        "orderLegCollection": [
            {
                "instruction": "BUY",        # 買入
                "quantity": quantity,        # 買入數量
                "instrument": {
                    "symbol": symbol,        # 股票代號
                    "assetType": "EQUITY"    # 資產類型
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
        print("下單成功")
        order_id = response.headers.get('location', '/').split('/')[-1]
        print(f"訂單編號：{order_id}")
        return order_id
    else:
        print("下單失敗")
        print(response.text)
        exit(1)

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
    # 預設查詢時間範圍為最近 7 天
    if not from_date:
        from_date = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT00:00:00.000Z')
    else:
        from_date = f"{from_date}T00:00:00.000Z"  # 自動補全起始時間
    if not to_date:
        to_date = datetime.utcnow().strftime('%Y-%m-%dT23:59:59.999Z')
    else:
        to_date = f"{to_date}T23:59:59.999Z"  # 自動補全結束時間

    # 建立請求參數
    params = {
        "maxResults": max_results,
        "fromEnteredTime": from_date,
        "toEnteredTime": to_date,
    }
    if status:
        params["status"] = status

    # 發送請求
    response = requests.get(
        f"{base_url}/orders",
        headers=headers,
        params=params
    )

    if response.status_code == 200:
        orders = response.json()
        print("\n所有訂單：")
        filtered_orders = []
        for order in orders:
            # 進一步篩選（如股票代號、數量範圍）
            order_symbol = order['orderLegCollection'][0]['instrument']['symbol']
            order_qty = order.get('quantity', 0)

            if symbol and order_symbol != symbol:
                continue
            if min_qty and order_qty < min_qty:
                continue
            if max_qty and order_qty > max_qty:
                continue

            # 打印符合條件的訂單
            print(f"訂單編號：{order.get('orderId')}")
            print(f"狀態：{order.get('status')}")
            print(f"股票代號：{order_symbol}")
            print(f"買入/賣出：{order['orderLegCollection'][0]['instruction']}")
            print(f"數量：{order_qty}")
            print(f"價格：{order.get('price')}")
            print(f"進入時間：{order.get('enteredTime')}")
            print(f"狀態描述：{order.get('statusDescription')}")
            print("-" * 40)
            filtered_orders.append(order)

        return filtered_orders
    else:
        print("查詢全部訂單失敗")
        print(response.text)
        exit(1)



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