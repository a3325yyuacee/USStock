import requests
import pandas as pd
import os
import yfinance as yf  # 使用 Yahoo Finance
from dotenv import load_dotenv
from datetime import timedelta

# 載入環境變數
load_dotenv()

# Constants
INITIAL_CASH = 2000
BUY_AMOUNT = 200
STOP_LOSS = 200  # 固定止損值

# '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
def fetch_historical_data(symbol, period='5y'):
    """
    使用 Yahoo Finance 獲取過去 n 年歷史數據
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

def calculate_annualized_return(initial_cash, final_cash, start_date, end_date):
    """
    計算年化報酬率
    """
    # 計算投資期間的年數
    duration_years = (end_date - start_date).days / 365.0
    if duration_years == 0:  # 防止除以零
        return 0
    # 計算年化報酬率
    annualized_return = ((final_cash / initial_cash) ** (1 / duration_years)) - 1
    return annualized_return * 100  # 返回百分比

def backtest_strategy(data):
    """
    按照策略邏輯進行回測
    """
    cash = INITIAL_CASH  # 初始現金
    holdings = 0  # 初始持倉
    entry_price = 0  # 初始買入價
    total_invested = 0  # 累積投入本金
    stop_loss_price = None  # 初始止損價
    trades = []

    for date, row in data.iterrows():
        current_price = float(row['Close'])  # 確保 current_price 是數值

        # 初始買入條件
        if holdings == 0 and cash >= BUY_AMOUNT:
            shares_to_buy = BUY_AMOUNT / current_price
            cash -= BUY_AMOUNT
            holdings += shares_to_buy
            entry_price = current_price
            total_invested += BUY_AMOUNT  # 更新累積投入本金
            stop_loss_price = entry_price - (STOP_LOSS / holdings)
            trades.append({'Date': date, 'Type': 'Buy', 'Price': current_price, 'Holdings': holdings})
            print(f"[{date}] 初始買入: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}, 投入本金 {total_invested:.2f}")
            continue  # 跳過後續檢查，進行下一天

        # 移動止損檢查
        if holdings > 0 and stop_loss_price and current_price <= stop_loss_price:
            # 平倉
            cash += holdings * current_price
            profit_loss = cash - total_invested  # 計算當前的損益
            total_invested = 0  # 平倉後，累積投入本金歸零
            print(f"[{date}] 平倉: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}, 損益 {profit_loss:.2f}")
            trades.append({'Date': date, 'Type': 'Sell', 'Price': current_price, 'Holdings': holdings})
            holdings = 0
            stop_loss_price = None

        # 檢查是否可以加碼
        if cash >= BUY_AMOUNT:
            # 調整目標價邏輯
            target_price = entry_price * 1.05 if entry_price > 0 else current_price * 1.05
            
            if current_price >= target_price:
                shares_to_buy = BUY_AMOUNT / current_price
                cash -= BUY_AMOUNT
                holdings += shares_to_buy
                total_invested += BUY_AMOUNT  # 更新累積投入本金
                entry_price = current_price
                stop_loss_price = entry_price - (STOP_LOSS / holdings)
                print(f"[{date}] 加碼買入: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}, 投入本金 {total_invested:.2f}")
                trades.append({'Date': date, 'Type': 'Buy', 'Price': current_price, 'Holdings': holdings})

    # 最終平倉
    if holdings > 0:
        cash += holdings * current_price
        profit_loss = cash - total_invested  # 計算當前的損益
        print(f"[最後] 平倉: 價格 {current_price:.2f}, 持倉 {holdings:.2f}, 現金 {cash:.2f}, 總損益 {profit_loss:.2f}")
        trades.append({'Date': date, 'Type': 'Sell', 'Price': current_price, 'Holdings': holdings})
        holdings = 0
    
    return trades, cash


if __name__ == "__main__":
    # 載入數據
    symbol = "TSLL"
    data = fetch_historical_data(symbol)
    print("Successfully loaded historical data")

    # 回測策略
    trades, final_cash = backtest_strategy(data)

    # 計算投資期間
    start_date = data.index.min()
    end_date = data.index.max()

    # 計算年化報酬率
    annualized_return = calculate_annualized_return(INITIAL_CASH, final_cash, start_date, end_date)
    
    # 輸出結果
    print(f"Final cash balance: ${final_cash:.2f}")
    print(f"總報酬率: {((final_cash - INITIAL_CASH) / INITIAL_CASH) * 100:.2f}%")
    print(f"年化報酬率: {annualized_return:.2f}%")
    print("Backtest completed.")
