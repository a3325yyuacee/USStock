import requests
import json


def get_account_positions(base_url, headers):
    """
    查詢帳戶資訊及持倉，並以簡化方式顯示
    """
    params = {'fields': 'positions'}
    response = requests.get(f'{base_url}/accounts', headers=headers, params=params)

    if response.status_code == 200:
        accounts_data = response.json()
        print("帳戶及持倉資訊如下：")
        
        # 避免重複列印
        unique_accounts = set()

        for account in accounts_data:
            # 提取帳戶資訊
            account_info = account.get('securitiesAccount', {})
            account_number = account_info.get('accountNumber', '未知帳號')
            cash_balance = account_info.get('currentBalances', {}).get('cashBalance', 0.0)

            # 如果該帳戶已經處理過，跳過
            if account_number in unique_accounts:
                continue
            unique_accounts.add(account_number)

            # 打印帳戶現金餘額
            print(f"\n帳號: {account_number}")
            print(f"現金餘額: ${cash_balance:,.2f}")

            # 提取並顯示持倉資訊
            positions = account_info.get('positions', [])
            if positions:
                print("持倉：")
                for position in positions:
                    symbol = position['instrument'].get('symbol', '未知股票')
                    quantity = position.get('longQuantity', 0.0)
                    market_value = position.get('marketValue', 0.0)
                    print(f"  股票代號: {symbol}，持股數量: {quantity}，市值: ${market_value:,.2f}")
            else:
                print("  此帳戶無持倉。")
    else:
        print("查詢帳戶及持倉失敗")
        print(f"錯誤代碼: {response.status_code}")
        print(response.text)
        exit(1)


if __name__ == "__main__":
    # 從 tokens.json 中讀取 access_token
    with open("tokens.json", "r") as f:
        tokens = json.load(f)

    access_token = tokens['access_token']
    base_url = "https://api.schwabapi.com/trader/v1/"
    headers = {'Authorization': f'Bearer {access_token}'}

    get_account_positions(base_url, headers)
