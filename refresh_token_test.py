import os
import base64
import requests
import json
from loguru import logger

def refresh_tokens():
    logger.info("Initializing...")

    # 替換為您的 app_key 和 app_secret
    app_key = "eTOdlULAGAECJta6idElCFNAnpomwdFt"
    app_secret = "6pEuGP4RMdMI8R4R"
    refresh_token_value = "DJARdigK0fpuzsBM5tVbZ-v6uppuymfvUh6B2shaG6L0CX0pebNS20DwQx8gHXQj9I-3aHIno0AvaMFnDA17Ffmf-nlv6WX833QGVyc3VvsZA-_e4lYFlhdyxoqe411UriZkqLVbvS8@"

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
    }
    headers = {
        "Authorization": f'Basic {base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()}',
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # 發送請求刷新 token
    refresh_token_response = requests.post(
        url="https://api.schwabapi.com/v1/oauth/token",
        headers=headers,
        data=payload,
    )
    if refresh_token_response.status_code == 200:
        logger.info("使用 refresh token 成功獲取新令牌")
        refresh_token_dict = refresh_token_response.json()
        logger.debug(refresh_token_dict)

        # 將新的令牌保存到 tokens.json 文件中
        with open("tokens.json", "w") as token_file:
            json.dump(refresh_token_dict, token_file)
        logger.info("新令牌已成功保存到 tokens.json")

    else:
        logger.error(
            f"刷新 access token 失敗: {refresh_token_response.text}"
        )

if __name__ == "__main__":
    refresh_tokens()
