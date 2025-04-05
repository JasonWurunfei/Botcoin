import yfinance as yf
import json
from botcoin.strategies.dip_buyer import DipBuyerStrategy

if __name__ == "__main__":
    #Fetch ticker information
    ticker = yf.Ticker('AAPL')
    print(ticker.info['longName'])

    #Fetch 5 years of daily candles
    candles = ticker.history(period="5y", interval="1d")
    prices = candles[["Open", "High", "Low", "Close"]]  
    strategy = DipBuyerStrategy(threshold=3, trade_amount=0.25)

    #Replay the strategy on the historical data
    bal, records = strategy.history_replay(prices)
    print(f"Final balance: {bal}")
    print(f"Trade records: ")
    print(json.dumps(records, indent=4))
