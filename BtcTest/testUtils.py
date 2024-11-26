
# import pandas as pd
# from testUtils import initialize_strategy, check_buy_conditions, check_stop_loss

# def backtest_strategy(data, initial_capital, num_positions, symbol='BTCUSDT'):
#     """
#     回測策略，使用歷史價格數據進行模擬交易。
    
#     :param data: DataFrame，包含歷史價格數據，必須有 'price' 列
#     :param initial_capital: 初始資本
#     :param num_positions: 加倉次數
#     :return: 策略總利潤
#     """
#     strategy = initialize_strategy(initial_capital, num_positions)
#     total_profit = 0

#     for index, row in data.iterrows():
#         current_price = row['price']

#         if check_stop_loss(strategy, current_price):
#             profit = strategy['capital'] - initial_capital
#             print(f"觸發停損，清倉: 價格 {current_price}, 獲利 {profit:.2f} USDT")
#             total_profit += profit
#             strategy = initialize_strategy(initial_capital, num_positions)  # 重置策略

#         if check_buy_conditions(strategy, current_price):
#             print(f"加倉: 價格 {current_price}, 總持倉 {strategy['btc_quantity']:.4f} BTC")
    
#     return total_profit
