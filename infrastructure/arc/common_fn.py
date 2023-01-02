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
from infrastructure.arc.buy_sell_activity import BuySellActivity

class CommonFN:
    def __init__(self, ticker, trade_day=None, record_metric=True):
        self.intraday_trend = IntradayTrendCalculator(self)
        self.activity_log = BuySellActivity(self)
        self.day_setup_done = False
        self.strategy_setup_done = False
        self.range = {'low': 99999999, 'high': 0}
        self.trade_day = trade_day
        self.market_data = OrderedDict()
        self.market_insights = {}
        self.pm = None
        self.profile_processor = None
        self.strategies = []
        self.ticker = ticker
        self.record_metric = record_metric
        self.run_aggregator=False
        self.curr_tpo = None
        self.last_tick = None
        self.last_periodic_update = None
        self.periodic_update_sec = 60
        self.open_type = None
        self.state_generator = None
        self.transition_data = {}
        self.mc = MarkovChainSecondLevel()
        self.state_prob_calculator = EmpiricalDistribution(self.transition_data)
        if trade_day is not None:
            self.set_day_tpos(trade_day)
            self.set_key_levels()
            self.set_transition_matrix()
            self.day_setup_done = True

    def set_trade_date_from_time(self, epoch_tick_time):
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        trade_day = tick_date_time.strftime('%Y-%m-%d')
        self.trade_day = trade_day
        self.set_day_tpos(trade_day)
        self.set_key_levels()
        self.set_transition_matrix()
        self.day_setup_done = True

    def set_day_tpos(self, trade_day):
        start_str = trade_day + " 09:15:00"
        ib_end_str = trade_day + " 10:15:00"
        end_str = trade_day + " 15:30:00"
        start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S")))
        ib_end_ts = int(time.mktime(time.strptime(ib_end_str, "%Y-%m-%d %H:%M:%S")))
        self.ib_periods = [start_ts, ib_end_ts]
        self.tpo_brackets = np.arange(start_ts, end_ts, 1800)

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

    def set_transition_matrix(self):
        self.state_generator = DayFullStateGenerator(self.ticker, self.trade_day, self.yday_profile)
        try:
            f = open(reports_dir + 'full_state_' + self.ticker + '.json')
            data = json.load(f)
            self.transition_data = MCPreprocessor().get_processed_data(data, symbol=self.ticker, start_tpo=1, end_tpo=None)
            self.mc.from_data(self.transition_data, "unique_transitions_fill_break")
            self.state_prob_calculator = EmpiricalDistribution(self.transition_data,"unique_transitions_fill_break")
        except:
            pass

    def add_strategy(self, strategy_class, strategy_kwarg={}):
        strategy = strategy_class(self, **strategy_kwarg)
        if strategy.is_aggregator:
            self.run_aggregator = True
        strategy.record_metric = self.record_metric
        self.strategies.append(strategy)

    def remove_strategy(self, strategy_to_remove):
        for strategy in self.strategies:
            if strategy.id == strategy_to_remove.id:
                strategy.insight_book = None
                self.strategies.remove(strategy)
                break

    def determine_day_open(self): ## this is definitive
        open_candle = next(iter(self.market_data.items()))[1]
        open_low = open_candle['open']
        open_high = open_candle['open']
        if open_low >= self.yday_profile['high']:
            self.open_type = 'GAP_UP'
        elif open_high <= self.yday_profile['low']:
            self.open_type = 'GAP_DOWN'
        elif open_low >= self.yday_profile['va_h_p']:
            self.open_type = 'ABOVE_VA'
        elif open_high <= self.yday_profile['va_l_p']:
            self.open_type = 'BELOW_VA'
        else:
            self.open_type = 'INSIDE_VA'

    def determine_level_break(self, ts):
        for k in self.yday_level_breaks:
            if not self.yday_level_breaks[k]['value']:
                level_range = [self.yday_profile[k] * (1 - 0.0015), self.yday_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.yday_level_breaks[k]['value'] = True
                    self.yday_level_breaks[k]['time'] = ts-self.ib_periods[0]

    def update_periodic(self):
        self.intraday_trend.calculate_measures()
        #print(self.intraday_trend.trend_params)
        self.market_insights = {**self.market_insights, **self.intraday_trend.trend_params}

    def set_up_strategies(self):
        self.activity_log.set_up()
        for strategy in self.strategies:
            strategy.set_up()

    def price_input_stream(self, price, iv=None):
        #print('price_input_stream+++++ insight book')
        epoch_tick_time = price['timestamp']
        epoch_minute = int(epoch_tick_time // 60 * 60) + 1
        key_list = ['timestamp','open', 'high', "low", "close"]
        feed_small = {key: price[key] for key in key_list}
        self.last_tick = feed_small
        #print(epoch_tick_time)
        if not self.day_setup_done:
            self.set_trade_date_from_time(epoch_tick_time)

        self.range['low'] = min(feed_small['low'], self.range['low'])
        self.range['high'] = max(feed_small['high'], self.range['high'])
        self.market_data[epoch_minute] = feed_small
        self.set_curr_tpo(epoch_minute)
        if len(self.market_data.items()) == 2 and self.open_type is None:
            self.determine_day_open()
            self.set_up_strategies()
        self.determine_level_break(epoch_tick_time)
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
        if price['timestamp'] - self.last_periodic_update > self.periodic_update_sec:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        self.update_state_transition()
        self.activity_log.process()
        """
        for strategy in self.strategies:
            strategy.evaluate()
        """
    def update_state_transition(self):
        last_state = self.state_generator.curr_state
        if last_state == '':
            self.state_generator.set_open_type(self.last_tick)
        self.state_generator.update_state(self.last_tick['close'])
        features = self.state_generator.get_features()
        #print(features)
        if last_state == '':
            open_type = features['open_type']
            probs = self.mc.get_prob_from_curr_state(open_type)
            #print(probs)
            self.pattern_signal('STATE', {'signal': 'open_type', 'params': {'open_type':open_type, 'probs': probs}})

    def pattern_signal(self, pattern, pattern_match_idx):
        if pattern == 'TREND':
            #print('TREND+++++', pattern, pattern_match_idx)
            self.market_insights = {**self.market_insights, **pattern_match_idx['trend']}
            for wave in pattern_match_idx['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
        for strategy in self.strategies:
            if strategy.is_aggregator:
                strategy.process_signal(pattern, pattern_match_idx)
            elif strategy.price_pattern == pattern:
                strategy.process_signal(pattern_match_idx)

        if self.pm.data_interface is not None:
            self.pm.data_interface.notify_pattern_signal(self.ticker, pattern, pattern_match_idx)

        #print('self.intraday_trend')
        #print(self.market_insights)

    def get_prior_wave(self, epoch_minute):
        all_waves_end_time = list(self.intraday_waves.keys())
        all_waves_end_time.sort()
        wave_idx = profile_utils.get_next_lowest_index(all_waves_end_time, epoch_minute)
        return self.intraday_waves[all_waves_end_time[wave_idx]]

    def set_curr_tpo(self, epoch_minute):
        ts_idx = profile_utils.get_next_lowest_index(self.tpo_brackets, epoch_minute)
        ts_idx = 13 if ts_idx < 0 else ts_idx + 1
        self.curr_tpo = ts_idx

    def get_sma(self, period=5):
        price_list = list(self.market_data.values())
        close = np.array([x['high'] for x in price_list])
        output = stream.SMA(close, timeperiod=period)
        return output

    def get_signal_generator_from_id(self, strat_id):
        strategy_signal_generator = None
        for strategy in self.strategies:
            if strategy.is_aggregator:
                strategy_signal_generator = strategy.get_signal_generator_from_id(strat_id)
            elif strategy.id == strat_id:
                    strategy_signal_generator = strategy
            if strategy_signal_generator is not None:
                break
        return strategy_signal_generator

    def get_inflex_pattern_df(self, period=None):
        return self.inflex_detector

    def get_time_to_close(self):
        return 375-len(self.market_data.items())

    def clean(self):
        self.inflex_detector = None
        for detector in self.price_action_pattern_detectors:
            detector.insight_book = None
        for detector in self.candle_pattern_detectors:
            detector.insight_book = None
        self.price_action_pattern_detectors = []
        self.candle_pattern_detectors = []

        self.trend_detector.insight_book = None
        self.trend_detector = None
        self.intraday_trend.insight_book = None
        self.intraday_trend = None
        self.market_data = None
        self.market_insights = {}
        self.pm = None
        self.profile_processor = None
        self.strategies = []
        self.state_generator = None
        self.transition_data = {}
        self.mc = None
        self.state_prob_calculator = None
