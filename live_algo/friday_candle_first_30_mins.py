import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.candle_pattern_strategy import CandlePatternStrategy

class FridayCandleFirst30Buy(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLHIKKAKE', order_type="BUY", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.002):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal)

    def set_up(self):
        pass

    def suitable_market_condition(self,matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = (self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo and len(self.insight_book.market_data.items()) <= 30





