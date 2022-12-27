from datetime import datetime
import numpy as np
import time
import copy
from profile import utils
from itertools import compress
from config import va_pct, include_pre_market
from truedata.custom import TDCustom
import pandas as pd
import asyncio
import math
import helper.utils as helper_utils

class OptionProfileService:
    def __init__(self,  trade_day=None, market_cache=None):
        self.trade_day = trade_day
        self.market_cache = market_cache
        self.option_data = {}
        self.derived_data = {}
        if trade_day is None: #Default to today
            self.trade_day = time.strftime('%Y-%m-%d')
            start_str = time.strftime("%m/%d/%Y") + " 09:00:00"
            end_str = time.strftime("%m/%d/%Y ") + " 15:30:00"
            start_ts = int(time.mktime(time.strptime(start_str, "%m/%d/%Y %H:%M:%S")))
            end_ts = int(time.mktime(time.strptime(end_str, "%m/%d/%Y %H:%M:%S")))
            self.tpo_brackets = np.arange(start_ts, end_ts, 900)
        self.waiting_for_data = True
        self.spot_data = {}
        self.important_strikes = {}
        self.load_from_cache()
        self.calculate_important_strikes()

    def load_from_cache(self):
        print('load option data from_cache')
        if self.market_cache is not None:
            option_data = self.market_cache.get('option_data')
            #print(option_data)
            if option_data:
                symbol = list(option_data.keys())[0]
                first_epoch_minute = list(option_data[symbol]['hist'].keys())[0]
                self.set_trade_date_from_time(first_epoch_minute)
                self.waiting_for_data = False
                self.option_data = option_data
            spot_data = self.market_cache.get('spot_data')
            if spot_data is not None:
                self.spot_data = spot_data

    def calculate_important_strikes(self):
        for ticker, ticker_data in self.option_data.items():
            hist_data = ticker_data.get('hist', None)
            if hist_data is not None:
                last_epoc = max(list(hist_data.keys()))
                last_entry = hist_data[last_epoc]
                df = pd.DataFrame(last_entry)
                df['prev_oi'] = df['oi'] - df['oi_change']
                call_strikes = list(df[df['type'] == 'CE'].nlargest(n=8, columns=['prev_oi', 'oi_change'])['strike'])
                put_strikes = list(df[df['type'] == 'PE'].nlargest(n=8, columns=['prev_oi', 'oi_change'])['strike'])
                self.important_strikes[ticker] = {'CE': call_strikes, 'PE': put_strikes}

    def set_trade_date_from_time(self, epoch_tick_time):
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        trade_day = tick_date_time.strftime('%Y-%m-%d')
        self.trade_day = trade_day
        start_str = trade_day + " 09:10:00"
        end_str = trade_day + " 15:30:00"
        start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S")))
        self.tpo_brackets = np.arange(start_ts, end_ts, 300)

    def update_derived_data(self, data_dict):
        option_lst = data_dict['options_data']
        epoch_tick_time = int(datetime.fromisoformat(option_lst[0]['ltt'] + '+05:30').timestamp())
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        minute = tick_date_time.minute
        ts_idx = utils.get_next_lowest_index(self.tpo_brackets, minute)

        if data_dict['symbol'] not in self.derived_data:
            self.derived_data[data_dict['symbol']] = {'option_syms': [], 'iv_matrix': np.empty((0, 0)), 'io_matrix': np.empty((0, 0))}
        symbol_option_data = self.derived_data[data_dict['symbol']]
        if len(option_lst) > symbol_option_data['iv_matrix'].shape[1]:
            option_syms = [[x['strike'], x['type']] for x in option_lst]
            iv_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(option_syms))))
            io_matrix = np.matrix(np.zeros((len(self.tpo_brackets), len(option_syms))))
            symbol_option_data['option_syms'] = option_syms
            symbol_option_data['iv_matrix'] = iv_matrix
            symbol_option_data['io_matrix'] = io_matrix
            for idx in range(len(option_lst)):
                symbol_option_data['iv_matrix'][0, idx] = option_lst[idx]['IV']
                symbol_option_data['io_matrix'][0, idx] = option_lst[idx]['prev_oi']
                try: ##required if restarted in between session
                    symbol_option_data['iv_matrix'][ts_idx-1, idx] = option_lst[idx]['IV']
                    symbol_option_data['io_matrix'][0, idx] = option_lst[idx]['oi']
                except:
                    pass
        for idx in range(len(option_lst)):
            symbol_option_data['iv_matrix'][ts_idx, idx] = option_lst[idx]['IV']
            symbol_option_data['io_matrix'][ts_idx, idx] = option_lst[idx]['oi']
        """
        recent_changes = symbol_option_data['iv_matrix'][ts_idx] - symbol_option_data['iv_matrix'][ts_idx-1]
        net_changes = symbol_option_data['iv_matrix'][ts_idx] - symbol_option_data['iv_matrix'][0]
        #print(recent_changes)
        """

    def process_input_data(self, data_dict):
        option_lst = data_dict['options_data']
        #epoch_tick_time = int(time.mktime(time.strptime(option_lst[0]['ltt'], "%Y-%m-%dT%H:%M:%S")))
        epoch_tick_time = int(datetime.fromisoformat(option_lst[0]['ltt'] + '+05:30').timestamp())
        epoch_minute = int(epoch_tick_time // 60 * 60) + 60

        if self.waiting_for_data:
            self.set_trade_date_from_time(epoch_tick_time)
            self.waiting_for_data = False

        if data_dict['symbol'] not in self.option_data:
            self.option_data[data_dict['symbol']] = {'hist': {}}

        if self.socket is not None:
            symbol_option_data = self.option_data[data_dict['symbol']]
            df = pd.DataFrame(option_lst)
            df['ltt'] = df['ltt'].apply(lambda x: epoch_tick_time)
            df.fillna(0, inplace=True)
            #print(df.head().T)
            hist_df = df[['strike', 'type','volume', 'oi', 'oi_change', 'IV', 'ltp', 'ltt']]
            symbol_option_data['hist'][epoch_minute] = hist_df.to_dict('records')

            highest_strike = math.ceil((self.spot_data[data_dict['symbol']]['day_high'] * 1.06)/100)*100
            lowest_strike = math.floor((self.spot_data[data_dict['symbol']]['day_low'] * 0.94)/100)*100
            df['strike'] = df['strike'].astype(int)
            df = df[(df['strike'] <= highest_strike) & (df['strike'] >= lowest_strike)]
            tmp_data = df[['strike', 'type','ltt','volume', 'oi', 'oi_change', 'IV', 'delta', 'gamma', 'theta', 'ltp']]
            #print(tmp_data.columns)
            #print(tmp_data.head())
            asyncio.ensure_future(self.socket.all_option_input(data_dict['symbol'], tmp_data.to_dict('records')))
            prev_imp_strikes = copy.deepcopy(self.important_strikes)
            self.calculate_important_strikes()
            if prev_imp_strikes != self.important_strikes:
                asyncio.ensure_future(self.socket.important_strikes_update(data_dict['symbol'], self.important_strikes))
            #f_data_list = [inst_data for inst_data in tmp_data.to_dict('records') if self.filtered_option(data_dict['symbol'], inst_data)]
            #asyncio.ensure_future(self.socket.important_option_input(data_dict['symbol'], f_data_list))

        self.market_cache.set('option_data', self.option_data)
        # self.socket.emit('price_bins', json.dumps(sym['price_bins'], cls=NpEncoder), room=ticker)
        #print(net_changes)


    def process_spot_data(self, dict_input):
        #print(dict_input)
        self.spot_data[dict_input['symbol']] = {'ltp':dict_input['ltp'],'day_high':dict_input['day_high'],'day_low':dict_input['day_low'] }
        self.market_cache.set('spot_data', self.spot_data)

    def filtered_option(self, ticker, inst_data):

        strikes_by_options = self.important_strikes[ticker]
        res = True
        if strikes_by_options is not None:
            strike = inst_data['strike']
            option_type = inst_data['type']
            res = res and (strike in strikes_by_options[option_type])
        return res

    def get_hist_data(self, ticker):
        print('get_hist_data+++++++++++++++++++++++++++++++++++++++++++')
        hist_data = self.option_data.get(ticker, {}).get('hist', None)
        root_symbol = helper_utils.root_symbol(ticker)
        highest_strike = math.ceil((self.spot_data[root_symbol]['day_high'] * 1.06) / 100) * 100
        lowest_strike = math.floor((self.spot_data[root_symbol]['day_low'] * 0.94) / 100) * 100

        if hist_data is not None:
            tmp_data = []
            for ts, options_data in hist_data.items():
                for inst_data in options_data:
                    strike = int(inst_data['strike'])
                    if (strike <= highest_strike and strike >= lowest_strike):
                        tmp_data.append(inst_data)
            hist_data = tmp_data
        self.calculate_important_strikes()
        return hist_data

    def get_hist_data_b(self, ticker):
        print('get_hist_data+++++++++++++++++++++++++++++++++++++++++++')
        #print(self.option_data)
        hist_data = self.option_data.get(ticker, {}).get('hist', None)
        if hist_data is not None:
            # print(hist_data)
            root_symbol = helper_utils.root_symbol(ticker)
            highest_strike = math.ceil((self.spot_data[root_symbol]['day_high'] * 1.06) / 100) * 100
            lowest_strike = math.floor((self.spot_data[root_symbol]['day_low'] * 0.94) / 100) * 100
            strikes_by_options = self.important_strikes[ticker]
            print('strikes_by_options', strikes_by_options)
            tmp_data = []
            for ts, options_data in hist_data.items():
                for inst_data in options_data:
                    if self.filtered_option(ticker, inst_data):
                        inst_data['ltt'] = ts
                        tmp_data.append(inst_data)
            hist_data = tmp_data
            #print(hist_data)


        return hist_data

    def refresh(self):
        print('refreshing++++++++')
        self.option_data = {}
        self.derived_data = {}
        self.trade_day = time.strftime('%Y-%m-%d')
        self.waiting_for_data = True

    def get_spot_data(self, symbol):
        #print(dict_input)
        return self.spot_data.get(symbol, None)
