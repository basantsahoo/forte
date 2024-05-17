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


class DailyCandlePatternDetector:
    def __init__(self, spot_book, period="daily"):
        self.last_match = None
        self.period = period
        self.last_match_dict = {}
        self.candles = []
        self.asset = spot_book.asset
        self.signal_dict = {}

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

    def detect(self):
        if len(self.candles) > 0:
            talib_pattern_df = self.check_candle_patterns_talib()
            cs_pattern_df = self.check_candle_patterns_cs()
            #print(pattern_df.T)
            for pattern in pattern_names:
                latest_idx = talib_pattern_df[pattern].to_list()[-1]
                if latest_idx:
                    if latest_idx > 0:
                        pattern_id = pattern + '_BUY'
                    else:
                        pattern_id = pattern + '_SELL'
                    signal = Signal(asset=self.asset, category='CANDLE_PATTERN', instrument=None,
                                 indicator=pattern_id,
                                 strength = latest_idx,
                                 signal_time=talib_pattern_df.timestamp[-1], notice_time=talib_pattern_df.timestamp[-1],
                                 signal_info={'open':talib_pattern_df.open[-1], 'high':talib_pattern_df.high[-1], 'low':talib_pattern_df.low[-1], 'close':talib_pattern_df.close[-1]},
                                 period=self.period)
                    self.signal_dict[(signal.category, signal.indicator, signal.period)] = signal
            for s_pattern in s_patterns:
                #print(cs_pattern_df[cs_pattern_df[s_pattern] == True]['timestamp'].to_list())
                latest_idx = cs_pattern_df[s_pattern].to_list()[-1]
                if latest_idx:
                    signal = Signal(asset=self.spot_book.asset, category='CANDLE_PATTERN', instrument=None,
                                 indicator=s_pattern,
                                 strength = 1,
                                 signal_time=cs_pattern_df.timestamp[-1], notice_time=cs_pattern_df.timestamp[-1],
                                 signal_info={'open':cs_pattern_df.open[-1], 'high':cs_pattern_df.high[-1], 'low':cs_pattern_df.low[-1], 'close':cs_pattern_df.close[-1]},
                                 period=self.period)
                    self.signal_dict[(signal.category, signal.indicator, signal.period)] = signal
            last_candle = self.candles[-1]
            body = abs(last_candle['close'] - last_candle['open'])
            size = abs(last_candle['high'] - last_candle['low'])
            cd_body_pattern = 'CDL_BD_L' if body >= config[self.asset]['CDL_BD_L'] else 'CDL_BD_S'
            cd_size_pattern = 'CDL_SZ_L' if size >= config[self.asset]['CDL_SZ_L'] else 'CDL_SZ_S'
            cd_dir_pattern = 'CDL_DIR_P' if (last_candle['close'] - last_candle['open']) >= 0 else 'CDL_DIR_N'
            for cd_pattern in [cd_body_pattern, cd_size_pattern, cd_dir_pattern]:
                signal = Signal(asset=self.asset, category='CANDLE_PATTERN', instrument=None,
                             indicator=cd_pattern,
                             strength=1,
                             signal_time=last_candle['timestamp'],
                             notice_time=last_candle['timestamp'],
                             signal_info=last_candle,
                             period=self.period)
                self.signal_dict[(signal.category, signal.indicator, signal.period)] = signal



