from collections import OrderedDict
from helper.utils import get_epoc_minute
from talipp.indicators import EMA, SMA, Stoch
from talipp.ohlcv import OHLCVFactory
from datetime import datetime
from db.market_data import get_prev_week_minute_data_by_start_day, get_curr_week_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from helper.utils import determine_day_open, determine_level_reach


class WeeklyProcessor:
    def __init__(self, insight_book, ticker):
        self.insight_book = insight_book
        self.ticker = ticker
        self.trade_day = None
        self.last_tick = {}
        self.first_tick_of_week = {}
        self.last_week_metrices = {}
        self.week_open_type = None
        self.curr_week_metrices = {
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0,
            'poc_price': 0,
            'va_l_p': 0,
            'va_l_poc_mid': 0,
            'va_l_low_mid': 0,
            'va_h_poc_mid': 0,
            'va_h_high_mid': 0,
            'va_h_p': 0,
            'balance_target': 0
        }

    def set_up(self, trade_day):
        self.trade_day = trade_day
        df = get_curr_week_minute_data_by_start_day(self.ticker, self.trade_day, week_start_day="Friday", start_time="9:15:00")
        df['symbol'] = self.ticker
        df['ltp'] = df['close']
        curr_week_recs = df.to_dict('records')
        print('start day ====', datetime.fromtimestamp(curr_week_recs[0]['timestamp']))
        df = get_prev_week_minute_data_by_start_day(self.ticker, self.trade_day, week_start_day="Friday", start_time="9:15:00")
        df['symbol'] = self.ticker
        df['ltp'] = df['close']
        last_week_recs = df.to_dict('records')
        processor = WeeklyMarketProfileService()
        processor.set_trade_date_from_time(last_week_recs[0]['timestamp'], last_week_recs[-1]['timestamp'])
        processor.process_input_data(last_week_recs)
        processor.calculateMeasures()
        processed_data = processor.get_profile_data()[0]
        self.last_week_metrices = {
            'open': processed_data['open'],
            'high': processed_data['high'],
            'low': processed_data['low'],
            'close': processed_data['close'],
            'poc_price': processed_data['poc_price'],
            'va_l_p': processed_data['value_area_price'][0],
            'va_h_p': processed_data['value_area_price'][1],
            'va_l_poc_mid': 0.5 * (processed_data['value_area_price'][0] + processed_data['poc_price']),
            'va_l_low_mid': 0.5 * (processed_data['value_area_price'][0] + processed_data['low']),
            'va_h_poc_mid': 0.5 * (processed_data['value_area_price'][1] + processed_data['poc_price']),
            'va_h_high_mid': 0.5 * (processed_data['value_area_price'][1] + processed_data['high']),
            'balance_target': processed_data['balance_target'],
            'h_a_l': processed_data['h_a_l'],
            'ext_low': processed_data['extremes']['ext_low'],
            'ext_high': processed_data['extremes']['ext_high'],
            'low_ext_val': processed_data['extremes']['low_ext_val'],
            'high_ext_val': processed_data['extremes']['high_ext_val'],
        }
        if curr_week_recs:
            self.first_tick_of_week = curr_week_recs[0]

    def process_minute_data(self, minute_data, notify=True):
        if not self.first_tick_of_week:
            self.first_tick_of_week = minute_data

        if self.week_open_type is None:
            self.set_week_open()
        lk_keys = ['open', 'high', 'low', 'close', 'poc_price', 'va_l_p', 'va_l_poc_mid', 'va_l_low_mid', 'va_h_poc_mid', 'va_h_high_mid', 'va_h_p', 'balance_target']
        for l_key in lk_keys:
            level = self.last_week_metrices[l_key]
            level_reach = determine_level_reach(level, minute_data)
            if level_reach:
                self.curr_week_metrices[l_key] += 1
                pat = {'category': 'WEEKLY_LEVEL_REACH', 'indicator': l_key, 'strength': 1,
                       'signal_time': minute_data['timestamp'], 'notice_time': minute_data['timestamp'],
                       'info': minute_data}
                self.insight_book.pattern_signal(pat)

    def set_week_open(self):
        self.week_open_type = determine_day_open(self.first_tick_of_week, self.last_week_metrices)
        pat = {'category': 'STATE', 'indicator': 'w_open', 'strength': 1,
               'signal_time': self.first_tick_of_week['timestamp'], 'notice_time': self.first_tick_of_week['timestamp'],
               'info': self.first_tick_of_week}
        self.insight_book.pattern_signal(pat)

    def get_market_params(self):
        mkt_parms = {}
        mkt_parms['week_open_type'] = self.week_open_type
        mkt_parms['tpo'] = 0
        return mkt_parms

