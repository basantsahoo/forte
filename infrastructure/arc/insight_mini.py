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
from settings import reports_dir
# Transitions
from dynamics.transition.intra_day_transition import DayFullStateGenerator
from dynamics.transition.mc_pre_process import MCPreprocessor
from dynamics.transition.second_level_mc import MarkovChainSecondLevel
from dynamics.transition.point_to_point_mc import MarkovChainPointToPoint
from dynamics.transition.empirical import EmpiricalDistribution
from infrastructure.arc.common_fn import CommonFN


class InsightBook(CommonFN):
    def set_key_levels(self):
        ticker = self.ticker
        self.weekly_pivots = get_pivot_points(get_prev_week_candle(ticker, self.trade_day))
        self.yday_profile = get_nth_day_profile_data(ticker, self.trade_day, 1).to_dict('records')[0]
        self.day_before_profile = get_nth_day_profile_data(ticker, self.trade_day, 2).to_dict('records')[0]
        self.yday_level_breaks = {'high': {'value': False, 'time': -1}, 'low': {'value': False, 'time': -1}, 'poc_price': {'value': False, 'time': -1}, 'va_h_p': {'value': False, 'time': -1}, 'va_l_p': {'value': False, 'time': -1}}
        self.day_before_level_breaks = {'high': {'value': False, 'time': -1}, 'low': {'value': False, 'time': -1}, 'poc_price': {'value': False, 'time': -1}, 'va_h_p': {'value': False, 'time': -1}, 'va_l_p': {'value': False, 'time': -1}}
        self.weekly_level_breaks = {'high': {'value': False, 'time':-1}, 'low': {'value': False, 'time':-1}, 'Pivot': {'value': False, 'time':-1}, 'S1': {'value': False, 'time':-1}, 'S2': {'value': False, 'time':-1}, 'S3': {'value': False, 'time':-1}, 'S4': {'value': False, 'time':-1}, 'R1': {'value': False, 'time':-1}, 'R2': {'value': False, 'time':-1},  'R3': {'value': False, 'time':-1}, 'R4': {'value': False, 'time':-1}}
        self.intraday_waves = {}
        prev_key_levels = get_prev_day_key_levels(ticker, self.trade_day)

        range_to_watch = [self.yday_profile['low'] * 0.97, self.yday_profile['high'] * 1.03]
        existing_supports = json.loads(prev_key_levels[1])
        existing_resistances = json.loads(prev_key_levels[2])
        self.supports_to_watch = [x for x in existing_supports if (x >= range_to_watch[0]) and (x <= range_to_watch[1])]
        self.resistances_to_watch = [x for x in existing_resistances if (x >= range_to_watch[0]) and (x <= range_to_watch[1])]

    def determine_level_break(self, ts):
        for k in self.yday_level_breaks:
            if not self.yday_level_breaks[k]['value']:
                level_range = [self.yday_profile[k] * (1 - 0.0015), self.yday_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.yday_level_breaks[k]['value'] = True
                    self.yday_level_breaks[k]['time'] = ts-self.ib_periods[0]


    def pattern_signal(self, pattern, pattern_match_idx):
        #print('pattern_signal mini+++++++ 1', pattern, pattern_match_idx)
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
