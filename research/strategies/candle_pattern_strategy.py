import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin

class CandlePatternStrategy(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, id, pattern, order_type, exit_time, period, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, target=[0.002,0.003, 0.004, 0.005], stop_loss=[0.001,0.002, 0.002,0.002], weekdays_allowed=[], criteria=[]):
        BaseStrategy.__init__(self, insight_book, id, pattern, order_type,exit_time, period,trend, min_tpo, max_tpo, record_metric, triggers_per_signal, max_signal, target, stop_loss, weekdays_allowed, criteria)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time) if id is None else id
        #print(self.id)
        self.last_match = None

    def relevant_signal(self, pattern, pattern_match_idx):
        #print('relevant_signal candle====', self.price_pattern == pattern)
        return self.price_pattern == pattern and self.order_type == pattern_match_idx['direction'] and self.period == pattern_match_idx['period']


    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal_to_journal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        return sig_key

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal candle+++++++++++', self.price_pattern)
        # looking for overlap in time
        """
        determine whether a new signal
        """
        last_match_ol = 0 if self.last_match is None else int(matched_pattern['time'] == self.last_match['time'])
        signal_passed = False
        #print(last_match_ol)
        """
        Control when a signal is considered for trade
        """
        #print("self.suitable_market_condition======", self.suitable_market_condition(matched_pattern))
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern
            self.record_params(matched_pattern)
            signal_passed = True
        #print('signal_passed====', signal_passed)
        return signal_passed




