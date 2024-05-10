import numpy as np
import pandas as pd
from statistics import mean
import talib
pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']
from arc.candle_processor import CandleProcessor
from entities.base import Signal
from candlestick import candlestick
from arc.signal_settings import config

s_patterns = ['hanging_man', 'bearish_harami', 'bullish_harami',
              'gravestone_doji', 'dark_cloud_cover', 'doji', 'doji_star', 'dragonfly_doji',
              'bearish_engulfing', 'bullish_engulfing', 'hammer', 'inverted_hammer', 'morning_star',
              'morning_star_doji', 'piercing_pattern', 'rain_drop', 'rain_drop_doji', 'star'
              'shooting_star']


class CandlePatternDetector(CandleProcessor):
    def __init__(self, spot_book, period, sliding_window=0):
        self.spot_book = spot_book
        self.last_match = None
        self.period = period
        self.last_match_dict = {}
        self.sliding_window = sliding_window
        self.candles = []

    def check_candle_patterns_talib(self):
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
            #df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
            df[pattern] = getattr(talib, pattern)(op, hi, lo, cl)
            #pass
            #print("*****", pattern, "=========", getattr(talib, pattern)(op, hi, lo, cl))
        return df

    def check_candle_patterns_cs(self):
        #print('test candle pattern')
        df = pd.DataFrame(self.candles[-7::])
        #print(df.tail(n=7))
        for pattern in s_patterns:
            try:
                df = getattr(candlestick, pattern)(df, target=pattern)
            except Exception as e:
                df[pattern] = False
        return df

    def on_new_candle(self, candle, notify):
        if len(self.candles) > 0:
            talib_pattern_df = self.check_candle_patterns_talib()
            cs_pattern_df = self.check_candle_patterns_cs()
            #print(pattern_df.T)
            for pattern in pattern_names:
                bullish_match_idx = np.where([talib_pattern_df[pattern] > 0])[1]
                bearish_match_idx = np.where([talib_pattern_df[pattern] < 0])[1]
                if len(bullish_match_idx) > 0:
                    pattern_id = (pattern, 'BUY')
                    pattern_pos = bullish_match_idx[-1]
                    if pattern_id not in self.last_match_dict.keys() or self.last_match_dict[pattern_id] != pattern_pos:
                        self.last_match_dict[pattern_id] = pattern_pos
                        if notify:
                            pat = Signal(asset=self.spot_book.asset, category='CANDLE_PATTERN', instrument=None,
                                         indicator=pattern + "_BUY",
                                         strength = talib_pattern_df[pattern][pattern_pos],
                                         signal_time=talib_pattern_df.timestamp[pattern_pos], notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                         signal_info={'open':talib_pattern_df.open[pattern_pos], 'high':talib_pattern_df.high[pattern_pos], 'low':talib_pattern_df.low[pattern_pos], 'close':talib_pattern_df.close[pattern_pos]},
                                         period=str(self.period) + "min")
                            self.spot_book.pattern_signal(pat)
                if len(bearish_match_idx) > 0:
                    pattern_id = (pattern, 'SELL')
                    pattern_pos = bearish_match_idx[-1]
                    if pattern_id not in self.last_match_dict.keys() or self.last_match_dict[pattern_id] != pattern_pos:
                        self.last_match_dict[pattern_id] = pattern_pos
                        if notify:
                            pat = Signal(asset=self.spot_book.asset, category='CANDLE_PATTERN', instrument=None,
                                         indicator=pattern + "_SELL",
                                         strength = talib_pattern_df[pattern][pattern_pos],
                                         signal_time=talib_pattern_df.timestamp[pattern_pos], notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                         signal_info={'open':talib_pattern_df.open[pattern_pos],'high':talib_pattern_df.high[pattern_pos], 'low':talib_pattern_df.low[pattern_pos], 'close':talib_pattern_df.close[pattern_pos]},
                                         period=str(self.period)+"min")
                            self.spot_book.pattern_signal(pat)
            for s_pattern in s_patterns:
                #print(cs_pattern_df[cs_pattern_df[s_pattern] == True]['timestamp'].to_list())
                match_ts = cs_pattern_df[cs_pattern_df[s_pattern] == True]['timestamp'].to_list()
                if len(match_ts) > 0:
                    pattern_time = match_ts[-1]
                    #print(pattern_time)
                    pattern_pos = np.where([cs_pattern_df['timestamp'] == pattern_time])[1]
                    if s_pattern not in self.last_match_dict.keys() or self.last_match_dict[s_pattern] != pattern_time:
                        self.last_match_dict[s_pattern] = pattern_time
                        if notify:
                            pat = Signal(asset=self.spot_book.asset, category='CANDLE_PATTERN', instrument=None,
                                         indicator=s_pattern,
                                         strength = 1,
                                         signal_time=cs_pattern_df.timestamp[pattern_pos], notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                         signal_info={'open':cs_pattern_df.open[pattern_pos], 'high':cs_pattern_df.high[pattern_pos], 'low':cs_pattern_df.low[pattern_pos], 'close':cs_pattern_df.close[pattern_pos]},
                                         period=str(self.period)+"min")
                            self.spot_book.pattern_signal(pat)
            if notify:
                last_candle = self.candles[-1]
                body = abs(last_candle['close'] - last_candle['open'])
                size = abs(last_candle['high'] - last_candle['low'])
                cd_body_pattern = 'CDL_BD_L' if body >= config[self.spot_book.asset]['CDL_BD_L'] else 'CDL_BD_S'
                cd_size_pattern = 'CDL_SZ_L' if size >= config[self.spot_book.asset]['CDL_SZ_L'] else 'CDL_SZ_S'
                cd_dir_pattern = 'CDL_DIR_P' if (last_candle['close'] - last_candle['open']) >= 0 else 'CDL_DIR_N'
                for cd_pattern in [cd_body_pattern, cd_size_pattern, cd_dir_pattern]:
                    pat = Signal(asset=self.spot_book.asset, category='CANDLE_PATTERN', instrument=None,
                                 indicator=cd_pattern,
                                 strength=1,
                                 signal_time=last_candle['timestamp'],
                                 notice_time=self.spot_book.spot_processor.last_tick['timestamp'],
                                 signal_info=last_candle,
                                 period=str(self.period)+"min")
                    self.spot_book.pattern_signal(pat)

    def evaluate(self, notify=True):
        self.create_candles(notify)


