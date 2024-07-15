
from datetime import datetime
import numpy as np
import time
from itertools import compress
from dynamics.profile import utils

from forte_config import va_pct, min_co_ext
from helper.utils import get_pivot_points
from entities.trading_day import TradeDateTime

class VolumeProfileService:
    def __init__(self, trade_day=None, time_period=1):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = min_co_ext
        self.waiting_for_data = True
        self.spot_book = None
        self.last_ts = None
        self.time_period = time_period * 60
        self.ib_periods = []
        self.tpo_brackets = []
        self.reset_pb = True
        self.tick_size = 0
        self.price_bins = []
        self.print_matrix = [[]]
        self.volume_print_matrix = [[]]
        self.last_intraday_ts = 0
        self.market_profile = {}
        self.volume_profile = {}


    def set_trade_date_from_time(self, epoch_tick_time):
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        trade_day = tick_date_time.strftime('%Y-%m-%d')
        self.trade_day = trade_day
        start_str = trade_day + " 09:15:00"
        ib_end_str = trade_day + " 10:15:00"
        end_str = trade_day + " 15:30:00"
        start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S")))
        ib_end_ts = int(time.mktime(time.strptime(ib_end_str, "%Y-%m-%d %H:%M:%S")))
        self.ib_periods = [start_ts, ib_end_ts]
        self.tpo_brackets = np.arange(start_ts, end_ts, 1800)

    def day_change_notification(self, trade_day):
        pass

    def day_setup(self, epoch_tick_time):
        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False

    def frame_change_action(self, current_frame, next_frame):
        self.day_setup(current_frame)
        if self.last_ts is None or current_frame - self.last_ts >= self.time_period:
            if self.spot_book is not None:
                lst = [minute_data for minute, minute_data in self.spot_book.spot_processor.spot_ts.items() if (self.last_ts is None or minute > self.last_ts)]
                self.process_input_data(lst)
                self.calculateProfile()
            self.last_ts = current_frame

    def process_input_data(self, lst):
        for inst in lst:
            first = False
            if not self.price_data:
                self.tick_size = utils.get_tick_size(inst['high'])
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

    def calculateProfile(self):
        if not self.waiting_for_data:
            if self.reset_pb:
                self.reset_pb = False
                self.price_bins = np.arange(np.floor(self.tick_size * np.floor(self.price_data['low']/self.tick_size)), np.ceil(self.tick_size * np.ceil(self.price_data['high']/self.tick_size)) + self.tick_size, self.tick_size)
                self.print_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(self.price_bins))))
                self.volume_print_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(self.price_bins))))
            if self.spot_book is not None:
                ib_data = []
                for minute, minute_data in self.spot_book.spot_processor.spot_ts.items():
                    if minute > self.last_intraday_ts:
                        self.last_intraday_ts = minute
                        if minute >= self.ib_periods[0] and minute <= self.ib_periods[1]:
                            ib_data.append(minute_data['low'])
                            ib_data.append(minute_data['high'])
                        # print(self.tpo_brackets)
                        # print(minute)
                        ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)
                        pb_idx_low = utils.get_next_lowest_index(self.price_bins, minute_data['low'])
                        pb_idx_high = utils.get_next_highest_index(self.price_bins, minute_data['high'])
                        for idx in range(pb_idx_low, pb_idx_high+1):
                            self.print_matrix[ts_idx, idx] = 1
                            self.volume_print_matrix[ts_idx, idx] = self.volume_print_matrix[ts_idx, idx] + minute_data['volume']

                res_p = self.calculateStatistics(self.print_matrix)
                res_v = self.calculateStatistics(self.volume_print_matrix)
                self.market_profile = res_p
                self.volume_profile = res_v
                #print(res_p)
                #print(res_v)
                """ calculate profile"""

    def calculateStatistics(self, print_matrix):
        tpo_sum_arr = np.sum(print_matrix, axis=0).A1
        #print(tpo_sum_arr)
        poc_idx = utils.mid_max_idx(tpo_sum_arr)
        poc_price = self.price_bins[poc_idx]
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
        initial_balance_tpo = np.sum(print_matrix[0:2], axis=0).A1
        # print(initial_balance_tpo)
        initial_balance_flags = [int(x > 0) for x in initial_balance_tpo]
        initial_balance_prices = np.multiply(initial_balance_flags, self.price_bins).tolist()
        initial_balance_tmp = [i for i in initial_balance_prices if i > 0]

        third_tpo = np.sum(print_matrix[3], axis=0).A1
        third_tpo_flags = [int(x > 0) for x in third_tpo]
        third_tpo_tmp = np.multiply(third_tpo_flags, self.price_bins).tolist()
        third_tpo_prices = [i for i in third_tpo_tmp if i > 0]
        #print('third_tpo')
        #print(third_tpo_prices)


        if len(initial_balance_tmp) == 0:
            initial_balance_tmp = [0, 0]
        initial_balance = [min(initial_balance_tmp), max(initial_balance_tmp)]
        initial_balance_idx = [initial_balance_prices.index(initial_balance[0]),
                               initial_balance_prices.index(initial_balance[1])]
        #print('initial_balance')
        #print(initial_balance)
        res = {}
        #res['poc_idx'] = poc_idx
        res['open'] = self.price_data['open']
        res['high'] = self.price_data['high']
        res['low'] = self.price_data['low']
        res['close'] = self.price_data['close']
        res['poc_price'] = poc_price
        #sym['poc_len'] = poc_len
        #res['value_area'] = value_area
        res['value_area_price'] = [self.price_bins[value_area[0]], self.price_bins[value_area[1]]]
        res['vah'] = max(res['value_area_price'])
        res['val'] = min(res['value_area_price'])
        #sym['balance_target'] = balance_target
        res['below_poc'] = below_poc
        res['above_poc'] = above_poc
        res['initial_balance'] = initial_balance
        res['third_tpo_high_extn'] = False if not third_tpo_prices else True if max(third_tpo_prices) > max(initial_balance) else False
        res['third_tpo_low_extn'] = False if not third_tpo_prices else True if min(third_tpo_prices) < min(initial_balance) else False
        #sym['initial_balance_acc'] = [min(ib_data), max(ib_data)]
        #res['initial_balance_idx'] = initial_balance_idx
        res['h_a_l'] = self.price_data['ht'] > self.price_data['lt']
        profile_dist = utils.get_profile_dist(print_matrix, self.price_bins, self.min_co_ext)
        profile_dist = utils.get_distribution(self.spot_book.spot_processor.spot_ts, profile_dist)
        res['profile_dist'] = profile_dist
        return res
