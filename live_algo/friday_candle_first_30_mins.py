import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.aggregators import CandlePatternStrategy

class FridayCandleFirst30Buy(CandlePatternStrategy):
    def __init__(self, insight_book,  id=None, pattern='CDLHIKKAKE', order_type="BUY", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002]):
        CandlePatternStrategy.__init__(self, insight_book,id,  pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal=triggers_per_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self):
        return super().suitable_market_condition() and self.insight_book.get_time_since_market_open() <= 30


class FridayCandleFirst30Sell(CandlePatternStrategy):
    def __init__(self, insight_book,  id=None, pattern='CDLHIKKAKE', order_type="SELL", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002]):
        CandlePatternStrategy.__init__(self, insight_book, id, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal=triggers_per_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self):
        return super().suitable_market_condition() and self.insight_book.get_time_since_market_open() <= 30

class FridayCandleBuyFullDay(CandlePatternStrategy):
    def __init__(self, insight_book, id=None, pattern='CDLHIKKAKE', order_type="BUY", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002]):
        CandlePatternStrategy.__init__(self, insight_book, id, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal=triggers_per_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']
        self.criteria = [
                        {'op': 'or', 'logical_test': 'd2_ad_resistance_pressure <= 0.045 and five_min_trend > -0.1'},
                        {'op': 'or', 'logical_test': '(exp_b <= 0.55 and d2_ad_resistance_pressure > 0.155)'},
                        {'op': 'or', 'logical_test': '(d2_ad_resistance_pressure > 0.045 and exp_b > 0.55 and d2_cd_new_business_pressure > 0.435 and open_type == "GAP_UP")'}
                        ]


class FridayCandleSellFullDay(CandlePatternStrategy):
    def __init__(self, insight_book, id=None, pattern='CDLHIKKAKE', order_type="SELL", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002]):
        CandlePatternStrategy.__init__(self, insight_book, id, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']



class FridayCandleBuyFullDayENG(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLENGULFING', order_type="BUY", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=[0.002,0.003, 0.004, 0.005], stop_loss_pct=[0.001,0.002, 0.002,0.002]):
        CandlePatternStrategy.__init__(self, insight_book, id, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

