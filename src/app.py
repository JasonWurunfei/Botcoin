import yfinance as yf
import json
from botcoin.strategies.dip_buyer import DipBuyerStrategy

if __name__ == "__main__":
    # Initialize the strategy
    strategy = DipBuyerStrategy(threshold=3, trade_amount=0.25, stop_gain=0.012)

    # Define the watchlist of tickers
    watchlist = [
        'AAPL',
        'MSFT',
        'AMZN',
        'GOOGL',
        'TSLA',
        'META',
        'NFLX',
        'NVDA',
        'AMD',
        'INTC'
    ]

    all_trades = []

    # Loop through each ticker in the watchlist
    for ticker in watchlist:
        # Fetch ticker information
        ticker_info = yf.Ticker(ticker)

        # Fetch 2 years of daily candles
        candles = ticker_info.history(period="2y", interval="1d")
        prices = candles[["Open", "High", "Low", "Close"]]

        # Replay the strategy on the historical data
        trades = strategy.get_history_tradeable_records(prices)
        all_trades.extend(trades)
    
    
    all_trades.sort(key=lambda x: x['date'])
    bal, records, win_rate = strategy.history_replay(all_trades)
    print(f"Final balance: {bal}, win rate: {win_rate} of {len(records)} trades")
