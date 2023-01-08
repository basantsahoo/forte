import numpy as np
import json
from datetime import datetime
import time
from collections import OrderedDict
import talib
from talib import stream

from db.market_data import get_daily_tick_data, prev_day_data, get_prev_week_candle, get_nth_day_profile_data, get_prev_day_key_levels
from helper.utils import get_pivot_points, get_overlap
from dynamics.profile import utils as profile_utils

from dynamics.trend.tick_price_smoothing import PriceInflexDetectorForTrend
from dynamics.trend.intraday_trend import IntradayTrendCalculator
from dynamics.patterns.price_action_pattern_detector import PriceActionPatternDetector
from dynamics.patterns.trend_detector import TrendDetector
from dynamics.patterns.candle_pattern_detector import CandlePatternDetector
# Transitions
from dynamics.transition.intra_day_transition import DayFullStateGenerator
from dynamics.transition.mc_pre_process import MCPreprocessor
from dynamics.transition.second_level_mc import MarkovChainSecondLevel
from dynamics.transition.point_to_point_mc import MarkovChainPointToPoint
from dynamics.transition.empirical import EmpiricalDistribution
from infrastructure.arc.common_fn import CommonFN


class InsightBook(CommonFN):

    def pattern_signal(self, pattern, pattern_match_idx):
        #print('pattern_signal mini+++++++ 1', pattern, pattern_match_idx['strength'])
        if pattern == 'TREND':
            #print('TREND+++++', pattern, pattern_match_idx)
            self.market_insights = {**self.market_insights, **pattern_match_idx['trend']}
            for wave in pattern_match_idx['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
        for strategy in self.strategies:
            strategy.process_signal(pattern, pattern_match_idx)
            """
            if strategy.is_aggregator:
                strategy.process_signal(pattern, pattern_match_idx)
            elif strategy.price_pattern == pattern:
                strategy.process_signal(pattern_match_idx)
            """

        if self.pm.data_interface is not None:
            self.pm.data_interface.notify_pattern_signal(self.ticker, pattern, pattern_match_idx)
