import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import  get_overlap
from dynamics.profile.utils import get_next_highest_index
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type


class StateCapStrategy(BaseStrategy):
    def __init__(self, insight_book, id, pattern, order_type, exit_time, period, trend=None, min_tpo=None, max_tpo=None, record_metric=True):
        BaseStrategy.__init__(self, insight_book, id, min_tpo, max_tpo)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time) if id is None else id
        #print(self.id)
        self.price_pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend

    def get_trades(self, pattern_match_prob, idx=1):
        last_candle = self.insight_book.last_tick
        side = get_broker_order_type(self.order_type)
        prob_numbers = list(pattern_match_prob.values())
        level_keys = list(pattern_match_prob.keys())
        prob_cut_off = 0  # slightly greater than the value as function checks for equals
        #print(pattern_match_prob)
        down_zero_prob_idx = min([i for i, v in enumerate(prob_numbers) if v > prob_cut_off]) - 1
        prob_numbers.reverse()
        up_zero_prob_idx = len(prob_numbers) - min([i for i, v in enumerate(prob_numbers) if v > prob_cut_off])

        neck_point = 0
        up_ceil = self.insight_book.state_generator.price_bands_reverse[level_keys[up_zero_prob_idx-(idx-1)]]
        down_floor = self.insight_book.state_generator.price_bands_reverse[level_keys[down_zero_prob_idx+(idx-1)]]
        return {'seq': idx, 'target': down_floor, 'stop_loss':up_ceil,'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}

    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal_to_journal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        #self.tradable_signals[sig_key]['max_triggers'] = 2
        return sig_key

    def suitable_market_condition(self,matched_pattern):
        return matched_pattern['params']['open_type'] != 'INSIDE_VA'

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal+++++++++++', matched_pattern)
        # looking for overlap in time
        """
        determine whether a new signal
        """
        last_match_ol = 0 if self.last_match is None else 1
        signal_passed = False
        #print(last_match_ol)
        """
        Control when a signal is considered for trade
        """
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern['params']['open_type']
            pattern_location = 0
            if self.record_metric:
                self.strategy_params['pattern_time'] = [self.insight_book.last_tick['timestamp']]
                self.strategy_params['pattern_price'] = [self.insight_book.last_tick['close']]
                self.strategy_params['pattern_location'] = pattern_location
                keys = ['total_energy_pyr', 'total_energy_ht', 'static_ratio', 'dynamic_ratio', 'd_en_ht', 's_en_ht', 'd_en_pyr', 's_en_pyr']
                for key in keys:
                    self.strategy_params['lw_'+ key] = 0
            signal_passed = True
        return signal_passed
