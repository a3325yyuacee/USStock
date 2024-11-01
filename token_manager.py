from datetime import datetime, timedelta
import json
import requests
import base64
from loguru import logger

class TokenManager:
    def __init__(self, app_key, app_secret, token_file='tokens.json'):
        self.app_key = app_key
        self.app_secret = app_secret
        self.token_file = token_file

    def load_tokens(self):
        """讀取存儲的令牌"""
        try:
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
            logger.info("令牌已加載成功")
            return tokens
        except FileNotFoundError:
            logger.error("Token file not found.")
            return None

    def save_tokens(self, tokens):
        """保存令牌到文件"""
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f)
        logger.info("令牌已成功更新並保存")

    def refresh_access_token(self):
        """使用 refresh token 獲取新的 access token"""
        tokens = self.load_tokens()
        if not tokens or 'refresh_token' not in tokens:
            logger.error("No refresh token found. Please authenticate first.")
            return None

        refresh_token = tokens['refresh_token']
        
        # 構建 headers 和 payload
        credentials = f"{self.app_key}:{self.app_secret}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(
            "https://api.schwabapi.com/v1/oauth/token",
            headers=headers,
            data=payload
        )

        if response.status_code == 200:
            new_tokens = response.json()
            logger.info("成功刷新 access token")

            # 去除 `@` 符號，確保符合 API 要求
            new_tokens['access_token'] = new_tokens['access_token'].replace('@', '')
            new_tokens['refresh_token'] = new_tokens['refresh_token'].replace('@', '')

            # 計算並添加 expires_at 到 tokens 字典
            expires_in = new_tokens.get('expires_in', 1800)  # 默認為 1800 秒（30 分鐘）
            new_tokens['expires_at'] = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            # 更新 tokens 並保存到文件
            tokens['access_token'] = new_tokens['access_token']
            tokens['refresh_token'] = new_tokens['refresh_token']
            tokens['expires_at'] = new_tokens['expires_at']  # 添加 expires_at 時間

            self.save_tokens(tokens)
            return new_tokens['access_token']
        else:
            logger.error(f"刷新 access token 失敗: {response.text}")
            return None
            
    def get_access_token(self):
        """獲取當前有效的 access token，若即將過期或不存在 expires_at 則刷新"""
        tokens = self.load_tokens()
        if not tokens:
            return None

        # 如果 tokens 中沒有 'expires_at'，則刷新 token 並生成
        if 'expires_at' not in tokens:
            logger.info("令牌缺少 expires_at，嘗試刷新")
            return self.refresh_access_token()

        # 檢查過期時間
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        if datetime.now() >= expires_at:
            logger.info("Access token 已過期，嘗試刷新")
            return self.refresh_access_token()
        
        return tokens['access_token']

