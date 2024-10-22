import requests
import sys

# 獲取 access_token 的函數
def get_access_token(client_id, client_secret):
    url = "https://api.schwabapi.com/v1/oauth/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        return None

# 模擬通過 API 下單
def place_order(access_token, account_number, order_data):
    url = f"https://api.schwabapi.com/v1/accounts/{account_number}/orders"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.post(url, headers=headers, json=order_data)
    return response.status_code == 201

def run_trading_bot():
    print("Running trading bot...")
    access_token = get_access_token('your_client_id', 'your_client_secret')
    if access_token:
        order_data = {'symbol': 'AAPL', 'quantity': 10}
        place_order(access_token, 'your_account_number', order_data)
    sys.exit()
