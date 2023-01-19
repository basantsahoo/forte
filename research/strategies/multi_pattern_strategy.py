import numpy as np
from research.strategies.t_core_strategy  import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.signal_setup import get_signal_key, get_target_fn
from arc.signal_queue import SignalQueue

class MultiPatternStrategy(BaseStrategy):
    def __init__(self, insight_book, id, order_type, spot_instruments, derivative_instruments, exit_time, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, spot_targets=[0.002,0.003, 0.004, 0.005], spot_stop_losses=[0.001,0.002, 0.002,0.002], weekdays_allowed=[], signal_filter_conditions=[]):
        BaseStrategy.__init__(self, insight_book=insight_book, id=id, order_type=order_type, spot_instruments=spot_instruments, derivative_instruments=derivative_instruments, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, record_metric=record_metric, triggers_per_signal=triggers_per_signal, max_signal=max_signal, spot_targets=spot_targets, spot_stop_losses=spot_stop_losses, weekdays_allowed=weekdays_allowed, signal_filter_conditions=signal_filter_conditions)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id
        #print('multi pattern init')
        #print(self.__class__.__name__)
        self.last_match = None
        self.entry_criteria = [
            {'OPEN_TYPE' : [-1, 'signal', "==", 'GAP_UP']},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', "<=", 20]},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', ">=", 5]},
            {'DT': [-1, 'pattern_height', ">=", -100]},
            {'TREND': [-1, "all_waves[-1]['dist']", ">=", -100]}
        ]
        self.entry_signal_queues = {pattern: SignalQueue(self,pattern) for pattern in
                                    [get_signal_key(list(set(criteria.keys()))[0]) for criteria in self.entry_criteria]}
        self.exit_criteria_list = [[
            {'CANDLE_5_DOJI_SELL': [-1, 'time_lapsed', ">=", 5]}
        ]]
        temp_patterns = []
        for criteria_list in self.exit_criteria_list:
            for criteria in criteria_list:
                temp_patterns.append(get_signal_key(list(criteria.keys())[0]))
        temp_patterns = list(set(temp_patterns))
        self.exit_signal_queues = {pattern: SignalQueue(self,pattern) for pattern in temp_patterns}

        print('self.entry_signal_queues+++++++++++', self.entry_signal_queues)
        print('self.exit_signal_queues+++++++++++', self.exit_signal_queues)
        #self.spot_targets = ['DT_HEIGHT_TARGET',  'LAST_N_CANDLE_BODY_TARGET', 'PCT_SPOT']
        self.inst_targets = []


