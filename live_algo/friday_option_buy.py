import numpy as np
from research.strategies.core_option_strategy import BaseOptionStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.cheap_option_buy import CheapOptionBuy


class FridayOptionBuy(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_FRI", exit_time=60, min_tpo=1, max_tpo=13,  max_signal = 10, target_pct=[0.1,0.2, 0.3, 0.5], stop_loss_pct=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id,  exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.last_match = None
        self.weekdays_allowed = ['Friday']
        self.put_bought = 0  # Do separate for this BELOW VA only buy Puts non of of them came below 20% in the sample
        self.criteria = [
            {"op": "or", "logical_test": "open_type in ['GAP_UP'] and tpo in [1,2,6,7,8] and strength >= 20  and kind in ['PE'] and money_ness in ['ATM_0' , 'OTM_1' , 'OTM_2', 'OTM_3']"},
            {"op": "or", "logical_test": "open_type in ['ABOVE_VA'] and strength >= 20  and kind in ['CE'] and money_ness in ['ATM_0' , 'OTM_1' , 'OTM_2']"},
            {"op": "or", "logical_test": "open_type in ['ABOVE_VA'] and tpo in [2,3] and strength >= 20  and kind in ['PE'] and money_ness in ['OTM_3' , 'OTM_4', 'OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['INSIDE_VA'] and tpo in [10,11] and strength >= 20  and kind in ['CE'] and money_ness in [ 'OTM_1' , 'OTM_2', 'OTM_3', 'OTM_4']"},
            {"op": "or", "logical_test": "open_type in ['GAP_DOWN'] and tpo in [1,6,7,8,9,10] and strength >= 20 and strength <= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2', 'OTM_3']"},
        ]
    def evaluate_signal(self, matched_pattern):
        print('process_pattern_signal Friday+++++++++++', matched_pattern)
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

class FridayBelowVA(CheapOptionBuy):
    def __init__(self, insight_book, id="BELOWVAFRI", exit_time=60, min_tpo=1, max_tpo=1,  max_signal = 10, target_pct=[0.2, 0.3, 0.3, 0.5], stop_loss_pct=[0.25,0.3, 0.4,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id, pattern="STATE", exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct, triggers_per_signal =4)
        self.last_match = None
        self.weekdays_allowed = ['Friday']
        self.put_bought = 0  # Do separate for this BELOW VA only buy Puts non of of them came below 20% in the sample
        self.open_types_allowed = ['BELOW_VA']

    def add_tradable_signal(self, pattern_match_idx):
        sig_key = self.add_new_signal_to_journal(pattern_match_idx)
        kind = 'PE'
        last_tick = self.insight_book.last_tick
        strike = int(last_tick['close'] / 100) * 100
        otm_strike = strike - 100 if kind == 'PE' else strike + 100
        pattern = {'strike': otm_strike, 'kind': kind, 'instrument': str(otm_strike) + "_" + kind, 'cover': 0, 'time': last_tick['timestamp']}
        self.tradable_signals[sig_key]['pattern'] = pattern
        return sig_key

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal Friday gap down+++++++++++', matched_pattern)
        last_match_ol = 0
        signal_passed = False
        """
        Control when a signal is considered for trade
        """
        #print("self.suitable_market_condition======", self.suitable_market_condition(matched_pattern))
        if self.suitable_market_condition(matched_pattern) and not self.put_bought:
            self.last_match = matched_pattern
            print('in evaluate_signal,', self.record_metric)
            matched_pattern['candle'] = [0,0,0,0]
            #self.record_params(pattern_match_idx)
            self.put_bought = 1
            signal_passed = True
        #print('signal_passed====', signal_passed)
        return signal_passed

    def suitable_market_condition(self, signal={}):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)
        suitable = enough_time and suitable_tpo
        #print('enough_time', enough_time)
        #print('suitable_tpo', suitable_tpo)
        if suitable:
            flag  = signal['params']['open_type'] in self.open_types_allowed
            suitable = suitable and flag
        return suitable

