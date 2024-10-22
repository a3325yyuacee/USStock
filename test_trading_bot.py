import unittest
from unittest.mock import patch
from trading_bot import get_access_token, place_order

# 測試函數
class TestTrading(unittest.TestCase):
    @patch('requests.post')
    def test_get_access_token_success(self, mock_post):
        # 模擬成功的API回應
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'access_token': 'fake_token'}

        token = get_access_token('fake_client_id', 'fake_client_secret')
        self.assertEqual(token, 'fake_token')

    @patch('requests.post')
    def test_get_access_token_failure(self, mock_post):
        # 模擬失敗的API回應
        mock_post.return_value.status_code = 400

        token = get_access_token('fake_client_id', 'fake_client_secret')
        self.assertIsNone(token)

class TestOrder(unittest.TestCase):
    @patch('requests.post')
    def test_place_order_success(self, mock_post):
        # 模擬成功的API回應
        mock_post.return_value.status_code = 201

        access_token = 'fake_access_token'
        account_number = 'fake_account_number'
        order_data = {'symbol': 'AAPL', 'quantity': 10}
        
        success = place_order(access_token, account_number, order_data)
        self.assertTrue(success)

    @patch('requests.post')
    def test_place_order_failure(self, mock_post):
        # 模擬失敗的API回應
        mock_post.return_value.status_code = 400

        access_token = 'fake_access_token'
        account_number = 'fake_account_number'
        order_data = {'symbol': 'AAPL', 'quantity': 10}
        
        success = place_order(access_token, account_number, order_data)
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
