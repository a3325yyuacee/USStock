from utils import fetch_current_price, initialize_strategy, check_buy_conditions, check_stop_loss, place_order
import time

# 初始參數
initial_capital = 1500
num_positions = 30 #每一筆 50 USDT
symbol = 'BTCUSDT'

strategy = initialize_strategy(initial_capital, num_positions)

while True:
    current_price = fetch_current_price(symbol)
    print(f"當前價格: {current_price}")

    if check_stop_loss(strategy, current_price):
        print("觸發動態停損，清倉結束。")
        break

    if check_buy_conditions(strategy, current_price):
        print(f"價格 {current_price} 達到加倉條件，加倉。")
        place_order(symbol, 'BUY', strategy['position_size'], current_price)

    time.sleep(5)  # 每5秒檢查一次