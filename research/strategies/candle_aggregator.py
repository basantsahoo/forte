import numpy as np
from research.strategies.candle_pattern_strategy import CandlePatternStrategy
from helper.utils import get_exit_order_type
import talib
import pandas as pd
from itertools import compress
from dynamics.trend.candle_rank import candle_rankings
candle_names = talib.get_function_groups()['Pattern Recognition']

class CandleAggregator:
    def __init__(self, insight_book=None):
        self.id = 'CANDLE_AGGR'
        self.insight_book = insight_book
        self.is_aggregator = True
        self.individual_strategies = []
        #self.individual_strategies.append(CandlePatternStrategy(insight_book, 'CDLHANGINGMAN', "SELL", 10, 5))
        #self.individual_strategies.append(CandlePatternStrategy(insight_book, 'CDLHANGINGMAN', "SELL", 10, 15))
        for candle_pattern in candle_names:
            """
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 10, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 10, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 15, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 15, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 20, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 20, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 30, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 30, 5))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 10, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 10, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 15, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 15, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 20, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 20, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 30, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 30, 15))
            """
            """
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 30, 15))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 30, 15))
            """
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "BUY", 10, 5, min_tpo=1, max_tpo=1, triggers_per_signal=1))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, candle_pattern, "SELL", 10, 5, min_tpo=1, max_tpo=1, triggers_per_signal=1))

    def set_up(self):
        for strategy in self.individual_strategies:
            strategy.set_up()

    def relevant_signal(self):
        return True

    def process_signal(self, pattern, pattern_match_idx):
        if self.relevant_signal():
            for strategy in self.individual_strategies:
                #if strategy.price_pattern == pattern and strategy.order_type == pattern_match_idx['direction'] and strategy.period == pattern_match_idx['period']:
                strategy.process_signal(pattern, pattern_match_idx)

    def evaluate(self):
        for strategy in self.individual_strategies:
            strategy.evaluate()

    def get_signal_generator_from_id(self, strat_id):
        strategy_signal_generator = None
        for signal_generator in self.individual_strategies:
            if signal_generator.id == strat_id:
                strategy_signal_generator = signal_generator
                break
        return strategy_signal_generator



