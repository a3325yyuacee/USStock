import requests
import unittest
from unittest.mock import patch

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

# 測試函數
class TestAccessToken(unittest.TestCase):

    @patch('requests.post')
    def test_get_access_token_success(self, mock_post):
        # 模擬成功的 API 回應
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'access_token': 'fake_token'}
        
        client_id = 'your_client_id'
        client_secret = 'your_client_secret'
        token = get_access_token(client_id, client_secret)
        
        self.assertEqual(token, 'fake_token')
    
    @patch('requests.post')
    def test_get_access_token_failure(self, mock_post):
        # 模擬失敗的 API 回應
        mock_post.return_value.status_code = 400
        
        client_id = 'your_client_id'
        client_secret = 'your_client_secret'
        token = get_access_token(client_id, client_secret)
        
        self.assertIsNone(token)

if __name__ == '__main__':
    unittest.main()
