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
headers = {'Authorization': f'Bearer {access_token}'}  # 更新為 Bearer 認證

# 查詢帳戶資訊及持倉資訊
params = {'fields': 'positions'}  # 添加查詢參數以獲取持倉
response = requests.get(f'{base_url}/accounts', headers=headers, params=params)

# 檢查回應並解析數據
if response.status_code == 200:
    accounts_data = response.json()
    print("Accounts and positions retrieved successfully:")
    for account in accounts_data:
        account_info = account.get('securitiesAccount', {})
        account_number = account_info.get('accountNumber')
        positions = account_info.get('positions', [])
        print(f"Account Number: {account_number}")
        if positions:
            print("Positions:")
            for position in positions:
                symbol = position['instrument'].get('symbol', 'N/A')
                quantity = position.get('longQuantity', 0)
                market_value = position.get('marketValue', 0)
                print(f"  Symbol: {symbol}, Quantity: {quantity}, Market Value: {market_value}")
        else:
            print("  No positions found for this account.")
else:
    print(f"Error retrieving accounts and positions: {response.status_code}")
    print(response.text)