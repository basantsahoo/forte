import numpy as np
from research.strategies import BaseStrategy
from research.strategies.candle_pattern_strategy import CandlePatternStrategy
from helper.utils import get_exit_order_type
import talib
import pandas as pd
from itertools import compress
from trend.candle_rank import candle_rankings
candle_names = talib.get_function_groups()['Pattern Recognition']

class CandleAggregator(BaseStrategy):
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None, record_metric=False):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = 'CANDLE_AGGR'
        self.pattern_df_5 = None
        self.pattern_df_15 = None
        self.is_aggregator = True
        self.individual_strategies = []
        for candle_pattern in candle_names:
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 10, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 10, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 15, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 15, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 20, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 20, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 30, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 30, 5))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 10, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 10, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 15, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 15, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 20, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 20, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "BUY", 30, 15))
            self.individual_strategies.append(CandlePatternStrategy(self, candle_pattern, "SELL", 30, 15))
    def evaluate(self):
        price_list = list(self.insight_book.market_data.values())
        chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
        chunks_15 = [x for x in chunks_15 if len(x) == 15]
        chunks_15_ohlc = [[x[0]['open'], max([y['high'] for y in x]), min([y['low'] for y in x]), x[-1]['close']] for x in chunks_15]
        chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
        chunks_5 = [x for x in chunks_5 if len(x) == 5]
        chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]
        if len(chunks_5_ohlc) > 0:
            self.check_candle_patterns(chunks_5_ohlc, 5)
        if len(chunks_15_ohlc) > 0:
            self.check_candle_patterns(chunks_15_ohlc, 15)

        for strategy in self.individual_strategies:
            strategy.evaluate()

    def check_candle_patterns(self,chunks_ohlc,period):
        #print('test candle pattern')
        df = pd.DataFrame(chunks_ohlc)
        df.columns = ['open', 'high', 'low', 'close']
        df = df.iloc[-5:, :]
        op = df['open']
        hi = df['high']
        lo = df['low']
        cl = df['close']
        for candle in candle_names:
            # below is same as;
            # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
            df[candle] = getattr(talib, candle)(op, hi, lo, cl)
        if period == 5:
            self.pattern_df_5 = df
        elif period == 15:
            self.pattern_df_15 = df

    def get_signal_generator_from_id(self, strat_id):
        strategy_signal_generator = None
        for signal_generator in self.individual_strategies:
            if signal_generator.id == strat_id:
                strategy_signal_generator = signal_generator
                break
        return strategy_signal_generator

    def get_pattern_df(self, period):
        pattern_df = None
        if period == 5:
            pattern_df = self.pattern_df_5
        elif period == 15:
            pattern_df = self.pattern_df_15
        return pattern_df




