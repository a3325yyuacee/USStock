import requests
import base64
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
import os

load_dotenv()

appKey = os.getenv("APP_KEY")
appSecret = os.getenv("APP_SECRET")

if not appKey or not appSecret:
    raise ValueError("APP_KEY or APP_SECRET is not set in .env file")
    
# OAuth 授權 URL
authUrl = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={appKey}&redirect_uri=https://127.0.0.1'

# 提示用戶完成授權
print(f"Click to authenticate: {authUrl}")

# 獲取用戶授權後的返回 URL
returnedLink = input("Paste the redirect URL here:")

# 提取授權碼 (code)
query_params = parse_qs(urlparse(returnedLink).query)
code = query_params.get('code', [None])[0]
if not code:
    raise ValueError("Authorization code not found in the redirect URL.")

# 構建請求頭與請求體
headers = {
    'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8")}',
    'Content-Type': 'application/x-www-form-urlencoded'
}
data = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': 'https://127.0.0.1'
}

# 請求 Access Token
response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)

# 檢查是否請求成功
if response.status_code == 200:
    td = response.json()
    access_token = td.get('access_token')
    refresh_token = td.get('refresh_token')
    if not access_token:
        raise KeyError("The response does not contain 'access_token'.")
    print(f"Access token: {access_token}")
    print(f"Refresh token: {refresh_token}")
else:
    print(f"Error: Unable to fetch access token. Status code: {response.status_code}")
    print(response.text)
    exit(1)

# 使用 Access Token 請求用戶帳戶資訊
base_url = "https://api.schwabapi.com/trader/v1/"
response = requests.get(f'{base_url}/accounts/accountNumbers', headers={'Authorization': f'Bearer {access_token}'})

# 打印帳戶資訊
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error retrieving accounts and positions: {response.status_code}")
    print(response.text)
    exit(1)

# 下單功能
# 構建下單的 JSON 請求結構
order_payload = {
    "session": "NORMAL",              # 訂單執行會話類型
    "duration": "DAY",                # 訂單有效期，"DAY" 表示當日有效
    "orderType": "MARKET",            # 訂單類型（市價單）
    "orderLegCollection": [
        {
            "orderLegType": "EQUITY",  # 資產類型（股票）
            "instrument": {
                "symbol": "AAPL",      # 股票代碼
                "type": "EQUITY"       # 資產類型
            },
            "instruction": "BUY",      # 動作（買入）
            "positionEffect": "OPENING", # 開倉
            "quantity": 1             # 買入數量，必須大於零
        }
    ],
    "orderStrategyType": "SINGLE"     # 單一訂單
}

print("Placing order...")
response = requests.post(f"{base_url}/accounts/{account_number}/orders", headers=headers, json=order_payload)

# 處理下單回應
if response.status_code == 201:
    print("Order placed successfully.")
    print("Order details:")
    print(response.headers.get('Location'))  # 回應的 Header 包含新訂單的連結
else:
    print(f"Failed to place order. Status code: {response.status_code}")
    print(response.json())  # 打印錯誤資訊
