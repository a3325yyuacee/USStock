import requests
import json
import base64
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# 載入環境變數
load_dotenv()

appKey = os.getenv("APP_KEY")
appSecret = os.getenv("APP_SECRET")

if not appKey or not appSecret:
    raise ValueError("APP_KEY 或 APP_SECRET 未在 .env 中設定")

TOKEN_FILE = "tokens.json"

def authenticate_user():
    """
    用戶授權以取得 access_token 和 refresh_token。
    """
    authUrl = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={appKey}&redirect_uri=https://127.0.0.1'
    print(f"點擊此連結以完成授權：{authUrl}")
    returnedLink = input("授權完成後，請貼上回調的 URL：")

    # 從回調的 URL 中提取授權碼
    query_params = parse_qs(urlparse(returnedLink).query)
    code = query_params.get('code', [None])[0]
    if not code:
        raise ValueError("未在回調的 URL 中找到授權碼")

    # 構建請求以取得 access_token
    headers = {
        'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8")}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://127.0.0.1'
    }

    response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
    if response.status_code == 200:
        tokens = response.json()
        tokens['expires_at'] = (datetime.utcnow() + timedelta(seconds=tokens['expires_in'])).isoformat()
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        print("Token 已成功保存到 tokens.json")
    else:
        print("授權失敗")
        print(response.text)
        exit(1)


def refresh_access_token():
    """
    使用 refresh_token 更新 access_token。
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print("無法找到 tokens.json 文件，請先執行 authenticate_user")
        exit(1)

    refresh_token = tokens.get('refresh_token')
    headers = {
        'Authorization': f'Basic {base64.b64encode(bytes(f"{appKey}:{appSecret}", "utf-8")).decode("utf-8")}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
    if response.status_code == 200:
        new_tokens = response.json()
        new_tokens['expires_at'] = (datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])).isoformat()
        with open(TOKEN_FILE, "w") as f:
            json.dump(new_tokens, f)
        print("Access token 已更新並保存到 tokens.json")
        return new_tokens['access_token']
    else:
        print("更新 access_token 失敗")
        print(response.text)
        exit(1)


def get_valid_access_token():
    """
    檢查 access_token 是否有效，若無效則自動更新。
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print("無法找到 tokens.json 文件，請先執行 authenticate_user")
        exit(1)

    expires_at = tokens.get('expires_at')
    if expires_at and datetime.utcnow() < datetime.fromisoformat(expires_at):
        # 如果 access_token 還有效
        return tokens['access_token']
    else:
        # access_token 過期，使用 refresh_token 更新
        print("Access token 已過期，正在更新...")
        return refresh_access_token()


if __name__ == "__main__":
    # 第一次需要進行用戶授權
    authenticate_user()
