import numpy as np
import json
from datetime import datetime
import time
from collections import OrderedDict
from talib import stream

from db.market_data import get_prev_week_candle, get_nth_day_profile_data, get_prev_day_key_levels
from helper.utils import get_pivot_points, convert_to_candle
from dynamics.profile import utils as profile_utils
from dynamics.constants import INDICATOR_TREND
from dynamics.trend.tick_price_smoothing import PriceInflexDetectorForTrend
from dynamics.trend.intraday_trend import IntradayTrendCalculator
from dynamics.patterns.price_action_pattern_detector import PriceActionPatternDetector
from dynamics.patterns.trend_detector import TrendDetector
from dynamics.patterns.candle_pattern_detector import CandlePatternDetector
from servers.server_settings import cache_dir
# Transitions
from dynamics.transition.intra_day_transition import DayFullStateGenerator
from dynamics.transition.mc_pre_process import MCPreprocessor
from dynamics.transition.second_level_mc import MarkovChainSecondLevel
from dynamics.transition.empirical import EmpiricalDistribution
from arc.market_activity import AssetActivityLog
from arc.intraday_option_processor import IntradayOptionProcessor
from arc.spot_processor import SpotProcessor
from arc.candle_processor import CandleProcessor
from entities.base import BaseSignal, Signal
from entities.trading_day import TradeDateTime

class SpotBook:
    def __init__(self, asset_book, asset):
        self.asset_book = asset_book
        self.asset = asset
        self.spot_processor = SpotProcessor(self)
        self.option_processor = IntradayOptionProcessor(self, asset)
        self.candle_1_processor = CandleProcessor(self, 1, 0)
        self.candle_5_processor = CandleProcessor(self, 5, 0)
        self.candle_15_processor = CandleProcessor(self, 15, 0)
        self.state_generator = None
        self.trend = {}
        self.activity_log = AssetActivityLog(self)
        self.inflex_detector = PriceInflexDetectorForTrend(asset, fpth=0.001, spth = 0.001,  callback=None)
        self.price_action_pattern_detectors = [PriceActionPatternDetector(self, period=1)]
        self.candle_pattern_detectors = [CandlePatternDetector(self, period=5), CandlePatternDetector(self, period=15)]
        self.trend_detector = TrendDetector(self, period=1)
        self.intraday_trend = IntradayTrendCalculator(self)
        self.day_setup_done = False
        self.mc = MarkovChainSecondLevel()
        self.last_periodic_update = None
        self.periodic_update_sec = 60

    def feed_stream(self, feed_list):
        for feed in feed_list:
            #print(feed)
            self.spot_minute_data_stream(feed)

    def day_change_notification(self, trade_day):
        self.set_key_levels()

    def set_key_levels(self):
        self.weekly_pivots = get_pivot_points(get_prev_week_candle(self.asset, self.asset_book.market_book.trade_day))
        self.yday_profile = get_nth_day_profile_data(self.asset, self.asset_book.market_book.trade_day, 1).to_dict('records')[0]
        self.day_before_profile = get_nth_day_profile_data(self.asset, self.asset_book.market_book.trade_day, 2).to_dict('records')[0]
        self.intraday_waves = {}
        prev_key_levels = get_prev_day_key_levels(self.asset, self.asset_book.market_book.trade_day)

        range_to_watch = [self.yday_profile['low'] * 0.97, self.yday_profile['high'] * 1.03]
        existing_supports = json.loads(prev_key_levels[1])
        existing_resistances = json.loads(prev_key_levels[2])
        self.supports_to_watch = [x for x in existing_supports if (x >= range_to_watch[0]) and (x <= range_to_watch[1])]
        self.resistances_to_watch = [x for x in existing_resistances if (x >= range_to_watch[0]) and (x <= range_to_watch[1])]

    def update_periodic(self):
        self.intraday_trend.calculate_measures()
        self.activity_log.update_periodic()

    def get_prior_wave(self, epoch_minute=None):
        all_waves_end_time = list(self.intraday_waves.keys())
        all_waves_end_time.sort()
        wave_idx = profile_utils.get_next_lowest_index(all_waves_end_time, epoch_minute) if epoch_minute else -1
        return self.intraday_waves[all_waves_end_time[wave_idx]]

    def get_prev_sph(self):
        last_wave = self.get_prior_wave()
        #return {'level': max(last_wave['start'], last_wave['end'])}
        return max(last_wave['start'], last_wave['end'])

    def get_prev_spl(self):
        last_wave = self.get_prior_wave()
        #return {'level': min(last_wave['start'], last_wave['end'])}
        return min(last_wave['start'], last_wave['end'])

    def get_n_candle_body_target_up(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else self.candle_1_processor if period == 1 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        body = big_candle['high'] - big_candle['low']
        return big_candle['high'] + body

    def get_n_candle_body_target_down(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else self.candle_1_processor if period == 1 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        body = big_candle['high'] - big_candle['low']
        return big_candle['low'] - body

    def get_last_n_candle_high(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else self.candle_1_processor if period == 1 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        return big_candle['high']

    def get_last_n_candle_low(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else self.candle_1_processor if period == 1 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        return big_candle['low']

    def get_sma(self, period=5):
        price_list = list(self.market_data.values())
        close = np.array([x['high'] for x in price_list])
        output = stream.SMA(close, timeperiod=period)
        return output

    def get_inflex_pattern_df(self, period=None):
        return self.inflex_detector

    def set_transition_matrix(self):
        self.state_generator = DayFullStateGenerator(self.asset, self.asset_book.market_book.trade_day, self.yday_profile)
        try:
            f = open(cache_dir + 'full_state_' + self.asset + '.json')
            data = json.load(f)
            self.transition_data = MCPreprocessor().get_processed_data(data, symbol=self.asset, start_tpo=1, end_tpo=None)
            self.mc.from_data(self.transition_data, "unique_transitions_fill_break")
            self.state_prob_calculator = EmpiricalDistribution(self.transition_data,"unique_transitions_fill_break")
        except Exception as e:
            print('Exception in set_transition_matrix')
            print(e)

    def update_state_transition(self):
        last_state = self.state_generator.curr_state
        if last_state == '':
            self.state_generator.set_open_type(self.spot_processor.last_tick)
        self.state_generator.update_state(self.spot_processor.last_tick['close'])
        features = self.state_generator.get_features()
        #print(features)
        if last_state == '':
            open_type = features['open_type']
            probs = self.mc.get_prob_from_curr_state(open_type)
            #print(probs)
            #self.pattern_signal('STATE', {'signal': 'open_type', 'params': {'open_type':open_type, 'probs': probs}, 'strength':0})
            pat = Signal(asset=self.asset, category="STATE", instrument="", indicator="open_type", signal=open_type,
                   signal_time=self.spot_processor.last_tick['timestamp'], notice_time=self.spot_processor.last_tick['timestamp'],
                   info={'probs': probs}, strength=0)
            self.pattern_signal(pat)

    def spot_minute_data_stream(self, price, iv=None):
        #print('Spot book of==', self.asset, " received price input===", price)
        epoch_tick_time = price['timestamp']
        epoch_minute = TradeDateTime.get_epoc_minute(epoch_tick_time)
        key_list = ['timestamp','open', 'high', "low", "close"]
        feed_small = {key: price[key] for key in key_list}
        self.spot_processor.process_minute_data(price)
        #self.activity_log.update_last_candle()
        #self.activity_log.determine_level_break(epoch_tick_time)
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
        if price['timestamp'] - self.last_periodic_update > self.periodic_update_sec:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        #self.inflex_detector.on_price_update([price['timestamp'], price['close']])
        #self.trend_detector.evaluate()
        self.candle_5_processor.create_candles()
        self.candle_15_processor.create_candles()
        self.candle_1_processor.create_candles()
        for pattern_detector in self.price_action_pattern_detectors:
            pattern_detector.evaluate()
        for candle_detector in self.candle_pattern_detectors:
            candle_detector.evaluate()
        self.spot_processor.process_spot_signals()
        #self.activity_log.process()

    def pattern_signal(self, signal: BaseSignal):
        #print(type(signal))
        #print(signal.category)
        if signal.is_option_signal():
            #print('pattern_signal+++++++++++', signal)
            pass
        self.activity_log.register_signal(signal)
        if signal.is_trend_signal():
            #print('TREND+++++', signal)
            self.activity_log.update_sp_trend(signal.info['trend'])
            for wave in signal.info['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
        self.asset_book.market_book.pattern_signal(signal)


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
        self.pm = None
        self.profile_processor = None
        self.state_generator = None
        self.transition_data = {}
        self.mc = None
        self.state_prob_calculator = None
