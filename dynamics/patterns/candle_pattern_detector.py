import numpy as np
import pandas as pd
from statistics import mean
import talib
pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']
from arc.candle_processor import CandleProcessor
from entities.base import Signal

class CandlePatternDetector(CandleProcessor):
    def __init__(self, spot_book, period, sliding_window=0):
        self.spot_book = spot_book
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

    def on_new_candle(self, candle, notify):
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
                            pat = Signal(asset=self.spot_book.asset, category='CANDLE_'+str(self.period), instrument="",
                                         indicator=pattern + "_BUY",
                                         signal= 1,
                                         strength = pattern_df[pattern][pattern_pos],
                                         signal_time=pattern_df.timestamp[pattern_pos], notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                         info={'candle':[pattern_df.open[pattern_pos],pattern_df.high[pattern_pos],pattern_df.low[pattern_pos], pattern_df.close[pattern_pos]]})
                            self.spot_book.pattern_signal(pat)
                if len(bearish_match_idx) > 0:
                    pattern_id = (pattern, 'SELL')
                    pattern_pos = bearish_match_idx[-1]
                    if pattern_id not in self.last_match_dict.keys() or self.last_match_dict[pattern_id] != pattern_pos:
                        self.last_match_dict[pattern_id] = pattern_pos
                        if notify:
                            pat = Signal(asset=self.spot_book.asset, category='CANDLE_'+str(self.period), instrument="",
                                         indicator=pattern + "_SELL",
                                         signal= 1,
                                         strength = pattern_df[pattern][pattern_pos],
                                         signal_time=pattern_df.timestamp[pattern_pos], notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                         info={'candle':[pattern_df.open[pattern_pos],pattern_df.high[pattern_pos], pattern_df.low[pattern_pos], pattern_df.close[pattern_pos]]})
                            self.spot_book.pattern_signal(pat)

    def evaluate(self, notify=True):
        self.create_candles(notify)


