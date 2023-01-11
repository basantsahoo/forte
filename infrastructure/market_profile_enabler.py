import json
from datetime import datetime
import numpy as np
import time
from itertools import compress
from dynamics.profile import utils
from config import va_pct, include_pre_market,live_feed, back_test_day
from dynamics.profile.utils import NpEncoder
from db.market_data import prev_day_data, get_prev_week_candle, get_nth_day_profile_data
from helper.utils import get_pivot_points

class MarketProfileEnablerService:
    def __init__(self, trade_day=None, market_cache=None):
        self.trade_day = trade_day
        self.price_data = {}
        self.value_area_pct = va_pct
        self.min_co_ext = 2
        self.socket = None
        self.market_cache = market_cache
        self.waiting_for_data = True
        self.load_from_cache()
        if trade_day is None: #Default to today
            self.trade_day = time.strftime('%Y-%m-%d')
            """
            if live_feed:
                self.trade_day = time.strftime('%Y-%m-%d')
            else:
                self.trade_day = back_test_day
            """

    def load_from_cache(self):
        if self.market_cache is not None:
            price_data = self.market_cache.get('price_data')
            if price_data:
                symbol = list(price_data.keys())[0]
                first_epoch_minute = list(price_data[symbol]['hist'].keys())[0]
                self.set_trade_date_from_time(first_epoch_minute)
                self.waiting_for_data = False
                self.price_data[self.trade_day] = price_data

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
        ib_end_ts = int(time.mktime(time.strptime(ib_end_str, "%Y-%m-%d %H:%M:%S")))
        self.ib_periods = [start_ts, ib_end_ts]
        self.price_data[self.trade_day] = {}

    def refresh(self):
        print('refreshing++++++++')
        self.price_data = {}
        self.trade_day = time.strftime('%Y-%m-%d')
        self.waiting_for_data = True

    def get_ltp(self, ticker):
        return prev_day_data(ticker, self.trade_day)[2]

    def get_last_info(self, ticker):
        intraday_info = self.price_data.get(self.trade_day, {}).get(ticker, {})
        last_tick = {}
        #print(self.price_data)
        if intraday_info and intraday_info['hist']:
            last_tick_time = max(intraday_info['hist'].keys())
            last_tick = {'date': self.trade_day, 'time': datetime.fromtimestamp(last_tick_time).strftime("%Y-%m-%d %H:%M:%S") , 'price': intraday_info['hist'][last_tick_time]['close']}
        if last_tick:
            return last_tick
        else:
            return {'date': self.trade_day, 'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'price': prev_day_data(ticker, self.trade_day)[2]}

    def get_pivots(self, ticker):
        return get_pivot_points(get_prev_week_candle(ticker, self.trade_day))

    def get_prev_day_profile(self, ticker):
        return get_nth_day_profile_data(ticker, self.trade_day, 1).to_dict('records')[0]

    """
    process ticks to 1 min data
    """

    def process_input_data(self, inst):
        epoch_tick_time = inst['timestamp']
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
        first = False
        if inst['symbol'] not in self.price_data[self.trade_day]:
            self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['high'])}
            first = True
        minute_candle = {
            'open': inst['open'],
            'high': inst['high'],
            'low': inst['low'],
            'close': inst['close'],
            'ltp': inst['close'],
            'volume': inst['volume'],
            'lt': inst['timestamp'],
            'ht': inst['timestamp']
        }
        if epoch_minute in self.price_data[self.trade_day][inst['symbol']]['hist']:
            minute_candle = {
                'open': self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['open'],
                'high': max(inst['high'],
                            self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['high']),
                'low': min(inst['low'],
                           self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['low']),
                'close': inst['close']
            }
            # print(minute_candle)
        if mm in [1, 31] and ss == 0:
            print(str(hh) + ":" + str(mm) + ":" + str(ss))
            # print(minute_candle)

        self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute] = minute_candle
        if first:
            self.price_data[self.trade_day][inst['symbol']].update(minute_candle)
        else:
            if minute_candle['high'] > self.price_data[self.trade_day][inst['symbol']]['high'] or minute_candle['low'] < self.price_data[self.trade_day][inst['symbol']]['low']:
                self.price_data[self.trade_day][inst['symbol']]['reset_pb'] = True
            self.price_data[self.trade_day][inst['symbol']]['high'] = max(inst['high'],
                                                                          self.price_data[self.trade_day][
                                                                              inst['symbol']]['high'])
            self.price_data[self.trade_day][inst['symbol']]['low'] = min(inst['low'],
                                                                         self.price_data[self.trade_day][
                                                                             inst['symbol']]['low'])
            self.price_data[self.trade_day][inst['symbol']]['close'] = inst['close']

        self.calculateMeasures(inst['symbol'])
        self.market_cache.set('price_data', self.price_data[self.trade_day])

    def calculateMeasures(self, ticker):
        sym = self.price_data[self.trade_day][ticker]
        if sym['reset_pb']:
            sym['reset_pb'] = False
            sym['price_bins'] = np.arange(np.floor(sym['tick_size'] * np.floor(sym['low'] / sym['tick_size'])),
                                          np.ceil(sym['tick_size'] * np.ceil(sym['high'] / sym['tick_size'])) + sym[
                                              'tick_size'], sym['tick_size'])
            #self.socket.send_pb_reset( sym['price_bins'], ticker)
            #self.socket.emit('price_bins', json.dumps(sym['price_bins'], cls=NpEncoder), room=ticker)

            return sym['price_bins']
        else:
            return None
    def get_hist_data(self, ticker):
        return self.price_data.get(self.trade_day, {}).get(ticker, None)


class TickMarketProfileEnablerService(MarketProfileEnablerService):

    def process_input_data(self, inst):
        if self.waiting_for_data:
            self.set_trade_date_from_time(inst['timestamp'])
            self.waiting_for_data = False
        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}
        epoch_tick_time = inst['timestamp']
        epoch_minute = int(epoch_tick_time // 60 * 60) + 60
        if self.trade_day not in self.price_data:
            self.price_data[self.trade_day] = {}

        """
        if not include_pre_market and epoch_minute < min(self.tpo_brackets) + 60:
            continue
        """

        first = False
        if inst['symbol'] not in self.price_data[self.trade_day]:
            self.price_data[self.trade_day][inst['symbol']] = {'reset_pb': True, 'hist': {}, 'tick_size': utils.get_tick_size(inst['ltp'])}
            first = True
        minute_candle = {
            'open': inst['ltp'],
            'high': inst['ltp'],
            'low': inst['ltp'],
            'close': inst['ltp'],
            'ltp': inst['ltp'],
            'volume': inst.get('min_volume', 0),
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
                'ltp': inst['ltp'],
                'volume': self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['volume'] + inst.get('min_volume', 0),
                'lt': inst['timestamp'] if inst['ltp'] > self.price_data[self.trade_day][inst['symbol']]['high'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['ht'],
                'ht': inst['timestamp'] if inst['ltp'] < self.price_data[self.trade_day][inst['symbol']]['low'] else self.price_data[self.trade_day][inst['symbol']]['hist'][epoch_minute]['lt']
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

            self.price_data[self.trade_day][inst['symbol']]['close'] = inst['ltp']
            self.price_data[self.trade_day][inst['symbol']]['volume'] = self.price_data[self.trade_day][inst['symbol']]['volume'] + inst['min_volume']
        self.market_cache.set('price_data', self.price_data[self.trade_day])
        tmp_data = minute_candle.copy()
        tmp_data['timestamp'] = epoch_minute
        tmp_data['symbol'] = inst['symbol']
        #del tmp_data['volume']
        del tmp_data['ht']
        del tmp_data['lt']
        return tmp_data

