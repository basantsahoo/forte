import numpy as np
from research.strategies.t_core_strategy  import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin

class MultiPatternStrategy(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, id, order_type, exit_time, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002], weekdays_allowed=[], criteria=[]):
        BaseStrategy.__init__(self, insight_book, id, order_type,exit_time, min_tpo, max_tpo, record_metric, triggers_per_signal, max_signal, target_pct, stop_loss_pct, weekdays_allowed, criteria)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id
        #print('multi pattern init')
        #print(self.__class__.__name__)
        self.last_match = None

    def relevant_signal(self):
        return True

    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal_to_journal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        return sig_key





