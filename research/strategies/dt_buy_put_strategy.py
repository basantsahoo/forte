import numpy as np
from research.strategies.t_core_strategy  import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.signal_setup import get_signal_key, get_target_fn
from arc.signal_queue import SignalQueue

class DTBuyPut(BaseStrategy):
    def __init__(self, insight_book, id, order_type, spot_instruments, derivative_instruments, exit_time, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, spot_targets=[0.002,0.003, 0.004, 0.005], spot_stop_losses=[0.001,0.002, 0.002,0.002], instr_targets=[], instr_stop_losses=[], weekdays_allowed=[], entry_criteria=[], exit_criteria_list=[],signal_filter_conditions=[]):
        self.instr_to_trade = derivative_instruments
        BaseStrategy.__init__(self, insight_book=insight_book, id=id, order_type=order_type, spot_instruments=spot_instruments, derivative_instruments=[], exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, record_metric=record_metric, triggers_per_signal=triggers_per_signal, max_signal=max_signal, spot_targets=spot_targets, spot_stop_losses=spot_stop_losses, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses, weekdays_allowed=weekdays_allowed, signal_filter_conditions=signal_filter_conditions, entry_criteria=entry_criteria, exit_criteria_list=exit_criteria_list)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id

    def register_instrument(self, signal):

        if (signal['category'], signal['indicator']) == get_signal_key('DT'):
            #print('instrument register')
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            atm_strike = round(ltp/100)*100
            for instr in self.instr_to_trade:
                money_ness = instr[0]
                kind = instr[2]
                level = -100*instr[1] if kind == 'PE' else instr[1]*100
                otm_strike = atm_strike + level
                itm_strike = atm_strike - level
                strike = otm_strike if money_ness == 'OTM' else itm_strike if money_ness == 'ITM' else atm_strike
                self.derivative_instruments.append(str(strike) + "_" + kind)

    def process_post_entry(self):
        self.derivative_instruments = []