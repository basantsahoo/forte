from datetime import datetime
from db.market_data import get_prev_week_consolidated_minute_data_by_start_day, get_curr_week_consolidated_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from helper.utils import determine_day_open, determine_level_reach
from entities.trading_day import TradeDateTime, NearExpiryWeek
import time


class WeeklyProcessor:
    def __init__(self, spot_book, time_period):
        self.ticker = spot_book.asset_book.asset
        self.spot_book = spot_book
        self.trade_day = None
        self.last_tick = {}
        self.first_tick_of_week = {}
        self.last_week_metric = {}
        self.week_open_type = None
        self.expiry_date = None
        self.curr_week_metric = {
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
        self.current_week_processor = WeeklyMarketProfileService(time_period = time_period)
        print('WeeklyProcessor time_period ===', time_period)
    def day_change_notification(self, trade_day):
        self.set_up(trade_day)

    def frame_change_action(self, current_frame, next_frame):
        self.current_week_processor.frame_change_action(current_frame, next_frame)
        #self.generate_signal()

    def set_up(self, trade_day):
        self.trade_day = trade_day
        df_prev = get_prev_week_consolidated_minute_data_by_start_day(self.ticker, self.trade_day, week_start_day="Friday", start_time="9:15:00")
        df_prev['symbol'] = self.ticker
        df_prev['ltp'] = df_prev['close']
        last_week_recs = df_prev.to_dict('records')
        lw_processor = WeeklyMarketProfileService()
        lw_processor.set_trade_date_from_time(last_week_recs[0]['timestamp'], last_week_recs[-1]['timestamp'])
        lw_processor.process_hist_data(last_week_recs)
        lw_processor.calculateProfile()
        processed_data = lw_processor.market_profile
        self.last_week_metric = {
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
            'h_a_l': processed_data['h_a_l'],
            'ext_low': processed_data['profile_dist']['ext_low'],
            'ext_high': processed_data['profile_dist']['ext_high'],
            'low_ext_val': processed_data['profile_dist']['low_ext_val'],
            'high_ext_val': processed_data['profile_dist']['high_ext_val'],
        }
        t_day = TradeDateTime(trade_day)
        expiry_week = NearExpiryWeek(t_day, self.ticker)
        self.expiry_date = expiry_week.end_date.date_time
        df = get_curr_week_consolidated_minute_data_by_start_day(self.ticker, self.trade_day, week_start_day="Friday", start_time="9:15:00", full_week=False)
        df['symbol'] = self.ticker
        df['ltp'] = df['close']
        curr_week_recs = df.to_dict('records')

        if curr_week_recs:
            first_tick_of_week = curr_week_recs[0]['timestamp']
        else:
            first_tick_of_week = t_day.market_start_epoc

        last_tick_of_week = t_day.market_end_epoc
        self.current_week_processor.set_trade_date_from_time(first_tick_of_week, last_tick_of_week)
        self.current_week_processor.spot_book = self.spot_book
        print('start day ====', datetime.fromtimestamp(first_tick_of_week))

    def generate_signal(self):
        print('WeeklyProcessor==== generate_signal')

    def process_minute_data(self, minute_data, notify=True):
        if not self.first_tick_of_week:
            self.first_tick_of_week = minute_data

        if self.week_open_type is None:
            self.set_week_open()
        lk_keys = ['open', 'high', 'low', 'close', 'poc_price', 'va_l_p', 'va_l_poc_mid', 'va_l_low_mid', 'va_h_poc_mid', 'va_h_high_mid', 'va_h_p', 'balance_target']
        for l_key in lk_keys:
            level = self.last_week_metric[l_key]
            level_reach = determine_level_reach(level, minute_data)
            if level_reach:
                self.curr_week_metric[l_key] += 1
                pat = {'category': 'WEEKLY_LEVEL_REACH', 'indicator': l_key, 'strength': 1,
                       'signal_time': minute_data['timestamp'], 'notice_time': minute_data['timestamp'],
                       'info': minute_data}
                self.spot_book.asset_book.pattern_signal(pat)

    def set_week_open(self):
        self.week_open_type = determine_day_open(self.first_tick_of_week, self.last_week_metrices)
        pat = {'category': 'STATE', 'indicator': 'w_open', 'strength': 1,
               'signal_time': self.first_tick_of_week['timestamp'], 'notice_time': self.first_tick_of_week['timestamp'],
               'info': self.first_tick_of_week}
        self.spot_book.asset_book.pattern_signal(pat)

    def get_expiry_day_time(self, t_string):
        start_str = self.expiry_date + " " + t_string + " +0530"
        ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S %z")))  # - 5.5 * 3600
        return ts

    def get_market_params(self):
        mkt_parms = {}
        mkt_parms['week_open_type'] = self.week_open_type
        mkt_parms['tpo'] = 0
        return mkt_parms

