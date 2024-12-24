import requests
import time  # 修復 NameError
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
from auth import get_valid_access_token
from order import get_account_hash

# 加載 .env 配置
load_dotenv()

# 配置常量
BASE_URL = "https://api.schwabapi.com/trader/v1/"


def get_all_orders(base_url, headers, account_hash, days=3):
    """
    查詢帳戶中所有目前的訂單，包含必需的查詢參數
    """
    now = datetime.now(timezone.utc)
    from_time = now - timedelta(days=days)

    from_time_str = from_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_time_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"{base_url.rstrip('/')}/accounts/{account_hash}/orders"
    params = {
        "fromEnteredTime": from_time_str,
        "toEnteredTime": to_time_str
    }
    # print(f"查詢所有訂單 URL: {url}")
    # print(f"查詢參數: {params}")
    # print(f"Headers: {headers}")

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        orders = response.json()
        if not orders:
            print("目前無任何訂單。")
            return []
        print(f"成功查詢到 {len(orders)} 筆訂單。")
        return orders
    else:
        print(f"查詢訂單失敗，HTTP 狀態碼: {response.status_code}")
        print(f"響應內容: {response.text}")
        return None


def cancel_order(base_url, headers, account_hash, order_id):
    """
    取消指定帳戶中的特定訂單
    """
    url = f"{base_url.rstrip('/')}/accounts/{account_hash}/orders/{order_id}"
    # print(f"取消訂單 URL: {url}")
    # print(f"Headers: {headers}")

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"訂單 {order_id} 已成功取消。")
        return True
    else:
        print(f"取消訂單 {order_id} 失敗，HTTP 狀態碼: {response.status_code}")
        # print(f"響應內容: {response.text}")
        return False


def cancel_all_orders(base_url, headers, account_hash, limit=50):
    """
    取消所有目前的訂單，加入狀態檢查和限量
    """
    orders = get_all_orders(base_url, headers, account_hash)
    if orders is None:
        print("未能成功獲取訂單，無法進行取消操作。")
        return

    canceled_orders = []
    failed_orders = []
    count = 0

    for order in orders:
        if count >= limit:  # 限制取消的訂單數量
            print(f"已達到本次執行的取消限制數量：{limit}")
            break

        order_id = order.get("orderId")
        order_status = order.get("status")

        # 跳過無法取消的訂單
        if order_status in ["CANCELED", "REJECTED", "FILLED", "REPLACED", "EXPIRED"]:
            print(f"跳過訂單 {order_id}，狀態為: {order_status}")
            continue

        print(f"正在取消訂單 ID: {order_id}，狀態: {order_status}")
        if cancel_order(base_url, headers, account_hash, order_id):
            canceled_orders.append(order_id)
        else:
            failed_orders.append(order_id)

        count += 1
        time.sleep(1)  # 增加延遲，避免請求過於頻繁

    # 報告結果
    print("\n取消操作完成。")
    print(f"成功取消的訂單數量: {len(canceled_orders)}")
    print(f"失敗的訂單數量: {len(failed_orders)}")

    if failed_orders:
        print("以下訂單無法取消:")
        for order_id in failed_orders:
            print(f" - 訂單 ID: {order_id}")


if __name__ == "__main__":
    # 初始化 API 和帳戶資料
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    account_hash = get_account_hash(BASE_URL, headers)  # 取得帳號的 hashValue

    print(f"已成功取得加密帳號：{account_hash}")
    print("正在取消所有目前的訂單...")
    cancel_all_orders(BASE_URL, headers, account_hash, limit=10)
