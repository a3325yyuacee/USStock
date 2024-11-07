import os
import base64
import requests
import json
from loguru import logger

import json
from schwab_oauth import SchwabOAuth
from loguru import logger

def obtain_new_tokens():
    # 初始化 OAuth 客戶端
    app_key = "eTOdlULAGAECJta6idElCFNAnpomwdFt"  # 替換為您的 app_key
    app_secret = "6pEuGP4RMdMI8R4R"  # 替換為您的 app_secret
    oauth_client = SchwabOAuth(app_key, app_secret)

    # 步驟 1: 生成並打開認證 URL
    oauth_client.construct_auth_url()

    # 步驟 2: 授權完成後，將瀏覽器返回的 URL 輸入
    returned_url = input("請將瀏覽器返回的 URL 粘貼到這裡: ")

    # 步驟 3: 提取授權碼
    response_code = oauth_client.extract_code_from_url(returned_url)

    # 步驟 4: 生成 headers 和 payload
    headers, payload = oauth_client.get_token_headers_and_payload(response_code)

    # 步驟 5: 使用授權碼交換新的 access token 和 refresh token
    tokens = oauth_client.retrieve_tokens(headers, payload)
    if tokens:
        logger.info(f"成功獲取新的 access token 和 refresh token: {tokens}")
        
        # 將新的令牌保存到 tokens.json 文件
        with open("tokens.json", "w") as f:
            json.dump(tokens, f)
        logger.info("新令牌已成功保存到 tokens.json")
    else:
        logger.error("無法獲取新令牌")

if __name__ == "__main__":
    obtain_new_tokens()

