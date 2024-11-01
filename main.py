from schwab_api import SchwabAPI
from loguru import logger

def main():
    # 初始化 OAuth 認證，填入您的 app_key 和 app_secret
    app_key = "eTOdlULAGAECJta6idElCFNAnpomwdFt"
    app_secret = "6pEuGP4RMdMI8R4R"
    api_client = SchwabAPI(app_key, app_secret)
    
    # 獲取帳戶號碼列表
    account_numbers = api_client.get_account_numbers()
    if account_numbers:
        logger.info(f"帳戶列表: {account_numbers}")

        # 獲取第一個帳戶的餘額和持倉資訊
        encrypted_account_number = account_numbers[0].get("encryptedAccountNumber")
        account_info = api_client.get_account_balance_and_positions(encrypted_account_number)
        logger.info(f"查詢到的帳戶資訊: {account_info}")
    else:
        logger.error("無法獲取帳戶號碼列表")

if __name__ == "__main__":
    main()
