import time
from datetime import datetime
from helper.utils import get_broker_order_type, root_symbol, get_broker_order_type, get_exit_order_type,get_lot_size
from infrastructure.arc.broker import BrokerLive
from infrastructure.arc.dummy_broker import DummyBroker


class AlgoPortfolioManager:
    def __init__(self, place_live_orders=False, data_interface=None):
        self.ltps = {}
        self.last_times = {}
        self.position_book = {}
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
        pass
        #self.set_dummy_broker()

    def price_input(self, input):
        #print('price input', input)
        self.ltps[input['symbol']] = input['close']
        self.last_times[input['symbol']] = input['timestamp']
        self.evaluate_risk()
        self.monitor_position()

    def option_price_input(self, option_data):
        ts = option_data['timestamp']
        option_recs = option_data['records']
        for instrument, data in option_recs.items():
            symbol = option_data['symbol'] + "_" + instrument
            self.last_times[symbol] = ts
            self.ltps[symbol] = data['close'] if 'close' in data else data['ltp']
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
        print('algo port strategy_entry_signal')
        print(signal_info)

        symbol = signal_info['symbol']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        order_type = signal_info['order_type']
        cover = signal_info.get('cover',0)
        total_quantity = sum([trig['qty'] for trig in signal_info['triggers']])
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
        for trigger in signal_info['triggers']:
            trigger_seq = trigger['seq']
            qty = abs(trigger['qty'])
            if trigger_seq not in self.position_book[(symbol, strategy_id, signal_id)]['position']:
                order_time = datetime.fromtimestamp(self.last_times[symbol]).strftime("%Y-%m-%d %H:%M:%S")
                trade_date = datetime.fromtimestamp(self.last_times[symbol]).strftime("%Y-%m-%d")
                self.position_book[(symbol, strategy_id, signal_id)]['position'][trigger_seq] = {'qty': qty, 'side': side, 'entry_time':self.last_times[symbol], 'entry_price': self.ltps[symbol], 'exit_time':None, 'exit_price': None, 'curr_qty': get_broker_order_type(order_type) * qty, 'un_realized_pnl': 0, 'realized_pnl': 0, 'order_id':order_id}
                self.position_book[(symbol, strategy_id, signal_id)]['order_book'].append([self.last_times[symbol], trigger_seq, order_type, qty, self.ltps[symbol]])
                if self.dummy_broker is not None:
                    self.dummy_broker.place_order(strategy_id, signal_id, trigger_seq, symbol, side, self.ltps[symbol], qty, trade_date, order_time)


    def strategy_exit_signal(self, signal_info, candle=None, option_signal=False):
        symbol = signal_info['symbol']
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trigger_seq = signal_info['trigger_id']
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
            if candle is None:
                self.place_oms_exit_order(strategy_id, symbol, exit_order_type, order_id, qty, option_signal)
            if self.dummy_broker is not None:
                self.dummy_broker.place_order(strategy_id, signal_id, trigger_seq, symbol, exit_order_type, l_price, qty, trade_date, order_time)


    def reached_risk_limit(self, strat_id):
        return False

    def evaluate_risk(self):
        pnl = 0
        for key, str_details in self.position_book.items():
            for trigger in str_details['position'].values():
                exit_order_type = get_exit_order_type(trigger['side'])
                trigger['un_realized_pnl'] = exit_order_type * trigger['curr_qty'] * (trigger['entry_price'] - self.ltps[key[0]])
