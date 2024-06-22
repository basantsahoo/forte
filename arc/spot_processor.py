from collections import OrderedDict
from helper.utils import get_overlap, compare_day_activity
import helper.utils as helper_utils
import json

from db.market_data import get_prev_week_candle, get_nth_day_profile_data, get_prev_day_key_levels, get_previous_n_day_profile_data
from helper.utils import get_pivot_points, convert_to_candle
from dynamics.trend.intraday_trend import IntradayTrendCalculator
from dynamics.patterns.trend_detector import TrendDetector
from entities.trading_day import TradeDateTime
from dynamics.patterns.daily_candle_pattern_detector import DailyCandlePatternDetector

class SpotFactorCalculator:
    def __init__(self, spot_book, asset):
        self.spot_book = spot_book
        self.asset_book = spot_book.asset_book
        self.asset = asset
        self.last_tick = {}
        self.spot_ts = OrderedDict()
        self.day_range = {'low': float('inf'), 'high': float('-inf')}

        self.trend_detector = TrendDetector(self, period=1)
        self.intraday_trend = IntradayTrendCalculator(self)
        self.daily_candle_pattern_detector = DailyCandlePatternDetector(spot_book)
        self.candle_stats = []
        self.hist_2d_activity = {}
        self.trend_features = {}
        self.spx_features = {}
        self.lc_features = {}
        self.open_type = None
        self.range = {'low': 99999999, 'high': 0}
        self.yday_level_breaks = {'high': {'value': False, 'time': -1}, 'low': {'value': False, 'time': -1}, 'poc_price': {'value': False, 'time': -1}, 'va_h_p': {'value': False, 'time': -1}, 'va_l_p': {'value': False, 'time': -1}}
        self.day_before_level_breaks = {'high': {'value': False, 'time': -1}, 'low': {'value': False, 'time': -1}, 'poc_price': {'value': False, 'time': -1}, 'va_h_p': {'value': False, 'time': -1}, 'va_l_p': {'value': False, 'time': -1}}
        self.weekly_level_breaks = {'high': {'value': False, 'time':-1}, 'low': {'value': False, 'time':-1}, 'Pivot': {'value': False, 'time':-1}, 'S1': {'value': False, 'time':-1}, 'S2': {'value': False, 'time':-1}, 'S3': {'value': False, 'time':-1}, 'S4': {'value': False, 'time':-1}, 'R1': {'value': False, 'time':-1}, 'R2': {'value': False, 'time':-1},  'R3': {'value': False, 'time':-1}, 'R4': {'value': False, 'time':-1}}
        self.weekly_pivots = []
        self.yday_profile = []
        self.day_before_profile = []
        self.intraday_waves = {}


    def day_change_notification(self, trade_day):
        self.set_key_levels()

    def set_key_levels(self):
        dt = get_previous_n_day_profile_data(self.asset, self.asset_book.market_book.trade_day, 7).to_dict('records')
        #print(dt)
        self.daily_candle_pattern_detector.candles = dt
        self.daily_candle_pattern_detector.detect()
        #print(self.daily_candle_pattern_detector.signal_dict)
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

    def frame_change_action(self, current_frame, next_frame):
            inst = self.spot_ts[current_frame]
            option_matrix = self.spot_book.asset_book.option_matrix
            put_volume, call_volume = option_matrix.get_ts_volume(self.spot_book.asset_book.market_book.trade_day, current_frame)
            total_volume = sum([put_volume, call_volume])/100000
            inst['volume'] = total_volume
            inst['asset'] = self.spot_book.asset_book.asset

    def process_minute_data(self, minute_data, notify=True):
        #print('spot process_minute_data+++++', datetime.fromtimestamp(minute_data['timestamp']))
        key_list = ['timestamp', 'open', 'high', "low", "close"]
        feed_small = {key: minute_data[key] for key in key_list}
        epoch_minute = TradeDateTime.get_epoc_minute(minute_data['timestamp'])
        self.spot_ts[epoch_minute] = feed_small
        self.last_tick = feed_small
        self.day_range['low'] = min(self.day_range['low'], feed_small['low'])
        self.day_range['high'] = max(self.day_range['high'], feed_small['high'])
        epoch_tick_time = minute_data['timestamp']
        epoch_minute = TradeDateTime.get_epoc_minute(epoch_tick_time)
        key_list = ['timestamp', 'open', 'high', "low", "close"]
        # self.activity_log.update_last_candle()
        # self.activity_log.determine_level_break(epoch_tick_time)
        self.spot_book.inflex_detector.on_price_update([minute_data['timestamp'], minute_data['close']])
        # self.trend_detector.evaluate()
        self.spot_book.candle_1_processor.create_candles()
        self.spot_book.candle_5_processor.create_candles()

        #self.spot_processor.process_spot_signals()

    def update_periodic(self):
        self.intraday_trend.calculate_measures()
        self.trend_features = {**self.trend_features, **self.intraday_trend.trend_params}


    def get_market_params(self):
        mkt_parms = {}
        mkt_parms['open_type'] = self.open_type
        mkt_parms['tpo'] = self.spot_book.asset_book.market_book.curr_tpo
        mkt_parms['spot'] = self.spot_book.spot_processor.last_tick['close']
        mkt_parms['candles_in_range'] = round(self.intraday_trend.candles_in_range, 2)
        from helper.utils import locate_point, locate_point_2

        pattern_df = self.spot_book.get_inflex_pattern_df().dfstock_3
        range = self.spot_book.spot_processor.day_range['high'] - self.spot_book.spot_processor.day_range['low']
        curr = self.spot_book.spot_processor.last_tick['close'] - self.spot_book.spot_processor.day_range['low']

        mkt_parms['price_location'] = curr/range * 100 #locate_point_2(pattern_df, self.spot_book.spot_processor.last_tick['close'])
        mkt_parms = {**mkt_parms, **self.trend_features}
        mkt_parms = {**mkt_parms, **self.lc_features}
        mkt_parms = {**mkt_parms, **self.get_day_features()}
        for (k,v) in self.hist_2d_activity.items():
            mkt_parms['d2_'+k] = v
        mkt_parms = {**mkt_parms, **self.spx_features}
        for (asset, category, indicator, period) in self.daily_candle_pattern_detector.signal_dict.keys():
            mkt_parms[indicator + "_" + period] = 1

        return mkt_parms

    def determine_day_open(self): ## this is definitive
        open_candle = next(iter(self.spot_book.spot_processor.spot_ts.items()))[1]
        open_low = open_candle['open']
        open_high = open_candle['open']
        if open_low >= self.spot_book.spot_processor.yday_profile['high']:
            self.open_type = 'GAP_UP'
        elif open_high <= self.spot_book.spot_processor.yday_profile['low']:
            self.open_type = 'GAP_DOWN'
        elif open_low >= self.spot_book.spot_processor.yday_profile['va_h_p']:
            self.open_type = 'ABOVE_VA'
        elif open_high <= self.spot_book.spot_processor.yday_profile['va_l_p']:
            self.open_type = 'BELOW_VA'
        else:
            self.open_type = 'INSIDE_VA'

    def determine_level_break(self, ts):
        for k in self.yday_level_breaks:
            if not self.yday_level_breaks[k]['value']:
                level_range = [self.spot_book.spot_processor.yday_profile[k] * (1 - 0.0015), self.spot_book.spot_processor.yday_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.yday_level_breaks[k]['value'] = True
                    self.yday_level_breaks[k]['time'] = ts-self.spot_book.spot_processor.market_book.ib_periods[0]
        for k in self.day_before_level_breaks:
            if not self.day_before_level_breaks[k]['value']:
                level_range = [self.spot_book.spot_processor.day_before_profile[k] * (1 - 0.0015), self.spot_book.spot_processor.day_before_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.day_before_level_breaks[k]['value'] = True
                    self.day_before_level_breaks[k]['time'] = ts-self.spot_book.spot_processor.market_book.ib_periods[0]

    def get_day_features(self):
        resp = {}
        for (lvl, item) in self.yday_level_breaks.items():
            resp['d_y_' + lvl] = int(item['value'])
        for (lvl, item) in self.day_before_level_breaks.items():
            resp['d_t_2_' + lvl] = int(item['value'])
        """
        for (lvl, item) in self.weekly_level_breaks.items():
            resp['d_w_' + lvl] = item['values']
        """
        return resp

    def check_support(self, candle):
        support_ind = 0
        for support in self.spot_book.spot_processor.supports_to_watch:
            support_range = [support-5, support+5]
            #candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
            candle_range = [candle['low'], candle['high']]
            ol = helper_utils.get_overlap(support_range, candle_range)
            if ol > 0:
                support_ind = 2 if support % 100 == 0 else 1
                break
        return support_ind

    def check_resistance(self, candle):
        resistance_ind = 0
        for resistance in self.spot_book.spot_processor.resistances_to_watch:
            resistance_range = [resistance-5, resistance+5]
            #candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
            candle_range = [candle['low'], candle['high']]
            ol = helper_utils.get_overlap(resistance_range, candle_range)
            if ol > 0:
                resistance_ind = 2 if resistance % 100 == 0 else 1
                break
        return resistance_ind

    def check_level(self, candle, level):
        ind = 0
        level_rng = [level - 10, level + 10]
        candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
        ol = helper_utils.get_overlap(level_rng, candle_range)
        if ol > 0:
            ind = 1
        return ind

    def update_periodic(self):
        self.trend_features = {**self.trend_features, **self.spot_book.intraday_trend.trend_params}

    def update_sp_trend(self,trend):
        #print('update_sp_trend======',trend)
        self.spx_features = trend


    def locate_price_region(self, mins=15):
        ticks = list(self.spot_book.spot_processor.spot_ts.values())[-mins::]
        candle = {'open': ticks[0]['open'], 'high': max([y['high'] for y in ticks]), 'low': min([y['low'] for y in ticks]), 'close': ticks[-1]['close']}
        #print('locate_price_region', candle)
        return self.candle_position_wrt_key_levels(candle)

    def candle_position_wrt_key_levels(self, candle):
        resp = {}
        yday_profile = {k: v for k, v in self.spot_book.spot_processor.yday_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p', 'poc_price')}
        for (lvl, price) in yday_profile.items():
            resp['y_' + lvl] = self.check_level(candle, price)
        t_2_profile = {k: v for k, v in self.spot_book.spot_processor.day_before_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p', 'poc_price')}
        for (lvl, price) in t_2_profile.items():
            resp['t_2_' + lvl] = self.check_level(candle, price)
        weekly_profile = {k: v for k, v in self.spot_book.spot_processor.weekly_pivots.items() if k not in ('open', 'close')}
        for (lvl, price) in weekly_profile.items():
            resp['w_' + lvl] = self.check_level(candle, price)
        return resp

    def register_signal(self, signal):
        pass

    def update_last_candle(self):
        self.lc_features = {}
        """
        self.lc_features['first_hour_trend'] = round(self.insight_book.intraday_trend.first_hour_trend,2)
        self.lc_features['whole_day_trend'] = round(self.insight_book.intraday_trend.whole_day_trend,2)
        self.lc_features['five_min_trend'] = round(self.insight_book.intraday_trend.five_min_trend,2)
        self.lc_features['fifteen_min_trend'] = round(self.insight_book.intraday_trend.fifteen_min_trend,2)
        self.lc_features['five_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.five_min_ex_first_hr_trend,2)
        self.lc_features['fifteen_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.fifteen_min_ex_first_hr_trend,2)
        self.lc_features['hurst_exp_15'] = round(self.insight_book.intraday_trend.hurst_exp_15,2)
        self.lc_features['hurst_exp_5'] = round(self.insight_book.intraday_trend.hurst_exp_5,2)
        self.lc_features['ret_trend'] = round(self.insight_book.intraday_trend.ret_trend,2)
        """


        last_candle = self.spot_book.spot_processor.last_tick
        self.range['low'] = min(last_candle['low'], self.range['low'])
        self.range['high'] = max(last_candle['high'], self.range['high'])

        next_level = round(last_candle['close'] / 100, 0) * 100
        self.lc_features['lc_dist_frm_level'] = last_candle['close'] - next_level
        self.lc_features['lc_resistance_ind'] = self.check_resistance(last_candle)
        self.lc_features['lc_support_ind'] = self.check_support(last_candle)
        candle_pos = self.candle_position_wrt_key_levels(last_candle)
        for key, val in candle_pos.items():
            self.lc_features['lc_'+ key] = val
