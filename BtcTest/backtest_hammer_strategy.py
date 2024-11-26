# import pandas as pd
# from binance.client import Client

# # 初始化 Binance 客戶端
# api_key = "test"
# api_secret = "test"
# client = Client(api_key, api_secret)

# # 獲取歷史 K 線數據
# def fetch_binance_data(symbol='BTCUSDT', interval='15m', start_date='1 Jan 2023', end_date='31 Dec 2023'):
#     klines = client.get_historical_klines(
#         symbol=symbol,
#         interval=interval,
#         start_str=start_date,
#         end_str=end_date
#     )

#     # 將數據轉換為 DataFrame
#     data = pd.DataFrame(klines, columns=[
#         'timestamp', 'open', 'high', 'low', 'close', 'volume',
#         'close_time', 'quote_asset_volume', 'number_of_trades',
#         'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
#     ])
#     # 格式化數據
#     data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms')
#     data['open'] = data['open'].astype(float)
#     data['high'] = data['high'].astype(float)
#     data['low'] = data['low'].astype(float)
#     data['close'] = data['close'].astype(float)
#     data['volume'] = data['volume'].astype(float)
#     return data[['datetime', 'open', 'high', 'low', 'close', 'volume']]

# # 初始化策略
# def initialize_strategy(capital, num_positions):
#     position_size = capital / num_positions  # 固定每筆下單金額
#     return {
#         'capital': capital,
#         'position_size': position_size,
#         'positions': [],
#         'btc_quantity': 0,
#         'stop_loss_price': None,
#         'initial_stop_loss_pct': 0.5,
#         'target_gain_pct': 0.05,
#         'num_positions': num_positions,
#         'prices': [],  # 用於計算移動平均線
#         'trade_log': []  # 記錄交易日誌
#     }

# # 更新移動平均線作為動態停損價格
# def update_moving_average(strategy, window=10):
#     if len(strategy['prices']) >= window:
#         moving_average = sum(strategy['prices'][-window:]) / window
#         strategy['stop_loss_price'] = moving_average

# # 檢查是否符合加倉條件
# def check_buy_conditions(strategy, current_price):
#     if len(strategy['positions']) < strategy['num_positions'] and \
#        (len(strategy['positions']) == 0 or current_price >= strategy['positions'][-1][0] * (1 + strategy['target_gain_pct'])):
#         strategy['positions'].append((current_price, strategy['position_size']))
#         strategy['btc_quantity'] += strategy['position_size'] / current_price
#         strategy['prices'].append(current_price)
#         update_moving_average(strategy)
#         return True
#     return False

# # 檢查是否觸發動態停損
# def check_stop_loss(strategy, current_price):
#     if current_price <= (strategy['stop_loss_price'] or 0):
#         strategy['capital'] = strategy['btc_quantity'] * current_price
#         strategy['trade_log'].append({
#             'action': 'STOP_LOSS',
#             'price': current_price,
#             'capital': strategy['capital']
#         })
#         strategy['positions'].clear()
#         strategy['btc_quantity'] = 0
#         strategy['stop_loss_price'] = None
#         strategy['prices'] = []
#         return True
#     return False

# # 回測邏輯
# def backtest_strategy(data, initial_capital=1500, num_positions=30):
#     strategy = initialize_strategy(initial_capital, num_positions)

#     for i, row in data.iterrows():
#         current_price = row['close']

#         # 檢查是否觸發動態停損
#         if check_stop_loss(strategy, current_price):
#             break

#         # 檢查是否符合加倉條件
#         if check_buy_conditions(strategy, current_price):
#             strategy['trade_log'].append({
#                 'action': 'BUY',
#                 'price': current_price,
#                 'btc_quantity': strategy['btc_quantity'],
#                 'position_size': strategy['position_size']  # 每次固定下單金額
#             })

#     # 最終資金計算
#     final_capital = strategy['capital'] + strategy['btc_quantity'] * data.iloc[-1]['close']
#     strategy['trade_log'].append({
#         'action': 'FINAL',
#         'price': data.iloc[-1]['close'],
#         'capital': final_capital
#     })
#     return strategy

# # 獲取數據並回測
# data = fetch_binance_data()
# result = backtest_strategy(data)

# # 顯示結果
# print("最終資金餘額:", result['capital'])
# print("交易日誌:")
# for log in result['trade_log']:
#     print(log)
