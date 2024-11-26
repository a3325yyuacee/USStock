import requests
import json
from auth import get_valid_access_token


def get_account_hash(base_url, headers):
    """
    查詢加密帳號值 (hashValue)
    """
    response = requests.get(f'{base_url}/accounts/accountNumbers', headers=headers)
    if response.status_code == 200:
        linked_accounts = response.json()
        print("已成功取得加密帳號：")
        print(json.dumps(linked_accounts, indent=4))
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

if __name__ == "__main__":
    # 設置基礎 URL 和取得有效的 access_token
    base_url = "https://api.schwabapi.com/trader/v1/"
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    # 查詢帳戶的加密哈希值
    account_hash = get_account_hash(base_url, headers)
    print(f"帳戶加密哈希值：{account_hash}")

    # 執行下單操作
    symbol = "TSLA"      # 股票代號
    quantity = 5         # 下單數量
    price = 200.00       # 每股價格
    place_order(base_url, headers, account_hash, symbol, quantity, price)
