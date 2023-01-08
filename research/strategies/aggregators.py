import numpy as np
from research.strategies.candle_pattern_strategy import CandlePatternStrategy
from research.strategies.double_top_strategy import DoubleTopStrategy
from research.strategies.double_top_break_strategy import DoubleTopBreakStrategy
from research.strategies.trend_strategy import TrendStrategy

from helper.utils import get_exit_order_type
import talib
import pandas as pd
from itertools import compress
from dynamics.trend.candle_rank import candle_rankings
candle_names = talib.get_function_groups()['Pattern Recognition']


class StrategyAggregator:
    def __init__(self, insight_book=None):
        self.id = 'AGGR'
        self.insight_book = insight_book
        self.is_aggregator = True
        self.individual_strategies = []

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


class CandleAggregator(StrategyAggregator):
    def __init__(self, insight_book=None):
        super().__init__(insight_book)
        self.id = "CANDLE_AGGR"
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
            self.individual_strategies.append(CandlePatternStrategy(insight_book, None, candle_pattern, "BUY", 10, 5, min_tpo=1, max_tpo=1, triggers_per_signal=1))
            self.individual_strategies.append(CandlePatternStrategy(insight_book, None, candle_pattern, "SELL", 10, 5, min_tpo=1, max_tpo=1, triggers_per_signal=1))


class PatternAggregator(StrategyAggregator):
    def __init__(self, insight_book=None):
        super().__init__(insight_book)
        self.id = 'PATTERN_AGGR'
        self.individual_strategies.append(DoubleTopStrategy(insight_book, None, 'DT', "SELL", 15, 1, 'UP'))
        #self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 10, 1, 'UP'))
        # ABOVE 2 TRIGGERED LOT OF TRADES WHY?
        #self.individual_strategies.append(DoubleTopStrategy(insight_book, 'TREND', "SELL", 10, 1, 'UP'))
