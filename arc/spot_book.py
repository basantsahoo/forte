import numpy as np
import json
from talib import stream

from db.market_data import get_prev_week_candle, get_nth_day_profile_data, get_prev_day_key_levels
from helper.utils import get_pivot_points, convert_to_candle
from dynamics.profile import utils as profile_utils
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
from arc.candle_processor import CandleProcessor
from entities.base import Signal
from entities.trading_day import TradeDateTime

from arc.spot_processor import SpotFactorCalculator
from arc.spot_signal_generator import SpotSignalGenerator
from arc.volume_profile import VolumeProfileService

class SpotBook:
    def __init__(self, asset_book, asset):
        self.asset_book = asset_book
        self.asset = asset
        self.spot_processor = SpotFactorCalculator(self, asset)
        self.signal_generator = SpotSignalGenerator(self, asset)
        self.candle_1_processor = CandleProcessor(self, 1, 0)
        self.candle_5_processor = CandleProcessor(self, 5, 0)
        #self.candle_15_processor = CandleProcessor(self, 15, 0)
        self.state_generator = None
        self.trend = {}
        #self.activity_log = AssetActivityLog(self)
        self.inflex_detector = PriceInflexDetectorForTrend(asset, fpth=0.001, spth = 0.001,  callback=None)
        self.trend_detector = TrendDetector(self, period=1)
        self.intraday_trend = IntradayTrendCalculator(self)
        self.day_setup_done = False
        self.mc = MarkovChainSecondLevel()
        self.last_periodic_update = None
        self.periodic_update_sec = 60
        self.volume_profile = VolumeProfileService()
        self.volume_profile.spot_book = self

    def update_periodic(self):
        self.spot_processor.update_periodic()

    def feed_stream_1(self, feed_list):
        for feed in feed_list:
            #print(feed)
            self.spot_processor.process_minute_data(feed)
            #self.market_profile.process_input_data(feed)


    def frame_change_action(self, current_frame, next_frame):
        self.spot_processor.frame_change_action(current_frame, next_frame)
        self.volume_profile.frame_change_action(current_frame, next_frame)
        self.signal_generator.generate_signals()

    def subscribe_to_clock(self, clock):
        clock.subscribe_to_frame_change(self.frame_change_action)

    def day_change_notification(self, trade_day):
        self.spot_processor.day_change_notification(trade_day)

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


    def pattern_signal(self, signal:Signal):
        #print(signal.category)
        if signal.is_option_signal():
            #print('pattern_signal+++++++++++', signal)
            pass
        if signal.is_trend_signal():
            #print('TREND+++++', signal)
            self.spot_processor.update_sp_trend(signal.signal_info['trend'])
            for wave in signal.signal_info['all_waves']:
                self.spot_processor.intraday_waves[wave['wave_end_time']] = wave
        self.asset_book.pattern_signal(signal)



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
