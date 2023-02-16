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
from arc.market_activity import MarketActivity
from arc.intraday_option_processor import IntradayOptionProcessor
from arc.spot_processor import SpotProcessor
from arc.candle_processor import CandleProcessor

class InsightBook:
    def __init__(self, ticker, trade_day=None, record_metric=True, candle_sw=0, insight_log=False):
        self.spot_processor = SpotProcessor(self, ticker)
        self.option_processor = IntradayOptionProcessor(self, ticker)
        self.candle_5_processor = CandleProcessor(self, 5, 0)
        self.candle_15_processor = CandleProcessor(self, 15, 0)
        # self.candle_5_processor.on_new_candle = self.on_new_5_min_candle
        #self.candle_15_processor.on_new_candle = self.on_new_15_min_candle
        #self.candle_5_queue = []
        #self.candle_15_queue = []
        self.trend = {}
        self.activity_log = MarketActivity(self)
        self.inflex_detector = PriceInflexDetectorForTrend(ticker, fpth=0.001, spth = 0.001,  callback=None)
        self.price_action_pattern_detectors = [PriceActionPatternDetector(self, period=1)]
        self.candle_pattern_detectors = [CandlePatternDetector(self, period=5, sliding_window=candle_sw), CandlePatternDetector(self, period=15, sliding_window=candle_sw)]
        self.trend_detector = TrendDetector(self, period=1)
        self.intraday_trend = IntradayTrendCalculator(self)
        self.day_setup_done = False
        self.range = {'low': 99999999, 'high': 0}
        self.trade_day = trade_day
        #self.market_data = OrderedDict()
        self.pm = None
        self.profile_processor = None
        self.strategies = []
        self.ticker = ticker
        self.record_metric = record_metric
        self.log_enabled = insight_log
        self.run_aggregator=False
        self.curr_tpo = None
        #self.last_tick = None
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
    """
    def on_new_5_min_candle(self, candle, notify):
        self.candle_5_queue.append(candle)

    def on_new_15_min_candle(self, candle, notify):
        self.candle_15_queue.append(candle)
    """
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
        self.market_start_ts = start_ts
        self.market_close_ts = end_ts
        self.tpo_brackets = np.arange(start_ts, end_ts, 1800)
        #self.set_key_levels()

    def set_key_levels(self):
        ticker = self.ticker
        self.weekly_pivots = get_pivot_points(get_prev_week_candle(ticker, self.trade_day))
        self.yday_profile = get_nth_day_profile_data(ticker, self.trade_day, 1).to_dict('records')[0]
        self.day_before_profile = get_nth_day_profile_data(ticker, self.trade_day, 2).to_dict('records')[0]
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
            f = open(cache_dir + 'full_state_' + self.ticker + '.json')
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
        print('remove_strategy', len(self.strategies))
        for strategy in self.strategies:
            if strategy.id == strategy_to_remove.id:
                #strategy.insight_book = None
                self.strategies.remove(strategy)
                break
        print('remove_strategy', len(self.strategies))

    def update_periodic(self):
        #print('update periodic')
        self.intraday_trend.calculate_measures()
        self.activity_log.update_periodic()
        #print('self.intraday_trend.trend_params', self.intraday_trend.trend_params)

    def set_up_strategies(self):
        self.activity_log.set_up()
        for strategy in self.strategies:
            strategy.set_up()

    def hist_spot_feed(self, hist_feed):
        print('hist_feed_input++++++++++++', len(hist_feed))
        for price in hist_feed:
            epoch_tick_time = price['timestamp']
            epoch_minute = int(epoch_tick_time // 60 * 60) + 1
            key_list = ['timestamp', 'open', 'high', "low", "close"]
            feed_small = {key: price[key] for key in key_list}
            if not self.day_setup_done:
                self.set_trade_date_from_time(epoch_tick_time)
            #self.market_data[epoch_minute] = feed_small
            self.spot_processor.process_minute_data(price)
        #self.last_tick = feed_small
        self.set_curr_tpo(epoch_minute)
        self.update_state_transition()
        self.activity_log.update_last_candle()
        self.activity_log.determine_level_break(epoch_tick_time)
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        self.set_up_strategies()
        self.candle_5_processor.create_candles()
        self.candle_15_processor.create_candles()
        for candle_detector in self.candle_pattern_detectors:
            candle_detector.evaluate(notify=False)
        self.spot_processor.process_spot_signals(notify=False)

    def spot_minute_data_stream(self, price, iv=None):
        #print('insight price_input_stream++++++++++++++++++++++++++++++++++++ insight book')
        epoch_tick_time = price['timestamp']
        epoch_minute = int(epoch_tick_time // 60 * 60) + 1
        key_list = ['timestamp','open', 'high', "low", "close"]
        feed_small = {key: price[key] for key in key_list}
        #self.last_tick = feed_small
        #print(epoch_tick_time)
        if not self.day_setup_done:
            self.set_trade_date_from_time(epoch_tick_time)
        #self.market_data[epoch_minute] = feed_small
        self.spot_processor.process_minute_data(price)
        self.set_curr_tpo(epoch_minute)
        for strategy in self.strategies:
            strategy.on_minute_data_pre()
        self.update_state_transition()
        if len(self.spot_processor.spot_ts.items()): #== 2 : #and self.open_type is None:
            #self.activity_log.determine_day_open()
            self.set_up_strategies()
        self.activity_log.update_last_candle()
        self.activity_log.determine_level_break(epoch_tick_time)
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
        if price['timestamp'] - self.last_periodic_update > self.periodic_update_sec:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        self.inflex_detector.on_price_update([price['timestamp'], price['close']])
        #print('input price', [price['timestamp'], price['close']])

        self.trend_detector.evaluate()
        self.candle_5_processor.create_candles()
        self.candle_15_processor.create_candles()
        for pattern_detector in self.price_action_pattern_detectors:
            #print('pattern_detector.evaluate')
            pattern_detector.evaluate()
        for candle_detector in self.candle_pattern_detectors:
            #print('candle patterns=====')
            candle_detector.evaluate()
        self.spot_processor.process_spot_signals()
        #self.activity_log.process()

        for strategy in self.strategies:
            strategy.process_custom_signal()
            strategy.on_minute_data_post()

    def option_minute_data_stream(self, option_data):
        #print('option price_input_stream+++++++++++++++++++++++++++++++++++++++++++++++++++++++++ insight book')
        epoch_tick_time = option_data['timestamp']
        if not self.day_setup_done:
            self.set_trade_date_from_time(epoch_tick_time)
        self.option_processor.process_input_stream(option_data)

    def hist_option_feed(self, hist_feed):
        for option_data in hist_feed:
            self.option_processor.process_input_stream(option_data, notify=False)

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
            pat = {'category': 'STATE', 'indicator': 'open_type', 'signal': open_type, 'strength':0, 'signal_time': self.spot_processor.last_tick['timestamp'], 'notice_time': self.spot_processor.last_tick['timestamp'], 'info': {'probs': probs}}
            self.pattern_signal(pat)

    def pattern_signal(self, signal):
        #print(signal['category'])
        if signal['category'] == 'OPTION':
            print('pattern_signal+++++++++++', signal)
            pass
        self.activity_log.register_signal(signal)
        if signal['indicator'] == INDICATOR_TREND:
            #print('TREND+++++', signal)
            self.activity_log.update_sp_trend(signal['info']['trend'])
            for wave in signal['info']['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
        for strategy in self.strategies:
            strategy.register_signal(signal)

        """
        if pattern == 'OPTION_PRICE_DROP':
            print('pattern_signal+++++++', pattern, pattern_match_idx)
        """
        """
        if pattern == 'DT':
            print('pattern_signal+++++++', pattern, pattern_match_idx)
        """
        """
        if pattern == 'TREND':
            #print('TREND+++++', pattern, pattern_match_idx)
            self.activity_log.update_sp_trend(pattern_match_idx['trend'])
            for wave in pattern_match_idx['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
            #print(self.intraday_waves)
        """
        """
        for strategy in self.strategies:
            strategy.register_signal(pattern, pattern_match_idx)
            #strategy.process_signal(pattern, pattern_match_idx)
        """
        if self.pm.data_interface is not None:
            self.pm.data_interface.notify_pattern_signal(self.ticker, signal)

        #print('self.intraday_trend')


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
        self.strategies = []
        self.state_generator = None
        self.transition_data = {}
        self.mc = None
        self.state_prob_calculator = None


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
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        body = big_candle['high'] - big_candle['low']
        return big_candle['high'] + body

    def get_n_candle_body_target_down(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        body = big_candle['high'] - big_candle['low']
        return big_candle['low'] - body

    def get_last_n_candle_high(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        return big_candle['high']

    def get_last_n_candle_low(self, period=5, n=1):
        candle_processor = self.candle_5_processor if period == 5 else self.candle_15_processor if period == 15 else None
        small_candles = candle_processor.get_last_n_candles(n)
        big_candle = convert_to_candle(small_candles)
        return big_candle['low']

    def set_curr_tpo(self, epoch_minute):
        ts_idx = profile_utils.get_next_lowest_index(self.tpo_brackets, epoch_minute)
        ts_idx = 13 if ts_idx < 0 else ts_idx + 1
        self.curr_tpo = ts_idx

    def get_sma(self, period=5):
        price_list = list(self.market_data.values())
        close = np.array([x['high'] for x in price_list])
        output = stream.SMA(close, timeperiod=period)
        return output

    def get_inflex_pattern_df(self, period=None):
        return self.inflex_detector

    def get_time_to_close(self):
        #print('market_close_ts=====', datetime.fromtimestamp(self.market_close_ts))
        return (self.market_close_ts - self.spot_processor.last_tick['timestamp']) / 60 #-1 # - 1 is done as hack

    def get_time_since_market_open(self):
        return (self.spot_processor.last_tick['timestamp'] - self.market_start_ts) / 60
