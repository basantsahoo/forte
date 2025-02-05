from datetime import datetime
from helper.utils import get_broker_order_type, get_exit_order_type
from arc.dummy_broker import DummyBroker
from servers.server_settings import cache_dir
from diskcache import Cache

class AlgoPortfolioManager:
    def __init__(self, place_live_orders=False, data_interface=None):
        self.cache = Cache(cache_dir + 'algo_pm_cache')
        self.ltps = {}
        self.last_times = {}
        self.position_book = self.cache.get('algo_pm', {})
        self.broker = None
        self.strategy_order_map = {}
        self.broker = None
        self.dummy_broker = None
        self.data_interface = data_interface
        self.pending_orders = {}
        self.pending_order_seq = 0
        self.executed_orders = 0

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
        self.evaluate_risk()
        self.monitor_position()

    def monitor_position(self):
        pass

    def place_oms_entry_order(self, strategy_id, symbol, order_side,order_id, qty, option_signal,cover):
        #print('going to place place_oms_entry_order', strategy_id, symbol, order_side,order_id,qty)
        qty = abs(qty)
        if self.data_interface is not None:
            self.data_interface.place_entry_order(symbol, order_side, qty, strategy_id, order_id, 'MARKET', option_signal, cover)

    def place_oms_exit_order(self, strategy_id, symbol, order_side, order_id, qty, option_signal):
        #print('going to place place_oms_exit_order', strategy_id, symbol, order_side, order_id,qty)
        qty = abs(qty)
        if self.data_interface is not None:
            self.data_interface.place_exit_order(symbol, order_side, qty, strategy_id, order_id, 'MARKET', option_signal)


    def strategy_entry_signal(self, signal_info, option_signal=False):
        print('########################################## algo port strategy_entry_signal')
        #print("algo port signal info===", signal_info)

        symbol = signal_info['symbol']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        order_type = signal_info['order_type']
        cover = signal_info.get('cover',0)
        total_quantity = sum([trig['qty'] for trig in signal_info['legs']])
        self.executed_orders += 1
        order_id = 'AL' + str(self.executed_orders)
        side = get_broker_order_type(order_type)
        self.place_oms_entry_order(strategy_id, symbol, side, order_id, total_quantity, option_signal, cover)
        #print('strategy_entry_signal')
        #print(symbol, id, trigger_id,  order_type, qty)



        if (symbol, strategy_id, signal_id) not in self.position_book.keys():
            self.position_book[(symbol, strategy_id, signal_id)] = {}
            self.position_book[(symbol, strategy_id, signal_id)]['order_book'] = []
            self.position_book[(symbol, strategy_id, signal_id)]['position'] = {}
        for trigger in signal_info['legs']:
            trigger_seq = trigger['seq']
            qty = abs(trigger['qty'])
            if trigger_seq not in self.position_book[(symbol, strategy_id, signal_id)]['position']:
                order_time = datetime.fromtimestamp(self.last_times[symbol]).strftime("%Y-%m-%d %H:%M:%S")
                trade_date = datetime.fromtimestamp(self.last_times[symbol]).strftime("%Y-%m-%d")
                self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq] = {'qty': qty, 'side': side, 'entry_time':self.last_times[symbol], 'entry_price': self.ltps[symbol], 'exit_time':None, 'exit_price': None, 'curr_qty': get_broker_order_type(order_type) * qty, 'un_realized_pnl': 0, 'realized_pnl': 0, 'order_id':order_id}
                self.position_book[(symbol, strategy_id, signal_id)]['order_book'].append([self.last_times[symbol], trigger_seq, order_type, qty, self.ltps[symbol]])
                if self.dummy_broker is not None:
                    self.dummy_broker.place_order(strategy_id, signal_id, trigger_seq, symbol, side, self.ltps[symbol], qty, trade_date, order_time)
        #print("algo port position book===", self.position_book)

    def strategy_exit_signal(self, signal_info, candle=None, option_signal=False):
        print('##########################################algo port strategy_exit_signal')
        #print(signal_info)

        symbol = signal_info['symbol']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trigger_seq = signal_info['leg_seq']
        qty = signal_info['qty']

        #print('strategy exit signal', qty)
        l_time = self.last_times[symbol]
        l_price = self.ltps[symbol]
        if candle is not None:
            l_time = candle['timestamp']
            l_price = candle['close']

        if trigger_seq in self.position_book[(symbol, strategy_id, signal_id)]['position']:
            order_info = self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]
            qty = order_info['qty'] if qty == 0 else qty
            order_id = order_info['order_id']
            exit_order_type = get_exit_order_type(order_info['side'])
            order_time = datetime.fromtimestamp(l_time).strftime("%Y-%m-%d %H:%M:%S")
            trade_date = datetime.fromtimestamp(l_time).strftime("%Y-%m-%d")
            self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['curr_qty'] += get_broker_order_type(exit_order_type) * qty
            self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['realized_pnl'] += get_broker_order_type(exit_order_type) * qty * (self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['entry_price'] - l_price)
            self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['un_realized_pnl'] = get_broker_order_type(exit_order_type) * self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['curr_qty'] * (self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['entry_price'] - l_price)
            self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['exit_time'] = l_time
            self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq]['exit_price'] = l_price
            print(self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq])
            if candle is None:
                self.place_oms_exit_order(strategy_id, symbol, exit_order_type, order_id, qty, option_signal)
            if self.dummy_broker is not None:
                self.dummy_broker.place_order(strategy_id, signal_id, trigger_seq, symbol, exit_order_type, l_price, qty, trade_date, order_time)

    def market_close_for_day(self):
        position_book = {}
        for (symbol, strategy_id, signal_id), sig_details in self.position_book.items():
            tot_qty = 0
            for trigger_seq in sig_details['position'].keys():
                tot_qty += sig_details['position'][trigger_seq]['curr_qty']
            if tot_qty:
                position_book[(symbol, strategy_id, signal_id)] = sig_details

        self.cache.set('algo_pm', position_book)


    def reached_risk_limit(self, strat_id):
        return False


    def evaluate_risk(self):
        pnl = 0
        for key, str_details in self.position_book.items():
            for trigger in str_details['position'].values():
                exit_order_type = get_exit_order_type(trigger['side'])
                trigger['un_realized_pnl'] = exit_order_type * abs(trigger['curr_qty']) * (trigger['entry_price'] - self.ltps[key[0]])
                #print("trigger['un_realized_pnl']", trigger['un_realized_pnl'])
                #print(exit_order_type, trigger['curr_qty'], trigger['entry_price'], self.ltps[key[0]])
