import requests
import pandas as pd
from binance.client import Client
from binance.enums import *
import math

# 初始化幣安客戶端
api_key = 'test'
api_secret = 'test'
client = Client(api_key, api_secret)

def fetch_current_price(symbol='BTCUSDT'):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def initialize_strategy(capital, num_positions):
    position_size = capital / num_positions
    return {
        'capital': capital,
        'position_size': position_size,
        'positions': [],
        'btc_quantity': 0,
        'stop_loss_price': None,
        'initial_stop_loss_pct': 0.5,
        'target_gain_pct': 0.05,
        'num_positions': num_positions,
        'prices': []  # 用於存儲價格，計算移動平均線
    }

def update_moving_average(strategy, window=10):
    if len(strategy['prices']) >= window:
        # 計算最近window期的移動平均線
        moving_average = sum(strategy['prices'][-window:]) / window
        strategy['stop_loss_price'] = moving_average
        print(f"更新停損價格為移動平均線: {moving_average}")

def check_buy_conditions(strategy, current_price):
    if len(strategy['positions']) < strategy['num_positions'] and \
       (len(strategy['positions']) == 0 or current_price >= strategy['positions'][-1][0] * (1 + strategy['target_gain_pct'])):
        strategy['positions'].append((current_price, strategy['position_size']))
        strategy['btc_quantity'] += strategy['position_size'] / current_price
        strategy['prices'].append(current_price)  # 加入當前價格，用於計算移動平均線
        update_moving_average(strategy)  # 每次加倉後更新停損價格
        return True
    return False

def check_stop_loss(strategy, current_price):
    if current_price <= (strategy['stop_loss_price'] or 0):
        strategy['capital'] = strategy['btc_quantity'] * current_price
        strategy['positions'].clear()
        strategy['btc_quantity'] = 0
        strategy['stop_loss_price'] = None
        strategy['prices'] = []  # 清空價格記錄
        return True
    return False

def place_order(symbol, side, usdt_amount, price):
    quantity = usdt_amount / price
    symbol_info = client.get_symbol_info(symbol)
    step_size = float(next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')['stepSize'])
    precision = int(round(-math.log(step_size, 10), 0))
    quantity = round(quantity, precision)

    try:
        order = client.create_order(
            symbol=symbol,
            side=SIDE_BUY if side == 'BUY' else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"真實下單成功！訂單詳情：{order}")
        return order
    except Exception as e:
        print(f"下單失敗：{e}")
        return None