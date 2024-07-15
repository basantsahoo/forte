from datetime import datetime
import numpy as np
import time
from itertools import compress
from dynamics.profile import utils
from config import va_pct


class WeeklyMarketProfileService:
    def __init__(self, trade_day=None, time_period=1):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = 2
        self.waiting_for_data = False
        self.spot_book = None
        self.last_ts = None
        self.time_period = time_period * 60
        self.tpo_brackets = []
        self.tpo_letters = []
        self.hist_data = {}
        self.recent_hist_data = {}
        self.reset_pb = True
        self.tick_size = 0
        self.price_bins = []
        self.print_matrix = [[]]
        self.volume_print_matrix = [[]]
        self.last_intraday_ts = 0
        self.market_profile = {}
        self.volume_profile = {}


    def frame_change_action(self, current_frame, next_frame):
        if self.last_ts is None or current_frame - self.last_ts >= self.time_period:
            if self.spot_book is not None:
                lst = [minute_data for minute, minute_data in self.spot_book.spot_processor.spot_ts.items() if (self.last_ts is None or minute > self.last_ts)]
                self.process_input_data(lst)
                self.calculateMeasures()
            self.last_ts = current_frame

    def set_trade_date_from_time(self, s_epoch_tick_time, e_epoch_tick_time):
        #print(s_epoch_tick_time, e_epoch_tick_time)
        tick_date_time = datetime.fromtimestamp(s_epoch_tick_time)
        trade_day = tick_date_time.strftime('%Y-%m-%d')
        self.trade_day = trade_day
        self.tpo_brackets = np.arange(s_epoch_tick_time, e_epoch_tick_time, 3600)
        self.tpo_letters = []
        for slab in self.tpo_brackets:
            cal_date = datetime.fromtimestamp(slab)
            week_day = ['M','T','W','G','F','S', 'Su'][cal_date.weekday()] #cal_date.strftime('%A')[0:2]
            cal_date_str = cal_date.strftime('%Y-%m-%d')
            start_str = cal_date_str + " 09:15:00 +0530"
            market_start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S %z"))) #- 5.5 * 3600
            hr = (slab - market_start_ts) // 3600 + 1
            self.tpo_letters.append(week_day + str(int(hr)))

    def process_hist_data(self, lst):
        for inst in lst:
            epoch_tick_time = inst['timestamp']
            epoch_minute = int(epoch_tick_time // 60 * 60)
            minute_candle = {
                'open': inst['open'],
                'high': inst['high'],
                'low': inst['low'],
                'close': inst['close'],
                'volume': inst['volume'],
            }
            self.hist_data[epoch_minute] = minute_candle
        self.process_input_data(lst)

    def process_input_data(self, lst):
        for inst in lst:
            first = False
            if not self.price_data:
                self.tick_size = utils.get_tick_size(inst['high']) * 5
                first = True
            minute_candle = {
                'open': inst['open'],
                'high': inst['high'],
                'low': inst['low'],
                'close': inst['close'],
                'volume': inst['volume'],
                'lt': inst['timestamp'],
                'ht': inst['timestamp']
            }
            if first:
                self.price_data.update(minute_candle)
            else:
                #print('self.price_data===', self.price_data)
                if minute_candle['high'] > self.price_data['high']:
                    self.price_data['high'] = minute_candle['high']
                    self.price_data['ht'] = minute_candle['ht']
                    self.reset_pb = True
                if minute_candle['low'] < self.price_data['low']:
                    self.price_data['low'] = minute_candle['low']
                    self.price_data['lt'] = minute_candle['lt']
                    self.reset_pb = True
                self.price_data['close'] = minute_candle['close']
                self.price_data['volume'] = self.price_data['volume'] + minute_candle['volume']


    def calculateMeasures(self):
        if not self.waiting_for_data:
            if self.reset_pb:
                self.reset_pb = False
                self.price_bins = np.arange(np.floor(self.tick_size * np.floor(self.price_data['low']/self.tick_size)), np.ceil(self.tick_size * np.ceil(self.price_data['high']/self.tick_size)) + self.tick_size, self.tick_size)
                self.print_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(self.price_bins))))
                self.volume_print_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(self.price_bins))))
                for minute, minute_data in self.hist_data.items():
                    ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)
                    pb_idx_low = utils.get_next_lowest_index(self.price_bins, minute_data['low'])
                    pb_idx_high = utils.get_next_highest_index(self.price_bins, minute_data['high'])
                    for idx in range(pb_idx_low, pb_idx_high+1):
                        self.print_matrix[ts_idx, idx] = 1
            if self.spot_book is not None:
                for minute, minute_data in self.spot_book.spot_processor.spot_ts.items():
                    if minute > self.last_intraday_ts:
                        self.last_intraday_ts = minute
                        ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)
                        pb_idx_low = utils.get_next_lowest_index(self.price_bins, minute_data['low'])
                        pb_idx_high = utils.get_next_highest_index(self.price_bins, minute_data['high'])
                        for idx in range(pb_idx_low, pb_idx_high + 1):
                            self.print_matrix[ts_idx, idx] = 1
                            self.volume_print_matrix[ts_idx, idx] = self.volume_print_matrix[ts_idx, idx] + minute_data['volume']
            res_p = self.calculateStatistics(self.print_matrix)
            res_v = self.calculateStatistics(self.volume_print_matrix)
            self.market_profile = res_p
            self.volume_profile = res_v

    def calculateStatistics(self, print_matrix):
        tpo_sum_arr = np.sum(print_matrix, axis=0).A1
        #print(tpo_sum_arr)
        poc_idx = utils.mid_max_idx(tpo_sum_arr)
        poc_price = self.price_bins[poc_idx]

        #print(poc_price)
        #poc_len = tpo_sum_arr[poc_idx]
        #balance_target = utils.calculate_balanced_target(poc_price, sym['high'], sym['low'])
        value_area = utils.calculate_value_area(tpo_sum_arr, poc_idx, self.value_area_pct)
        total_val = np.sum(tpo_sum_arr)
        below_poc = round(np.sum(tpo_sum_arr[0:poc_idx])/total_val, 2)
        #print('below_poc=====', below_poc)
        try:
            above_poc = round(np.sum(tpo_sum_arr[poc_idx + 1::])/total_val,2)
        except:
            print(tpo_sum_arr)
            print(poc_idx)
        #print('above_poc=====', above_poc)
        res = {}
        res['open'] = self.price_data['open']
        res['high'] = self.price_data['high']
        res['low'] = self.price_data['low']
        res['close'] = self.price_data['close']
        res['poc_price'] = poc_price
        res['value_area_price'] = [self.price_bins[value_area[0]], self.price_bins[value_area[1]]]
        res['vah'] = max(res['value_area_price'])
        res['val'] = min(res['value_area_price'])
        res['below_poc'] = below_poc
        res['above_poc'] = above_poc
        res['h_a_l'] = self.price_data['ht'] > self.price_data['lt']
        profile_dist = utils.get_profile_dist(print_matrix, self.price_bins, self.min_co_ext)
        res['profile_dist'] = profile_dist
        return res
