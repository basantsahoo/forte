import numpy as np
from research.strategies.core_option_strategy import BaseOptionStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.cheap_option_buy import CheapOptionBuy


class ThursdayOptionBuy(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_THURS", exit_time=60, min_tpo=1, max_tpo=13,  max_signal = 10, target_pct=[0.1,0.2, 0.3, 0.5], stop_loss_pct=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book,id=id,  exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.last_match = None
        self.weekdays_allowed = ['Thursday']
        self.criteria = [
            {"op": "or", "logical_test": "open_type in ['GAP_DOWN'] and tpo in [10,11] and strength >= 80  and kind in ['PE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3']"},
        ]
        print('ThursdayOptionBuy init')

    def evaluate_signal(self, matched_pattern):
        print('process_pattern_signal wednesday+++++++++++', matched_pattern)
        last_match_ol = 0
        signal_passed = False
        """
        Control when a signal is considered for trade
        """
        #print("self.suitable_market_condition======", self.suitable_market_condition(matched_pattern))
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern
            print('in evaluate_signal,', self.record_metric)
            matched_pattern['candle'] = [0,0,0,0]
            self.record_params(matched_pattern)
            signal_passed = True
        #print('signal_passed====', signal_passed)
        return signal_passed
