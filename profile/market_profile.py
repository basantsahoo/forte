
from datetime import datetime
import numpy as np
import time
from itertools import compress
from profile import utils

from config import va_pct, include_pre_market


class MarketProfileService:
    def __init__(self, trade_day=None):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = 2
        if trade_day is None: #Default to today
            self.trade_day = time.strftime('%Y-%m-%d')
            start_str = time.strftime("%m/%d/%Y") + " 09:15:00"
            end_str = time.strftime("%m/%d/%Y ") + " 15:30:00"
            start_ts = int(time.mktime(time.strptime(start_str, "%m/%d/%Y %H:%M:%S")))
            end_ts = int(time.mktime(time.strptime(end_str, "%m/%d/%Y %H:%M:%S")))
            self.tpo_brackets = np.arange(start_ts, end_ts, 1800)
        self.tpo_letters = list(map(chr, range(65, 91)))[0:len(self.tpo_brackets)]
        self.waiting_for_data = True

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

    """
    process ticks to 1 min data
    """

    def process_input_data(self, lst):
        epoch_tick_time = lst[0]['timestamp']
        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False
        epoch_minute = int(epoch_tick_time // 60 * 60) + 60
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        mm = tick_date_time.minute
        ss = tick_date_time.second
        hh = tick_date_time.hour

        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        processed_data = []
        for inst in lst:
            if not include_pre_market and epoch_minute < min(self.tpo_brackets):
                continue
            first = False
            if inst['symbol'] not in self.price_data[self.trade_day]:
                self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['high'])}
                first = True
            minute_candle = {
                'open': inst['ltp'],
                'high': inst['ltp'],
                'low': inst['ltp'],
                'close': inst['ltp']
            }
            if epoch_minute in self.price_data[self.trade_day][inst['symbol']]['hist']:
                minute_candle = {
                    'open': self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['open'],
                    'high': max(inst['ltp'],
                                self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['high']),
                    'low': min(inst['ltp'],
                               self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['low']),
                    'close': inst['ltp']
                }
                # print(minute_candle)
            if mm in [1, 31] and ss == 0:
                print(str(hh) + ":" + str(mm) + ":" + str(ss))
                # print(minute_candle)
            self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute] = minute_candle
            if first:
                self.price_data[self.trade_day][inst['symbol']].update(minute_candle)
            else:
                if minute_candle['high'] > self.price_data[self.trade_day][inst['symbol']]['high'] or minute_candle[
                    'low'] < self.price_data[self.trade_day][inst['symbol']]['low']:
                    self.price_data[trade_day][inst['symbol']]['reset_pb'] = True
                self.price_data[self.trade_day][inst['symbol']]['high'] = max(inst['ltp'],
                                                                              self.price_data[self.trade_day][
                                                                                  inst['symbol']]['high'])
                self.price_data[self.trade_day][inst['symbol']]['low'] = min(inst['ltp'],
                                                                             self.price_data[self.trade_day][
                                                                                 inst['symbol']]['low'])
                self.price_data[self.trade_day][inst['symbol']]['close'] = inst['ltp']
            # print(self.price_data[self.trade_day][inst['symbol']])
            processed_data.append([inst['symbol'], {epoch_minute: minute_candle}])
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
                extremes = utils.get_extremes(sym['print_matrix'], sym['price_bins'], self.min_co_ext)
                extremes = utils.get_distribution(sym['hist'], extremes)
                sym['extremes'] = extremes

    def get_profile_data(self):
        day = self.price_data.get(self.trade_day, {})
        response = []
        for ticker in day.keys():
            data = day[ticker].copy()
            data['symbol'] = ticker
            del data['hist']
            response.append(data)
        return response

    def get_profile_data_for_day_sym(self, ticker):
        day = self.price_data[self.trade_day]
        response = day[ticker].copy()
        del response['hist']
        response['symbol'] = ticker
        return response

class TickMarketProfileService(MarketProfileService):
    def process_input_data(self, lst):
        epoch_tick_time = lst[0]['timestamp']
        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False
        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        epoch_minute = int(epoch_tick_time // 60 * 60)
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        mm = tick_date_time.minute
        ss = tick_date_time.second
        hh = tick_date_time.hour
        #print(hh)
        ts = hh * 100 + mm
        #print(ts)
        if ts < 915:
            print('market not open')
            return []
        processed_data = []
        for inst in lst:
            first = False
            if inst['symbol'] not in self.price_data[self.trade_day]:
                self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['ltp'])}
                first = True
            minute_candle = {
                'open': inst['ltp'],
                'high': inst['ltp'],
                'low': inst['ltp'],
                'close': inst['ltp'],
                'volume': inst.get('volume', 0),
                'lt': inst['timestamp'],
                'ht': inst['timestamp']
            }
            if epoch_minute in self.price_data[self.trade_day][inst['symbol']]['hist']:
                minute_candle = {
                    'open': self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['open'],
                    'high': max(inst['ltp'],
                                self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['high']),
                    'low': min(inst['ltp'],
                               self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['low']),
                    'close': inst['ltp'],
                    'volume': self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['low'] + inst.get('volume', 0),
                    'lt': inst['timestamp'] if inst['ltp'] > self.price_data[self.trade_day][inst['symbol']]['high'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['ht'],
                    'ht': inst['timestamp'] if inst['ltp'] < self.price_data[self.trade_day][inst['symbol']]['low'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['lt']
                }
                # print(minute_candle)
            if mm in [1, 31] and ss == 0:
                print(str(hh) + ":" + str(mm) + ":" + str(ss))
                # print(minute_candle)
            self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute] = minute_candle
            if first:
                self.price_data[self.trade_day][inst['symbol']].update(minute_candle)
            else:
                if minute_candle['high'] > self.price_data[self.trade_day][inst['symbol']]['high']:
                    self.price_data[self.trade_day][inst['symbol']]['high'] = minute_candle['high']
                    self.price_data[self.trade_day][inst['symbol']]['ht'] = minute_candle['ht']
                    self.price_data[self.trade_day][inst['symbol']]['reset_pb'] = True
                if minute_candle['low'] < self.price_data[self.trade_day][inst['symbol']]['low']:
                    self.price_data[self.trade_day][inst['symbol']]['low'] = minute_candle['low']
                    self.price_data[self.trade_day][inst['symbol']]['lt'] = minute_candle['lt']
                    self.price_data[self.trade_day][inst['symbol']]['reset_pb'] = True
                self.price_data[self.trade_day][inst['symbol']]['close'] = inst['ltp']
            # print(self.price_data[self.trade_day][inst['symbol']])
            tmp_data = minute_candle.copy()
            tmp_data['timestamp'] = epoch_minute
            tmp_data['symbol'] = inst['symbol']
            del tmp_data['volume']
            del tmp_data['ht']
            del tmp_data['lt']
            processed_data.append({epoch_minute: tmp_data})
        return processed_data

class HistMarketProfileService(MarketProfileService):

    def process_input_data(self, lst):
        if self.waiting_for_data:
            self.set_trade_date_from_time(lst[0]['timestamp'])
            self.waiting_for_data = False
        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}
        for inst in lst:
            epoch_tick_time = inst['timestamp']
            epoch_minute = int(epoch_tick_time // 60 * 60)
            """
            if not include_pre_market and epoch_minute < min(self.tpo_brackets) + 60:
                continue
            """
            first = False
            if inst['symbol'] not in self.price_data[self.trade_day]:
                self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['high'])}
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
            """
            if mm in [1, 31] and ss == 0:
                print(str(hh) + ":" + str(mm) + ":" + str(ss))
                # print(minute_candle)
            """
            self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute] = minute_candle
            if first:
                self.price_data[self.trade_day][inst['symbol']].update(minute_candle)
            else:
                if minute_candle['high'] > self.price_data[self.trade_day][inst['symbol']]['high']:
                    self.price_data[self.trade_day][inst['symbol']]['high'] = minute_candle['high']
                    self.price_data[self.trade_day][inst['symbol']]['ht'] = minute_candle['ht']
                    self.price_data[self.trade_day][inst['symbol']]['reset_pb'] = True
                if minute_candle['low'] < self.price_data[self.trade_day][inst['symbol']]['low']:
                    self.price_data[self.trade_day][inst['symbol']]['low'] = minute_candle['low']
                    self.price_data[self.trade_day][inst['symbol']]['lt'] = minute_candle['lt']
                    self.price_data[self.trade_day][inst['symbol']]['reset_pb'] = True

                self.price_data[self.trade_day][inst['symbol']]['close'] = inst['close']
                self.price_data[self.trade_day][inst['symbol']]['volume'] = self.price_data[self.trade_day][inst['symbol']]['volume'] + inst['volume']



