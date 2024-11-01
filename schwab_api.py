import requests
from loguru import logger
from token_manager import TokenManager

class SchwabAPI:
    def __init__(self, app_key, app_secret):
        self.token_manager = TokenManager(app_key, app_secret)
        logger.info("TokenManager 初始化成功")  # 加入此行來確認 TokenManager 被正確實例化
        self.base_url = "https://api.schwabapi.com/v1"

    def get_account_numbers(self):
        """獲取帳戶號碼和加密值"""
        access_token = self.token_manager.get_access_token()
        logger.info(f"使用的 access token: {access_token}")
        
        # 嘗試僅使用 Authorization 和 Content-Type
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/accounts/accountNumbers"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            account_numbers = response.json()
            logger.info("帳戶號碼和加密值獲取成功")
            return account_numbers
        else:
            # 詳細記錄錯誤訊息
            error_info = response.json().get("message", "Unknown error")
            error_details = response.json().get("errors", [])
            logger.error(f"獲取帳戶號碼失敗，狀態碼：{response.status_code}")
            logger.error(f"錯誤訊息: {error_info}")
            logger.error(f"錯誤細節: {error_details}")
            return None

    def get_account_balance_and_positions(self, account_number):
        """獲取指定帳戶的餘額和持倉資訊"""
        access_token = self.token_manager.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/accounts/{account_number}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            account_info = response.json()
            logger.info("帳戶餘額和持倉資訊獲取成功")
            return account_info
        else:
            logger.error(f"無法獲取帳戶 {account_number} 的詳情，狀態碼：{response.status_code}")
            return None
