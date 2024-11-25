# testMain.py

import pandas as pd
from testUtils import backtest_strategy

# 載入歷史數據 (假設 CSV 文件包含一列名為 'price' 的歷史價格)
data = pd.read_csv("historical_btc_data.csv")

# 回測參數
initial_capital = 1500
num_positions = 30  # 每筆倉位 50 USDT

# 開始回測
total_profit = backtest_strategy(data, initial_capital, num_positions)
print(f"策略回測的總利潤：{total_profit:.2f} USDT")
