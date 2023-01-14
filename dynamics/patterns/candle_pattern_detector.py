import numpy as np
import pandas as pd
from statistics import mean
import talib
pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']

class CandlePatternDetector:
    def __init__(self, insight_book, period, sliding_window=0):
        self.insight_book = insight_book
        self.last_match = None
        self.period = period
        self.last_match_dict = {}
        self.sliding_window = sliding_window
        self.candles = []

    def check_candle_patterns(self):
        #print('test candle pattern')
        df = pd.DataFrame(self.candles)
        #df.columns = ['open', 'high', 'low', 'close']
        #df = df.iloc[-5:, :]
        op = df['open']
        hi = df['high']
        lo = df['low']
        cl = df['close']
        for pattern in pattern_names:
            #print(pattern)
            #print(getattr(talib, pattern)(op, hi, lo, cl))
            # below is same as;
            # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
            df[pattern] = getattr(talib, pattern)(op, hi, lo, cl)
        return df

    def evaluate(self, notify=True):
        #print('candle pattern evaluate')
        price_list = list(self.insight_book.spot_processor.spot_ts.values())[self.sliding_window::]
        #print(price_list[0]['timestamp'])
        chunks = [price_list[i:i + self.period] for i in range(0, len(price_list), self.period)]
        chunks = [x for x in chunks if len(x) == self.period]
        self.candles = [{'timestamp':x[0]['timestamp'], 'open':x[0]['open'], 'high': max([y['high'] for y in x]), 'low':min([y['low'] for y in x]), 'close':x[-1]['close']} for x in chunks]

        if len(self.candles) > 0:
            pattern_df = self.check_candle_patterns()
            for pattern in pattern_names:
                bullish_match_idx = np.where([pattern_df[pattern] > 0])[1]
                bearish_match_idx = np.where([pattern_df[pattern] < 0])[1]
                if len(bullish_match_idx) > 0:
                    pattern_id = (pattern, 'BUY')
                    pattern_pos = bullish_match_idx[-1]
                    if pattern_id not in self.last_match_dict.keys() or self.last_match_dict[pattern_id] != pattern_pos:
                        self.last_match_dict[pattern_id] = pattern_pos
                        if notify:
                            self.insight_book.pattern_signal(pattern, {'time':pattern_df.timestamp[pattern_pos], 'candle':[pattern_df.open[pattern_pos],pattern_df.high[pattern_pos],pattern_df.low[pattern_pos], pattern_df.close[pattern_pos]], 'direction':'BUY', 'period': self.period, 'strength':pattern_df[pattern][pattern_pos]})
                        #print({'time':pattern_df.timestamp[pattern_pos], 'candle':[pattern_df.open[pattern_pos],pattern_df.high[pattern_pos],pattern_df.low[pattern_pos], pattern_df.close[pattern_pos]], 'direction':'BUY'})
                        #print(price_list)
                if len(bearish_match_idx) > 0:
                    pattern_id = (pattern, 'SELL')
                    pattern_pos = bearish_match_idx[-1]
                    if pattern_id not in self.last_match_dict.keys() or self.last_match_dict[pattern_id] != pattern_pos:
                        self.last_match_dict[pattern_id] = pattern_pos
                        if notify:
                            self.insight_book.pattern_signal(pattern, {'time':pattern_df.timestamp[pattern_pos], 'candle':[pattern_df.open[pattern_pos],pattern_df.high[pattern_pos],pattern_df.low[pattern_pos], pattern_df.close[pattern_pos]], 'direction':'SELL', 'period': self.period, 'strength':pattern_df[pattern][pattern_pos]})

