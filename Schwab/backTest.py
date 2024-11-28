import requests
import pandas as pd
import os
import matplotlib.pyplot as plt
import yfinance as yf  # 使用 Yahoo Finance
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from matplotlib import rcParams


# 載入環境變數
load_dotenv()

# Constants
INITIAL_CASH = 5000
BUY_AMOUNT = 500
STOP_LOSS = 500  # 固定止損值

def fetch_historical_data(symbol, period='1y'):
    """
    使用 Yahoo Finance 獲取過去一年歷史數據
    """
    try:
        df = yf.download(symbol, period=period, interval='1d')
        df.reset_index(inplace=True)
        df.rename(columns={
            'Date': 'Date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        }, inplace=True)
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        raise ValueError(f"無法獲取 {symbol} 的歷史數據: {e}")

def backtest_strategy(data):
    """
    按照策略邏輯進行回測
    """
    cash = INITIAL_CASH
    holdings = 0
    entry_price = 0
    stop_loss_price = None
    trades = []
    
    for date, row in data.iterrows():
        current_price = float(row['Close'])  # 確保 current_price 是數值

        # 初始買入條件
        if holdings == 0 and cash >= BUY_AMOUNT:
            shares_to_buy = BUY_AMOUNT / current_price
            cash -= BUY_AMOUNT
            holdings += shares_to_buy
            entry_price = current_price
            stop_loss_price = entry_price - (STOP_LOSS / holdings)
            trades.append({'Date': date, 'Type': 'Buy', 'Price': current_price, 'Holdings': holdings})
            print(f"[{date}] 初始買入: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}")
            continue  # 跳過後續檢查，進行下一天

        # 移動止損檢查
        if holdings > 0 and stop_loss_price and current_price <= stop_loss_price:
            # 平倉
            cash += holdings * current_price
            print(f"[{date}] 平倉: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}")
            trades.append({'Date': date, 'Type': 'Sell', 'Price': current_price, 'Holdings': holdings})
            holdings = 0
            stop_loss_price = None

        # 檢查是否可以買入
        if cash >= BUY_AMOUNT:
            # 調整目標價邏輯
            target_price = entry_price * 1.02 if entry_price > 0 else current_price * 1.02
            
            if current_price >= target_price:
                shares_to_buy = BUY_AMOUNT / current_price
                cash -= BUY_AMOUNT
                holdings += shares_to_buy
                entry_price = current_price
                stop_loss_price = entry_price - (STOP_LOSS / holdings)
                print(f"[{date}] 買入: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}")
                trades.append({'Date': date, 'Type': 'Buy', 'Price': current_price, 'Holdings': holdings})

    # 最終平倉
    if holdings > 0:
        cash += holdings * current_price
        print(f"[最後] 平倉: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}")
        trades.append({'Date': date, 'Type': 'Sell', 'Price': current_price, 'Holdings': holdings})
        holdings = 0
    
    return trades, cash



def plot_trades(data, trades):
    """
    繪製回測結果和交易點
    """
    plt.figure(figsize=(12, 6))
    plt.plot(data['Close'], label='Close Price', alpha=0.7)
    
    for trade in trades:
        if trade['Type'] == 'Buy':
            plt.scatter(trade['Date'], trade['Price'], color='green', label='Buy', alpha=0.6)
        elif trade['Type'] == 'Sell':
            plt.scatter(trade['Date'], trade['Price'], color='red', label='Sell', alpha=0.6)

    plt.title("回測交易點與股價")
    plt.xlabel("日期")
    plt.ylabel("價格")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    # 載入數據
    symbol = "TSLA"
    data = fetch_historical_data(symbol)
    print("Successfully loaded historical data")

    # 回測策略
    trades, final_cash = backtest_strategy(data)
    
    # 輸出最終現金餘額
    print(f"Final cash balance: ${final_cash:.2f}")
    
    # 計算總收益率
    total_return = ((final_cash - INITIAL_CASH) / INITIAL_CASH) * 100
    print(f"Total return: {total_return:.2f}%")

    # 繪製交易結果
    plot_trades(data, trades)

    print("Backtest completed.")

