import requests
import base64

appKey = "aaa"
appSecret = "bbb"

# 構建授權 URL
authUrl = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={appKey}&response_type=code&redirect_uri=https://developer.schwab.com/oauth2-redirect.html'
print(f"Click to authenticate: {authUrl}")

# 提示用戶粘貼返回的 URL
returnedLink = input ("Pase the redirect URL here:")

# 從返回的 URL 中提取授權碼 (code)
try:
    code = returnedLink.split("code=")[1].split("&")[0]
except IndexError:
    print("Error: Unable to extract authorization code from the provided URL.")
    exit()

# 編碼 app_key 和 app_secret 並設置 Authorization 標頭
headers = {'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8")}', 'Content-Type': 'application/x-www-form-urlencoded'}

# 構建請求資料
data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': 'https://developer.schwab.com/oauth2-redirect.html'}

# 發送 POST 請求以獲取 access_token
response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)

# 處理返回的 token
if response.status_code == 200:
    td = response.json()
    access_token = td['access_token']
    refresh_token = td['refresh_token']
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")

    # 使用 access_token 發送 API 請求，這裡是範例
    base_url = "https://api.schwabapi.com/trader/v1/"
    response = requests.get(f'{base_url}/accounts/accountNumbers', headers={'Authorization': f'Bearer {access_token}'})
    
     # 檢查 API 請求結果
    if response.status_code == 200:
        print("Account Data:", response.json())
    else:
        print(f"Error fetching account data: {response.status_code}, {response.text}")

else:
    print(f"Error: {response.status_code}, {response.text}")