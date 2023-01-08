import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.strat_mixin import PatternMetricRecordMixin
from research.strategies.aggregators import CandlePatternStrategy

class FridayCandleFirst30Buy(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLHIKKAKE', order_type="BUY", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.001):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self, matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo and len(self.insight_book.market_data.items()) <= 30


class FridayCandleFirst30Sell(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLHIKKAKE', order_type="SELL", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.001):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self, matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo and len(self.insight_book.market_data.items()) <= 30

class FridayCandleBuyFullDay(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLHIKKAKE', order_type="BUY", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.001,criteria=[]):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct, criteria)
        self.weekdays_allowed = ['Friday', 'Thursday']
        self.criteria = [
                        {'op': 'or', 'logical_test': 'd2_ad_resistance_pressure <= 0.045 and five_min_trend > -0.1'},
                        {'op': 'or', 'logical_test': '(exp_b <= 0.55 and d2_ad_resistance_pressure > 0.155)'},
                        {'op': 'or', 'logical_test': '(d2_ad_resistance_pressure > 0.045 and exp_b > 0.55 and d2_cd_new_business_pressure > 0.435 and open_type == "GAP_UP")'}
                        ]

    def suitable_market_condition(self,matched_pattern):
        print('checking suitable_market_condition')
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)
        suitable = enough_time and suitable_tpo
        if suitable:
            print('checking suitable_market_condition 1')
            market_params = self.insight_book.activity_log.get_market_params()
            d2_ad_resistance_pressure = market_params['d2_ad_resistance_pressure']
            five_min_trend = market_params['five_min_trend']
            exp_b = market_params['exp_b'] if 'exp_b' in market_params else 0
            d2_cd_new_business_pressure = market_params['d2_cd_new_business_pressure']
            open_type = market_params['open_type']
            flag = False
            for condition in self.criteria:
                flag = flag or eval(condition['logical_test'])
            suitable = suitable and flag
        return suitable


class FridayCandleSellFullDay(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLHIKKAKE', order_type="SELL", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.001):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self, matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo


class FridayCandleBuyFullDayENG(CandlePatternStrategy):
    def __init__(self, insight_book, pattern='CDLENGULFING', order_type="BUY", exit_time=15, period=5, trend=None, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, target_pct=0.002, stop_loss_pct=0.001):
        CandlePatternStrategy.__init__(self, insight_book, pattern, order_type, exit_time, period, trend, min_tpo, max_tpo, record_metric, triggers_per_signal, target_pct, stop_loss_pct)
        self.weekdays_allowed = ['Friday', 'Thursday']

    def suitable_market_condition(self, matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)

        return enough_time and suitable_tpo

