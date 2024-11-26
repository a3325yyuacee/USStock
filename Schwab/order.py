import requests
import json

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

def place_order(base_url, account_hash, headers, symbol, quantity, price):
    """
    下單功能
    """
    order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "price": str(price),
        "orderLegCollection": [
            {
                "instruction": "BUY",
                "quantity": quantity,
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
        print("下單成功")
        order_id = response.headers.get('location', '/').split('/')[-1]
        print(f"訂單編號：{order_id}")
        return order_id
    else:
        print("下單失敗")
        print(response.text)
        exit(1)

if __name__ == "__main__":
    # 從 tokens.json 中讀取 access_token
    with open("tokens.json", "r") as f:
        tokens = json.load(f)

    access_token = tokens['access_token']
    base_url = "https://api.schwabapi.com/trader/v1/"
    headers = {'Authorization': f'Bearer {access_token}'}

    # 取得加密帳號
    account_hash = get_account_hash(base_url, headers)

    # 執行下單
    symbol = "TSLA"
    quantity = 5
    price = 200.00
    place_order(base_url, account_hash, headers, symbol, quantity, price)
