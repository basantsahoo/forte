import numpy as np
from datetime import datetime
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.t_core_strategy import BaseStrategy

class BaseOptionStrategy(BaseStrategy):
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",
                 instrument_type='OPTION',
                 instrument = None,
                 exit_time=10,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 target_pct=[0.002, 0.003, 0.004, 0.005],
                 stop_loss_pct=[0.001, 0.002, 0.002, 0.002],
                 weekdays_allowed=[],
                 entry_criteria=[],
                 exit_criteria_list=[],
                 filter_conditions=[],
                 spot_targets=[],
                 inst_targets=[]
                 ):
        BaseStrategy.__init__(self, insight_book, id, order_type,instrument_type, instrument, exit_time, min_tpo, max_tpo, record_metric, triggers_per_signal,
                              max_signal, target_pct, stop_loss_pct, weekdays_allowed, entry_criteria,exit_criteria_list, filter_conditions,spot_targets,inst_targets)

