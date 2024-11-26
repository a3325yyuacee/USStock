import requests
import json
import base64
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os

# 載入環境變數
load_dotenv()

appKey = os.getenv("APP_KEY")
appSecret = os.getenv("APP_SECRET")

if not appKey or not appSecret:
    raise ValueError("APP_KEY or APP_SECRET is not set in .env file")

# 提供授權 URL 給用戶
authUrl = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={appKey}&redirect_uri=https://127.0.0.1'
print(f"Click to authenticate: {authUrl}")

# 用戶完成授權後，粘貼回調 URL
returnedLink = input("Paste the redirect URL here: ")

# 提取授權碼
query_params = parse_qs(urlparse(returnedLink).query)
code = query_params.get('code', [None])[0]
if not code:
    raise ValueError("Authorization code not found in the redirect URL.")

# 請求 Access Token 的 headers 和資料
headers = {
    'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8")}',
    'Content-Type': 'application/x-www-form-urlencoded'
}
data = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': 'https://127.0.0.1'
}

# 發送請求以獲取 Access Token
response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)

# 檢查請求結果
if response.status_code == 200:
    tokens = response.json()
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    if not access_token:
        raise KeyError("The response does not contain 'access_token'.")

    # 保存 Tokens 到文件
    with open("tokens.json", "w") as f:
        json.dump(tokens, f)
        print("Tokens saved to tokens.json")

    print(f"Access token: {access_token}")
    print(f"Refresh token: {refresh_token}")
else:
    print(f"Error: Unable to fetch access token. Status code: {response.status_code}")
    print(response.text)
    exit(1)

# 使用 Access Token 調用 API 查詢帳戶資訊及持倉
base_url = "https://api.schwabapi.com/trader/v1/"
headers = {'Authorization': f'Bearer {access_token}'}

# 查詢帳戶及持倉
params = {'fields': 'positions'}
response = requests.get(f'{base_url}/accounts', headers=headers, params=params)

# 獲取帳戶資料
if response.status_code == 200:
    accounts_data = response.json()
    print("Accounts and positions retrieved successfully:")
    print(json.dumps(accounts_data, indent=4))
    # 提取第一個帳戶的加密值
    account_number = accounts_data[0]['securitiesAccount']['accountNumber']
    print(f"Account number: {account_number}")
else:
    print(f"Error retrieving accounts and positions: {response.status_code}")
    print(response.text)
    exit(1)

# 整合下單功能
def place_order(account_hash, symbol, quantity, price):
    """
    下單功能
    :param account_hash: 帳戶哈希值
    :param symbol: 股票代號
    :param quantity: 下單數量
    :param price: 下單價格
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

    # 發送下單請求
    response = requests.post(
        f'{base_url}/accounts/{account_hash}/orders',
        headers={**headers, "Content-Type": "application/json"},
        json=order
    )

    # 檢查下單結果
    if response.status_code == 201:
        print("Order placed successfully.")
        order_id = response.headers.get('location', '/').split('/')[-1]
        print(f"Order ID: {order_id}")
    else:
        print(f"Failed to place order. Status code: {response.status_code}")
        print(response.text)

# 嘗試獲取加密的帳號
response = requests.get(f'{base_url}/accounts/accountNumbers', headers=headers)

if response.status_code == 200:
    linked_accounts = response.json()
    print("Linked accounts retrieved successfully:")
    print(json.dumps(linked_accounts, indent=4))

    # 獲取第一個帳戶的加密值
    account_hash = linked_accounts[0].get('hashValue')  
    print(f"Account hash (encrypted): {account_hash}")
else:
    print(f"Error retrieving linked accounts: {response.status_code}")
    print(response.text)
    exit(1)

# 測試下單
symbol = "TSLA"
quantity = 5
price = 200.00

place_order(account_hash, symbol, quantity, price)
