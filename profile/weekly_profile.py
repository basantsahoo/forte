from datetime import datetime
import numpy as np
import time
from itertools import compress
from profile import utils
from config import va_pct, include_pre_market


class WeeklyMarketProfileService:
    def __init__(self, trade_day=None):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = 2
        self.waiting_for_data = False

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


    def process_input_data(self, lst):
        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        for inst in lst:
            epoch_tick_time = inst['timestamp']
            epoch_minute = int(epoch_tick_time // 60 * 60)

            first = False
            if inst['symbol'] not in self.price_data[self.trade_day]:
                self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['high']) * 5}
                first = True
            minute_candle = {
                'open': inst['ltp'],
                'high': inst['ltp'],
                'low': inst['ltp'],
                'close': inst['ltp'],
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
                    'lt': inst['timestamp'] if inst['ltp'] > self.price_data[self.trade_day][inst['symbol']][
                        'high'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['ht'],
                    'ht': inst['timestamp'] if inst['ltp'] < self.price_data[self.trade_day][inst['symbol']]['low'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['lt']
                }
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


    def calculateMeasures(self):
        if not self.waiting_for_data:
            for ticker, sym in self.price_data[self.trade_day].items():
                #print(sym)
                #print(self.ib_periods)
                if sym['reset_pb']:
                    sym['reset_pb'] = False
                    sym['price_bins'] = np.arange(np.floor(sym['tick_size']*np.floor(sym['low']/sym['tick_size'])), np.ceil(sym['tick_size']*np.ceil(sym['high']/sym['tick_size'])) + sym['tick_size'], sym['tick_size'])
                    sym['print_matrix'] = np.matrix(np.zeros((len(self.tpo_brackets), len(sym['price_bins']))))
                for minute, minute_data in sym['hist'].items():
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
                sym['poc_idx'] = poc_idx
                sym['poc_price'] = poc_price
                sym['poc_len'] = poc_len
                sym['value_area'] = value_area
                sym['value_area_price'] = [sym['price_bins'][value_area[0]], sym['price_bins'][value_area[1]]]
                sym['balance_target'] = balance_target
                sym['below_poc'] = below_poc
                sym['above_poc'] = above_poc
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