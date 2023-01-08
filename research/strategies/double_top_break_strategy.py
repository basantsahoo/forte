import numpy as np
from research.strategies.core_strategy import BaseStrategy
from research.strategies.double_top_strategy import DoubleTopStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils


class DoubleTopBreakStrategy(DoubleTopStrategy):
    def __init__(self, insight_book, id=None, pattern="DT", order_type="SELL", exit_time=10, period=5, min_tpo=None, max_tpo=None, record_metric=True):
        DoubleTopStrategy.__init__(self, insight_book, id, pattern, order_type, exit_time, period, min_tpo=min_tpo, max_tpo=max_tpo, record_metric=record_metric)
        self.id = 'DTBRK' + "_" + order_type + "_" + str(period) + "_" + str(exit_time) if id is None else id

    def get_trades(self, pattern_match_prices, idx=1, curr_price=None,):
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = highest_high_point - neck_point
        last_candle = self.insight_book.last_tick
        if idx == 1:
            return {'seq': idx, 'target': lowest_high_point + pattern_height, 'stop_loss':neck_point - 2,'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}
        elif idx == 2:
            return {'seq': idx, 'target': lowest_high_point + 2 * pattern_height, 'stop_loss': lowest_high_point - 2, 'duration': self.exit_time * 2, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}

    def initiate_signal_trades(self, sig_key):
        pass


    def suitable_market_condition(self, matched_pattern):
        return True

    def process_incomplete_signals(self):
        #print('process_incomplete_signals+++++++++')
        last_candle = self.insight_book.last_tick
        if not self.insight_book.pm.reached_risk_limit(self.id) and self.tradable_signals: #risk limit not reached and there are some signals
            for sig_key, signal in self.tradable_signals.items():
                pattern_end_price = min(signal['pattern']['price_list'][1], signal['pattern']['price_list'][3])
                if not signal['trade_completed'] and last_candle['close'] > pattern_end_price:
                    #print(self.tradable_signals)
                    next_trigger = len(signal['triggers']) + 1
                    triggers = [self.get_trades(signal['pattern']['price_list'], trd_idx) for trd_idx in range(next_trigger, next_trigger + 1 + 1)]
                    self.trigger_entry(self.order_type, sig_key, triggers)
                    signal['trade_completed'] = True



