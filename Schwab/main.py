import requests
import base64
from urllib.parse import urlparse, parse_qs


appKey = "eTOdlULAGAECJta6idElCFNAnpomwdFt"
appSecret = "6pEuGP4RMdMI8R4R"

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
    print(f"Error: Unable to fetch account information. Status code: {response.status_code}")
    print(response.text)


# authUrl = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={appKey}&redirect_uri=https://127.0.0.1'

# print(f"Click to authenticate: {authUrl}")

# returnedLink = input("Pase the redirect URL here:")

# code = f"{returnedLink[returnedLink.index('code=')+5:returnedLink.index('%40')]}@"

# headers = {'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8") }', 'Content-Type': 'application/x-www-form-urlencoded'}
# data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': 'https://127.0.0.1'}

# response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
# td = response.json()

# access_token = td['access_token']
# refresh_token = td['refresh_token']

# base_url = "https://api.schwabapi.com/trader/v1/"

# response = requests.get(f'{base_url}/accounts/accountNumbers', headers={'Authorization': f'Bearer {access_token}'})

# print(response.json())