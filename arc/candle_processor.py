import numpy as np
import pandas as pd
from statistics import mean
import talib
pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']

class CandleProcessor:
    def __init__(self, insight_book, period, sliding_window=0):
        self.insight_book = insight_book
        self.period = period
        self.sliding_window = sliding_window
        self.candles = []

    def create_candles(self, notify=True):
        #print('candle pattern evaluate')
        price_list = list(self.insight_book.spot_processor.spot_ts.values())[self.sliding_window::]
        #print(price_list[0]['timestamp'])
        chunks = [price_list[i:i + self.period] for i in range(0, len(price_list), self.period)]
        chunks = [x for x in chunks if len(x) == self.period]
        if len(chunks) > len(self.candles):
            self.candles = [{'timestamp':x[0]['timestamp'], 'open':x[0]['open'], 'high': max([y['high'] for y in x]), 'low':min([y['low'] for y in x]), 'close':x[-1]['close']} for x in chunks]
            self.on_new_candle(self.candles[-1], notify)

    def on_new_candle(self, candle, notify):
        pass

    def get_last_n_candles(self, n):
        return self.candles[-1*min(n, len(self.candles))::]
