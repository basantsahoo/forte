import numpy as np
from research.strategies.core_option_strategy import BaseOptionStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin

class OptionHeavySellStrategy(BaseOptionStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY", pattern="OPTION_PRICE_DROP", order_type="BUY", exit_time=60, min_tpo=1, max_tpo=13,  max_signal = 10000000, target_pct=[0.1,0.2, 0.3, 0.5], stop_loss_pct=[0.5,0.5, 0.5,0.5], criteria=[]):
        print('OptionHeavySellStrategy init')
        print('self.pattern' , pattern)
        BaseOptionStrategy.__init__(self, insight_book, id=id, pattern=pattern, order_type=order_type, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct, criteria=criteria)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time) if id is None else id
        #print(self.id)
        #self.record_metric = False
        self.last_match = None

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal option heavy sell+++++++++++', matched_pattern)
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


    """
    def calculate_custom_signal(self):
        for inst in self.insight_book.option_processor.option_data_inst_ts:
            inst_series = self.insight_book.option_processor.option_data_inst_ts[inst]
            inst_series = list(inst_series.values())
            open_price = inst_series[0]['close']
            last_price = inst_series[-1]['close']
            if last_price < 0.5 * open_price:
                print(inst)
    """
    """will be used by strategy which doesnt have a pattern/trend signal"""
    """
    def process_custom_signal(self):
        signal_found = self.calculate_custom_signal() #len(self.tradable_signals.keys()) < self.max_signals+5  #
        if signal_found:
            sig_key = self.add_tradable_signal(pattern_match_idx)
            self.initiate_signal_trades(sig_key)
    """



