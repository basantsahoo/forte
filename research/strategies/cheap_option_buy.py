import numpy as np
from research.strategies.core_option_strategy import BaseOptionStrategy
from helper.utils import get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.signal_setup import get_signal_key, get_target_fn

class CheapOptionBuy(BaseOptionStrategy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY", order_type="BUY", exit_time=60,  max_signal = 10000000, target_pct=[0.1,0.2, 0.3, 0.5], stop_loss_pct=[0.5,0.5, 0.5,0.5], signal_filter_conditions=[], weekdays_allowed=[]):
        entry_criteria = [{'OPTION_PRICE_DROP': []}]
        BaseOptionStrategy.__init__(self, insight_book, id=id, order_type=order_type,  exit_time=exit_time, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct, signal_filter_conditions=signal_filter_conditions, weekdays_allowed=weekdays_allowed, entry_criteria = entry_criteria)
        #print(self.id)
        #self.record_metric = False
        self.last_match = None

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP'):
            self.derivative_instruments.append(signal['instrument'])

    def process_post_entry(self):
        self.derivative_instruments = []



