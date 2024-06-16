from helper.utils import convert_to_candle


class CandleProcessor:
    def __init__(self, spot_book, period, sliding_window=0):
        self.spot_book = spot_book
        self.period = period
        self.sliding_window = sliding_window
        self.candles = []

    def create_candles(self, notify=True):
        price_list = list(self.spot_book.spot_processor.spot_ts.values())[self.sliding_window::]
        chunks = [price_list[i:i + self.period] for i in range(0, len(price_list), self.period)]
        chunks = [x for x in chunks if len(x) == self.period]
        if len(chunks) > len(self.candles):
            self.candles = [convert_to_candle(x) for x in chunks]
            self.on_new_candle(self.candles[-1], notify)

    def on_new_candle(self, candle, notify):
        pass

    def get_last_n_candles(self, n=1):
        return self.candles[-1*min(n, len(self.candles))::]

    def get_candle_count(self):
        return len(self.candles)
