
from datetime import datetime
import numpy as np
import time
from itertools import compress
from dynamics.profile import utils

from config import va_pct, include_pre_market
from helper.utils import get_pivot_points
from entities.trading_day import TradeDateTime

class MarketProfileService:
    def __init__(self, trade_day=None, market_cache=None):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = 2
        self.socket = None
        self.market_cache = market_cache
        self.waiting_for_data = True
        self.load_from_cache()
        self.spot_book = None

        if trade_day is None: #Default to today
            self.trade_day = time.strftime('%Y-%m-%d')
            start_str = time.strftime("%m/%d/%Y") + " 09:15:00"
            end_str = time.strftime("%m/%d/%Y ") + " 15:30:00"
            start_ts = int(time.mktime(time.strptime(start_str, "%m/%d/%Y %H:%M:%S")))
            end_ts = int(time.mktime(time.strptime(end_str, "%m/%d/%Y %H:%M:%S")))
            self.tpo_brackets = np.arange(start_ts, end_ts, 1800)

    def load_from_cache(self):
        pass

    def set_trade_day(self, trade_day):
        self.trade_day = trade_day

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
        self.price_data[self.trade_day] = {}
        self.tpo_brackets = np.arange(start_ts, end_ts, 1800)

    """
    process ticks to 1 min data
    """

    def process_input_data(self, lst):
        epoch_tick_time = lst[0]['timestamp']
        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False
        epoch_minute = TradeDateTime.get_epoc_minute(epoch_tick_time)
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        mm = tick_date_time.minute
        ss = tick_date_time.second
        hh = tick_date_time.hour

        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        processed_data = []
        for inst in lst:
            first = False
            if inst['asset'] not in self.price_data[self.trade_day]:
                self.price_data[self.trade_day][inst['asset']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['high'])}
                first = True
            minute_candle = {
                'open': inst['ltp'],
                'high': inst['ltp'],
                'low': inst['ltp'],
                'close': inst['ltp']
            }
            if epoch_minute in self.price_data[self.trade_day][inst['asset']]['hist']:
                minute_candle = {
                    'open': self.price_data[self.trade_day][inst['asset']]['hist'][epoch_minute]['open'],
                    'high': max(inst['ltp'],
                                self.price_data[self.trade_day][inst['asset']]['hist'][epoch_minute]['high']),
                    'low': min(inst['ltp'],
                               self.price_data[self.trade_day][inst['asset']]['hist'][epoch_minute]['low']),
                    'close': inst['ltp']
                }
                # print(minute_candle)
            if mm in [1, 31] and ss == 0:
                print(str(hh) + ":" + str(mm) + ":" + str(ss))
                # print(minute_candle)
            self.price_data[self.trade_day][inst['asset']]['hist'][epoch_minute] = minute_candle
            if first:
                self.price_data[self.trade_day][inst['asset']].update(minute_candle)
            else:
                if minute_candle['high'] > self.price_data[self.trade_day][inst['asset']]['high'] or minute_candle[
                    'low'] < self.price_data[self.trade_day][inst['asset']]['low']:
                    self.price_data[self.trade_day][inst['asset']]['reset_pb'] = True
                self.price_data[self.trade_day][inst['asset']]['high'] = max(inst['ltp'],
                                                                              self.price_data[self.trade_day][
                                                                                  inst['asset']]['high'])
                self.price_data[self.trade_day][inst['asset']]['low'] = min(inst['ltp'],
                                                                             self.price_data[self.trade_day][
                                                                                 inst['asset']]['low'])
                self.price_data[self.trade_day][inst['asset']]['close'] = inst['ltp']
            # print(self.price_data[self.trade_day][inst['asset']])
            processed_data.append([inst['asset'], {epoch_minute: minute_candle}])
        return processed_data


    def calculateMeasures(self):
        if not self.waiting_for_data:
            for ticker, sym in self.price_data[self.trade_day].items():
                #print(sym)
                #print(self.ib_periods)
                if sym['reset_pb']:
                    sym['reset_pb'] = False
                    sym['price_bins'] = np.arange(np.floor(sym['tick_size']*np.floor(sym['low']/sym['tick_size'])), np.ceil(sym['tick_size']*np.ceil(sym['high']/sym['tick_size'])) + sym['tick_size'] , sym['tick_size'])
                    sym['print_matrix'] = np.matrix(np.zeros((len(self.tpo_brackets), len(sym['price_bins']))))
                ib_data = []
                for minute, minute_data in sym['hist'].items():
                    if minute >= self.ib_periods[0] and minute <= self.ib_periods[1]:
                        ib_data.append(minute_data['low'])
                        ib_data.append(minute_data['high'])
                    # print(self.tpo_brackets)
                    # print(minute)
                    ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)
                    pb_idx_low = utils.get_next_lowest_index(sym['price_bins'], minute_data['low'])
                    pb_idx_high = utils.get_next_highest_index(sym['price_bins'], minute_data['high'])
                    for idx in range(pb_idx_low, pb_idx_high+1):
                        sym['print_matrix'][ts_idx, idx] = 1
                """ calculate profile"""
                # print(sym['print_matrix'])

                tpo_sum_arr = np.sum(sym['print_matrix'], axis=0).A1
                # print(tpo_sum_arr)
                poc_idx = utils.mid_max_idx(tpo_sum_arr)
                poc_price = sym['price_bins'][poc_idx]
                poc_len = tpo_sum_arr[poc_idx]
                balance_target = utils.calculate_balanced_target(poc_price, sym['high'], sym['low'])
                value_area = utils.calculate_value_area(tpo_sum_arr, poc_idx, self.value_area_pct)
                below_poc = np.sum(tpo_sum_arr[0:poc_idx])
                try:
                    above_poc = np.sum(tpo_sum_arr[poc_idx + 1::])
                except:
                    print(tpo_sum_arr)
                    print(poc_idx)
                    print(sym)
                initial_balance_tpo = np.sum(sym['print_matrix'][0:2], axis=0).A1
                # print(initial_balance_tpo)
                initial_balance_flags = [int(x > 0) for x in initial_balance_tpo]
                initial_balance_prices = np.multiply(initial_balance_flags, sym['price_bins']).tolist()
                initial_balance_tmp = [i for i in initial_balance_prices if i > 0]
                if len(initial_balance_tmp) == 0:
                    initial_balance_tmp = [0, 0]
                initial_balance = [min(initial_balance_tmp), max(initial_balance_tmp)]
                initial_balance_idx = [initial_balance_prices.index(initial_balance[0]),
                                       initial_balance_prices.index(initial_balance[1])]
                sym['poc_idx'] = poc_idx
                sym['poc_price'] = poc_price
                sym['poc_len'] = poc_len
                sym['value_area'] = value_area
                sym['value_area_price'] = [sym['price_bins'][value_area[0]], sym['price_bins'][value_area[1]]]
                sym['balance_target'] = balance_target
                sym['below_poc'] = below_poc
                sym['above_poc'] = above_poc
                sym['initial_balance'] = initial_balance
                sym['initial_balance_acc'] = [min(ib_data), max(ib_data)]
                sym['initial_balance_idx'] = initial_balance_idx
                sym['h_a_l'] = sym['ht'] > sym['lt']
                profile_dist = utils.get_profile_dist(sym['print_matrix'], sym['price_bins'], self.min_co_ext)
                profile_dist = utils.get_distribution(sym['hist'], profile_dist)
                sym['profile_dist'] = profile_dist

    def get_profile_data(self):
        day = self.price_data.get(self.trade_day, {})
        response = []
        for ticker in day.keys():
            data = day[ticker].copy()
            data['asset'] = ticker
            del data['hist']
            response.append(data)
        return response

    def get_profile_data_for_day_sym(self, ticker):
        day = self.price_data[self.trade_day]
        response = day[ticker].copy()
        del response['hist']
        response['asset'] = ticker
        return response

class VolumeProfileService(MarketProfileService):
    def day_setup(self, epoch_tick_time):
        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False



    def frame_change_action(self, current_frame, next_frame):
        self.day_setup(current_frame)
        if self.spot_book is not None:
            """
            inst = self.spot_book.spot_processor.spot_ts[current_frame]
            option_matrix = self.spot_book.asset_book.option_matrix
            put_volume, call_volume = option_matrix.get_ts_volume(self.trade_day, current_frame)
            total_volume = sum([put_volume, call_volume])/100000
            inst['volume'] = total_volume
            inst['asset'] = self.spot_book.asset_book.asset
            """
            self.process_input_data(current_frame)
            self.calculateProfile()
            self.generate_signal()

    def process_input_data(self, current_frame):
        print('process_input_data+++++++++', current_frame)
        if self.waiting_for_data:
            self.set_trade_date_from_time(current_frame)
            self.waiting_for_data = False

        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        #epoch_tick_time = inst['timestamp']
        epoch_minute = TradeDateTime.get_epoc_minute(current_frame)

        """
        if not include_pre_market and epoch_minute < min(self.tpo_brackets) + 60:
            continue
        """
        first = False
        inst = self.spot_book.spot_processor.spot_ts[current_frame]
        if self.spot_book.asset_book.asset not in self.price_data[self.trade_day]:
            self.price_data[self.trade_day][self.spot_book.asset_book.asset] = {'reset_pb': True,  'tick_size': utils.get_tick_size(inst['high'])}
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

        #self.price_data[self.trade_day][inst['asset']]['hist'][epoch_minute] = minute_candle
        if first:
            self.price_data[self.trade_day][inst['asset']].update(minute_candle)
        else:
            if minute_candle['high'] > self.price_data[self.trade_day][inst['asset']]['high']:
                self.price_data[self.trade_day][inst['asset']]['high'] = minute_candle['high']
                self.price_data[self.trade_day][inst['asset']]['ht'] = minute_candle['ht']
                self.price_data[self.trade_day][inst['asset']]['reset_pb'] = True
            if minute_candle['low'] < self.price_data[self.trade_day][inst['asset']]['low']:
                self.price_data[self.trade_day][inst['asset']]['low'] = minute_candle['low']
                self.price_data[self.trade_day][inst['asset']]['lt'] = minute_candle['lt']
                self.price_data[self.trade_day][inst['asset']]['reset_pb'] = True

            self.price_data[self.trade_day][inst['asset']]['close'] = inst['close']
            self.price_data[self.trade_day][inst['asset']]['volume'] = self.price_data[self.trade_day][inst['asset']]['volume'] + inst['volume']

    def calculateProfile(self):
        if not self.waiting_for_data:
            for ticker, sym in self.price_data[self.trade_day].items():
                #print(sym)
                #print(self.ib_periods)
                if sym['reset_pb']:
                    sym['reset_pb'] = False
                    sym['price_bins'] = np.arange(np.floor(sym['tick_size']*np.floor(sym['low']/sym['tick_size'])), np.ceil(sym['tick_size']*np.ceil(sym['high']/sym['tick_size'])) + sym['tick_size'] , sym['tick_size'])
                    sym['print_matrix'] = np.matrix(np.zeros((len(self.tpo_brackets), len(sym['price_bins']))))
                    sym['volume_print_matrix'] = np.matrix(np.zeros((len(self.tpo_brackets), len(sym['price_bins']))))
                ib_data = []
                for minute, minute_data in self.spot_book.spot_processor.spot_ts.items():
                    if minute >= self.ib_periods[0] and minute <= self.ib_periods[1]:
                        ib_data.append(minute_data['low'])
                        ib_data.append(minute_data['high'])
                    # print(self.tpo_brackets)
                    # print(minute)
                    ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)
                    pb_idx_low = utils.get_next_lowest_index(sym['price_bins'], minute_data['low'])
                    pb_idx_high = utils.get_next_highest_index(sym['price_bins'], minute_data['high'])
                    for idx in range(pb_idx_low, pb_idx_high+1):
                        sym['print_matrix'][ts_idx, idx] = 1
                        sym['volume_print_matrix'][ts_idx, idx] = sym['print_matrix'][ts_idx, idx] + minute_data['volume']

                res_p = self.calculateStatistics(sym, category="market")
                res_v = self.calculateStatistics(sym, category="volume")
                sym['market_profile'] = res_p
                sym['volume_profile'] = res_v
                print(res_p)
                print(res_v)
                """ calculate profile"""

    def calculateStatistics(self, sym, category="market"):

                if category == 'market':
                    print_matrix = sym['print_matrix']
                elif category == 'volume':
                    print_matrix = sym['volume_print_matrix']
                else:
                    print_matrix = sym['volume_print_matrix']

                tpo_sum_arr = np.sum(print_matrix, axis=0).A1
                #print(tpo_sum_arr)
                poc_idx = utils.mid_max_idx(tpo_sum_arr)
                poc_price = sym['price_bins'][poc_idx]

                #print(poc_price)
                #poc_len = tpo_sum_arr[poc_idx]
                #balance_target = utils.calculate_balanced_target(poc_price, sym['high'], sym['low'])
                value_area = utils.calculate_value_area(tpo_sum_arr, poc_idx, self.value_area_pct)
                total_val = np.sum(tpo_sum_arr)
                below_poc = round(np.sum(tpo_sum_arr[0:poc_idx])/total_val, 2)
                try:
                    above_poc = round(np.sum(tpo_sum_arr[poc_idx + 1::])/total_val,2)
                except:
                    print(tpo_sum_arr)
                    print(poc_idx)
                    print(sym)
                initial_balance_tpo = np.sum(print_matrix[0:2], axis=0).A1
                # print(initial_balance_tpo)
                initial_balance_flags = [int(x > 0) for x in initial_balance_tpo]
                initial_balance_prices = np.multiply(initial_balance_flags, sym['price_bins']).tolist()
                initial_balance_tmp = [i for i in initial_balance_prices if i > 0]

                third_tpo = np.sum(print_matrix[3], axis=0).A1
                third_tpo_flags = [int(x > 0) for x in third_tpo]
                third_tpo_tmp = np.multiply(third_tpo_flags, sym['price_bins']).tolist()
                third_tpo_prices = [i for i in third_tpo_tmp if i > 0]
                print('third_tpo')
                print(third_tpo_prices)


                if len(initial_balance_tmp) == 0:
                    initial_balance_tmp = [0, 0]
                initial_balance = [min(initial_balance_tmp), max(initial_balance_tmp)]
                initial_balance_idx = [initial_balance_prices.index(initial_balance[0]),
                                       initial_balance_prices.index(initial_balance[1])]

                res = {}
                #res['poc_idx'] = poc_idx
                res['open'] = sym['open']
                res['poc_price'] = poc_price
                #sym['poc_len'] = poc_len
                #res['value_area'] = value_area
                res['value_area_price'] = [sym['price_bins'][value_area[0]], sym['price_bins'][value_area[1]]]
                #sym['balance_target'] = balance_target
                res['below_poc'] = below_poc
                res['above_poc'] = above_poc
                res['initial_balance'] = initial_balance
                res['third_tpo_high_extn'] = False if not third_tpo_prices else True if max(third_tpo_prices) > max(initial_balance) else False
                res['third_tpo_low_extn'] = False if not third_tpo_prices else True if min(third_tpo_prices) < min(initial_balance) else False
                #sym['initial_balance_acc'] = [min(ib_data), max(ib_data)]
                #res['initial_balance_idx'] = initial_balance_idx
                res['h_a_l'] = sym['ht'] > sym['lt']
                profile_dist = utils.get_profile_dist(sym['print_matrix'], sym['price_bins'], self.min_co_ext)
                profile_dist = utils.get_distribution(self.spot_book.spot_processor.spot_ts, profile_dist)
                res['profile_dist'] = profile_dist
                return res

    def generate_signal(self):
        {'volume_profile.third_tpo_high_extn':False}

