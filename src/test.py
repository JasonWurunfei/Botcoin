from botcoin.data.data_fetcher import PriceTicker

if __name__ == "__main__":
    # websocket.enableTrace(True)
    pt = PriceTicker(tickers=["MSTR"])
    pt.tick()