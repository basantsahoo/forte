import copy
import time
from datetime import datetime
from helper.utils import get_broker_order_type, get_exit_order_type
from arc.dummy_broker import DummyBroker
from servers.server_settings import cache_dir
from diskcache import Cache
import pandas as pd
from helper.utils import inst_is_option, get_market_view
from datetime import datetime as dt

class AlgoPortfolioManager:
    def __init__(self, place_live_orders=False, data_interface=None, process_id=1000):
        self.ltps = {}
        self.last_times = {}
        self.broker = None
        self.strategy_order_map = {}
        self.broker = None
        self.dummy_broker = None
        self.data_interface = data_interface
        self.pending_orders = {}
        self.pending_order_seq = 0
        self.executed_orders = 0
        self.market_book = None
        self.process_id = process_id
        #self.cache = Cache(cache_dir + 'algo_pm_cache')
        self.cache = Cache(cache_dir + "/P_" + str(self.process_id) + "/" + 'algo_pm_cache')
        self.position_book = self.cache.get('algo_pm', {})
        self.cache.set('algo_pm', {})

        if place_live_orders:
            self.set_live()


    """required for storing trades in trader db"""
    def set_dummy_broker(self):
        pass
        #self.dummy_broker = DummyBroker()

    def set_live(self):
        #pass
        self.set_dummy_broker()

    def feed_stream(self, feed):

        if feed['feed_type'] == 'spot':
            for data_item in feed['data']:
                self.ltps[feed['asset']] = data_item['close']
                self.last_times[feed['asset']] = data_item['timestamp']
        if feed['feed_type'] == 'option':
            for data_item in feed['data']:
                symbol = feed['asset'] + "_" + data_item['instrument']
                self.ltps[symbol] = data_item['close']
                self.last_times[symbol] = data_item['timestamp']
        try: #Next day first feed will fail
            self.evaluate_risk()
        except Exception as e:
            print(e)
        self.monitor_position()

    def monitor_position(self):
        pass

    def place_oms_entry_order(self, order_info, order_type):
        #print('going to place place_oms_entry_order', strategy_id, symbol, order_side,order_id,qty)
        if self.data_interface is not None:
            self.data_interface.place_entry_order(order_info, order_type)

    def place_oms_exit_order(self, order_info, order_type):
        print('going to place data_interface ==============')
        #print('going to place place_oms_exit_order', strategy_id, symbol, order_side, order_id,qty)
        if self.data_interface is not None:
            self.data_interface.place_exit_order(order_info, order_type)

    def add_trade_symbol(self, instrument):
        asset_book = self.market_book.get_asset_book(instrument['asset'])
        expiry_date = asset_book.expiry_dates[instrument['expiry']]
        is_month_end = asset_book.expiry_month_ends[instrument['expiry']]
        exp = dt.strptime(expiry_date, '%Y-%m-%d').strftime('%y%-m%d') if not is_month_end else dt.strptime(expiry_date, '%Y-%m-%d').strftime('%y%b').upper()
        sym = "NSE:" + instrument['asset'] + exp + str(instrument['strike']) + instrument['kind']
        instrument['symbol'] = sym
        return instrument

    def strategy_entry_signal(self, signal_info):
        print('########################################## algo port strategy_entry_signal')
        #print("algo port signal info===", signal_info)
        trade_set = signal_info['trade_set']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        for trade in trade_set:
            for leg_group in trade['leg_groups']:
                for leg in leg_group['legs']:
                    leg['instrument'] = self.add_trade_symbol(leg['instrument'])
        #print(signal_info)
        self.place_oms_entry_order(signal_info, order_type='MARKET')
        for trade in trade_set:
            #print('trade =====', trade)
            trade_seq = trade['trade_seq']
            for leg_group in trade['leg_groups']:
                #print('leg_group =====', leg_group)
                leg_group_id = leg_group['lg_id']
                """
                if (strategy_id, signal_id, trade_seq, leg_group_id) in self.position_book.keys():
                    lg_entries = [key for key in list(self.position_book.keys()) if leg_group_id in key[3]]
                    new_leg_group_id = leg_group_id + '_' + repr(len(lg_entries))
                    self.position_book[(strategy_id, signal_id, trade_seq, new_leg_group_id)] = self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]
                """
                if (strategy_id, signal_id, trade_seq, leg_group_id) not in self.position_book.keys():
                    self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)] = {}
                    self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['order_book'] = []
                    self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'] = {}
                    for leg in leg_group['legs']:
                        full_code = leg['instrument']['full_code']
                        order_type = leg['order_type']
                        leg_id = leg['leg_id']
                        #print('leg_id adding 0', leg_id)
                        qty = abs(leg['quantity'])
                        side = get_broker_order_type(order_type)
                        order_time = datetime.fromtimestamp(self.last_times[full_code]).strftime("%Y-%m-%d %H:%M:%S")
                        trade_date = datetime.fromtimestamp(self.last_times[full_code]).strftime("%Y-%m-%d")
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id] = {'full_code': full_code, 'symbol': leg['instrument']['symbol'], 'qty': qty, 'side': side, 'entry_time':self.last_times[full_code], 'entry_price': self.ltps[full_code], 'exit_time':None, 'exit_price': None, 'curr_qty': get_broker_order_type(order_type) * qty, 'un_realized_pnl': 0, 'realized_pnl': 0}
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['order_book'].append([self.last_times[full_code], trade_seq, leg_group_id, full_code, leg_id, order_type, qty, self.ltps[full_code]])
                        if self.dummy_broker is not None:
                            self.dummy_broker.place_order(strategy_id, signal_id, trade_seq, full_code, side, self.ltps[full_code], qty, trade_date, order_time)
        #print("algo port position book===", self.position_book)

    def strategy_exit_signal(self, signal_info, exit_at=None):
        print('########################################## algo port strategy_exit_signal')
        #print("exiting ")
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trade_set = signal_info['trade_set']
        oms_order_info = {'strategy_id': signal_info['strategy_id'], 'signal_id': signal_info['signal_id'], 'trade_set': []}

        for trade in trade_set:
            #print('trade =====', trade)
            trade_seq = trade['trade_seq']
            oms_trade_info = {'trade_seq': trade_seq, 'leg_groups': []}
            for leg_group in trade['leg_groups']:
                leg_group_id = leg_group['lg_id']
                oms_leg_group_info = {'lg_id': leg_group_id, 'legs': []}
                #print('trade_seq leg_group =====', trade_seq, leg_group_id)
                for leg in leg_group['legs']:
                    full_code = leg['instrument']['full_code']
                    asset = leg['instrument']['asset']
                    kind = leg['instrument']['kind']
                    is_option_instrument = kind in ['CE', 'PE']
                    leg_id = leg['leg_id']
                    #print('leg_id adding 0', leg_id)
                    qty = abs(leg['quantity'])
                    l_time = self.last_times[full_code]
                    l_price = self.ltps[full_code]

                    if leg_id in self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position']:
                        order_info = self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]
                        if exit_at == 'low':
                            asset_book = self.market_book.get_asset_book(asset)
                            lowest_candle = asset_book.get_lowest_candle(full_code, after_ts=order_info['entry_time'], is_option=is_option_instrument)
                            if lowest_candle is not None:
                                l_time = lowest_candle['timestamp']
                                l_price = lowest_candle['close']
                        elif exit_at == 'high':
                            asset_book = self.market_book.get_asset_book(asset)
                            highest_candle = asset_book.get_highest_candle(full_code, after_ts=order_info['entry_time'], is_option=is_option_instrument)
                            if highest_candle is not None:
                                l_time = highest_candle['timestamp']
                                l_price = highest_candle['close']

                        #print('order_info=====', order_info)
                        qty = order_info['qty'] if qty == 0 else qty
                        #order_id = order_info['order_id']
                        exit_order_type = get_exit_order_type(order_info['side'])
                        order_time = datetime.fromtimestamp(l_time).strftime("%Y-%m-%d %H:%M:%S")
                        trade_date = datetime.fromtimestamp(l_time).strftime("%Y-%m-%d")
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['curr_qty'] += get_broker_order_type(exit_order_type) * qty
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['realized_pnl'] += get_broker_order_type(exit_order_type) * qty * (self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['entry_price'] - l_price)
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['un_realized_pnl'] = get_broker_order_type(exit_order_type) * self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['curr_qty'] * (self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['entry_price'] - l_price)
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['exit_time'] = l_time
                        self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id]['exit_price'] = l_price
                        #print(self.position_book[(strategy_id, signal_id, trade_seq, leg_group_id)]['position'][leg_id])
                        if exit_at is None:
                            oms_leg_info = copy.deepcopy(leg)
                            oms_leg_info['order_type'] = exit_order_type
                            oms_leg_info['quantity'] = qty
                            oms_leg_info['instrument']['symbol'] = order_info['symbol']
                            oms_leg_group_info['legs'].append(oms_leg_info)
                        if self.dummy_broker is not None:
                            self.dummy_broker.place_order(strategy_id, signal_id, leg_id, full_code, exit_order_type,
                                                          l_price, qty, trade_date, order_time)
                oms_trade_info['leg_groups'].append(oms_leg_group_info)
            oms_order_info['trade_set'].append(oms_trade_info)
        self.place_oms_exit_order(oms_order_info, order_type='MARKET')
        time.sleep(0.1)

    def get_order_info_from_signal_info(self, signal_info):
        symbol = signal_info['symbol']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trigger_seq = signal_info['leg_seq']
        qty = signal_info['qty']
        if trigger_seq in self.position_book[(symbol, strategy_id, signal_id)]['position']:
            order_info = self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]
        else:
            order_info = {}
        return order_info

    def market_close_for_day(self):
        position_book = {}
        for (strategy_id, signal_id, trade_seq, leg_group_id), sig_details in self.position_book.items():
            tot_qty = 0
            for leg_id in sig_details['position'].keys():
                tot_qty += abs(sig_details['position'][leg_id]['curr_qty'])
            if tot_qty:
                position_book[(strategy_id, signal_id, trade_seq, leg_group_id)] = sig_details
        self.cache.set('algo_pm', position_book)


    def reached_risk_limit(self, strat_id):
        return False


    def evaluate_risk(self):
        pnl = 0
        for key, str_details in self.position_book.items():
            for trigger in str_details['position'].values():
                symbol = trigger['full_code']
                exit_order_type = get_exit_order_type(trigger['side'])
                trigger['un_realized_pnl'] = exit_order_type * abs(trigger['curr_qty']) * (trigger['entry_price'] - self.ltps[symbol])
                #print("trigger['un_realized_pnl']", trigger['un_realized_pnl'])
                #print(exit_order_type, trigger['curr_qty'], trigger['entry_price'], self.ltps[key[0]])
