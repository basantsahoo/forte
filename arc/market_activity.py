from research.strategies.core_strategy import BaseStrategy
from helper.utils import pattern_param_match, get_broker_order_type, get_overlap
from statistics import mean
import math
from db.market_data import get_candle_body_size
from helper.utils import get_overlap, compare_day_activity
import helper.utils as helper_utils

class MarketActivity:
    def __init__(self, insight_book):
        self.insight_book = insight_book
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


    def process(self):
        price_list = list(self.insight_book.spot_processor.spot_ts.values())
        if len(price_list) < 2:
            return
        #print('process++++++')
        #print(self.insight_book.yday_profile)

    def set_up(self):
        self.determine_day_open()
        #self.candle_stats = get_candle_body_size(self.insight_book.ticker, self.insight_book.trade_day)
        self.t_minus_1 = {'high':self.insight_book.yday_profile['high'], 'va_h_p':self.insight_book.yday_profile['va_h_p'],'poc_price':self.insight_book.yday_profile['poc_price'], 'va_l_p':self.insight_book.yday_profile['va_l_p'], 'low':self.insight_book.yday_profile['low'], 'open':self.insight_book.yday_profile['open'], 'close':self.insight_book.yday_profile['close']}
        self.t_minus_2 = {'high': self.insight_book.day_before_profile['high'],
                          'va_h_p': self.insight_book.day_before_profile['va_h_p'],
                          'poc_price': self.insight_book.day_before_profile['poc_price'],
                          'va_l_p': self.insight_book.day_before_profile['va_l_p'],
                          'low': self.insight_book.day_before_profile['low'],
                          'open': self.insight_book.day_before_profile['open'],
                          'close': self.insight_book.day_before_profile['close']}
        self.open_type = self.insight_book.state_generator.get_features()['open_type']
        self.hist_2d_activity = compare_day_activity(self.t_minus_1, self.t_minus_2)

        """
        self.daily_trend = round((self.t_minus_1['poc_price'] / self.t_minus_2['poc_price'] - 1)*100, 2)
        new_teritory = 1 - round(get_overlap([self.t_minus_1['low'], self.t_minus_1['high']], [self.t_minus_2['low'],self.t_minus_2['high']])/(self.t_minus_1['high']-self.t_minus_1['low']), 2)
        retest = round(get_overlap([self.t_minus_2['low'], self.t_minus_2['high']], [self.t_minus_1['low'], self.t_minus_1['high']]) / (self.t_minus_2['high'] - self.t_minus_2['low']), 2)
        print(self.open_type)
        print(self.daily_trend)
        print(advance)
        print(retest)
        """
    def determine_day_open(self): ## this is definitive
        open_candle = next(iter(self.insight_book.spot_processor.spot_ts.items()))[1]
        open_low = open_candle['open']
        open_high = open_candle['open']
        if open_low >= self.insight_book.yday_profile['high']:
            self.open_type = 'GAP_UP'
        elif open_high <= self.insight_book.yday_profile['low']:
            self.open_type = 'GAP_DOWN'
        elif open_low >= self.insight_book.yday_profile['va_h_p']:
            self.open_type = 'ABOVE_VA'
        elif open_high <= self.insight_book.yday_profile['va_l_p']:
            self.open_type = 'BELOW_VA'
        else:
            self.open_type = 'INSIDE_VA'

    def determine_level_break(self, ts):
        for k in self.yday_level_breaks:
            if not self.yday_level_breaks[k]['value']:
                level_range = [self.insight_book.yday_profile[k] * (1 - 0.0015), self.insight_book.yday_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.yday_level_breaks[k]['value'] = True
                    self.yday_level_breaks[k]['time'] = ts-self.insight_book.ib_periods[0]
        for k in self.day_before_level_breaks:
            if not self.day_before_level_breaks[k]['value']:
                level_range = [self.insight_book.day_before_profile[k] * (1 - 0.0015), self.insight_book.day_before_profile[k] * (1 + 0.0015)]
                ol = get_overlap(level_range, [self.range['low'], self.range['high']])
                if ol > 0:
                    self.day_before_level_breaks[k]['value'] = True
                    self.day_before_level_breaks[k]['time'] = ts-self.insight_book.ib_periods[0]

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
        for support in self.insight_book.supports_to_watch:
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
        for resistance in self.insight_book.resistances_to_watch:
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
        self.trend_features = {**self.trend_features, **self.insight_book.intraday_trend.trend_params}

    def update_sp_trend(self,trend):
        #print('update_sp_trend======',trend)
        self.spx_features = trend


    def locate_price_region(self, mins=15):
        ticks = list(self.insight_book.spot_processor.spot_ts.values())[-mins::]
        candle = {'open': ticks[0]['open'], 'high': max([y['high'] for y in ticks]), 'low': min([y['low'] for y in ticks]), 'close': ticks[-1]['close']}
        #print('locate_price_region', candle)
        return self.candle_position_wrt_key_levels(candle)

    def candle_position_wrt_key_levels(self, candle):
        resp = {}
        yday_profile = {k: v for k, v in self.insight_book.yday_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p', 'poc_price')}
        for (lvl, price) in yday_profile.items():
            resp['y_' + lvl] = self.check_level(candle, price)
        t_2_profile = {k: v for k, v in self.insight_book.day_before_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p', 'poc_price')}
        for (lvl, price) in t_2_profile.items():
            resp['t_2_' + lvl] = self.check_level(candle, price)
        weekly_profile = {k: v for k, v in self.insight_book.weekly_pivots.items() if k not in ('open', 'close')}
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


        last_candle = self.insight_book.spot_processor.last_tick
        self.range['low'] = min(last_candle['low'], self.range['low'])
        self.range['high'] = max(last_candle['high'], self.range['high'])

        next_level = round(last_candle['close'] / 100, 0) * 100
        self.lc_features['lc_dist_frm_level'] = last_candle['close'] - next_level
        self.lc_features['lc_resistance_ind'] = self.check_resistance(last_candle)
        self.lc_features['lc_support_ind'] = self.check_support(last_candle)
        candle_pos = self.candle_position_wrt_key_levels(last_candle)
        for key, val in candle_pos.items():
            self.lc_features['lc_'+ key] = val

    def get_market_params(self):
        mkt_parms = {}
        mkt_parms['open_type'] = self.open_type
        mkt_parms['tpo'] = self.insight_book.curr_tpo
        mkt_parms['spot'] = self.insight_book.spot_processor.last_tick['close']
        mkt_parms['candles_in_range'] = round(self.insight_book.intraday_trend.candles_in_range, 2)
        mkt_parms = {**mkt_parms, **self.trend_features}
        mkt_parms = {**mkt_parms, **self.lc_features}
        mkt_parms = {**mkt_parms, **self.get_day_features()}
        for (k,v) in self.hist_2d_activity.items():
            mkt_parms['d2_'+k] = v
        mkt_parms = {**mkt_parms, **self.spx_features}
        return mkt_parms

