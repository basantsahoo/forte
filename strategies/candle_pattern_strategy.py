import numpy as np
from strategies.core_strategy import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from strategies.strat_mixin import PatternMetricRecordMixin

class CandlePatternStrategy(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, pattern, order_type, exit_time, period, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=2):
        BaseStrategy.__init__(self, insight_book, order_type, min_tpo, max_tpo)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time)
        #print(self.id)
        self.price_pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend
        self.triggers_per_signal = triggers_per_signal

    def set_up(self):
        pass

    def get_trades(self, pattern_match_prices, idx=1, curr_price=None,):
        high_point = pattern_match_prices[1]
        low_point = pattern_match_prices[2]
        close_point = pattern_match_prices[3]
        last_candle = self.insight_book.last_tick
        neck_point = 0
        side = get_broker_order_type(self.order_type)
        if idx == 1:
            return {'seq': idx, 'target': close_point * (1 + side * 0.002), 'stop_loss':close_point * (1 - side * 0.001),'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}
        elif idx == 2:
            return {'seq': idx, 'target': close_point * (1 + side * 0.003), 'stop_loss': close_point * (1 - side * 0.0015), 'duration': self.exit_time + 10, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}

    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        self.tradable_signals[sig_key]['max_triggers'] = 2
        return sig_key

    def suitable_market_condition(self,matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = (self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo and len(self.insight_book.market_data.items()) <= 30


    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_trades(curr_signal['pattern']['candle'], trd_idx) for trd_idx in range(next_trigger, next_trigger + self.triggers_per_signal)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type, sig_key, triggers)

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal+++++++++++', matched_pattern)
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
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern
            self.record_params()
            signal_passed = True
        return signal_passed




