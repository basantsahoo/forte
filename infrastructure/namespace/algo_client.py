import time
import socketio
from arc.algo_settings import algorithm_setup
from arc.data_interface import AlgorithmIterface
from dynamics.profile.utils import NpEncoder
import json
import pandas as pd
from infrastructure.namespace.market_client import MarketClient
from servers.server_settings import feed_socket_service
enabled_symbols = list(algorithm_setup.keys())

sio = socketio.Client(reconnection_delay=5)

class AlgoClient(socketio.ClientNamespace):
    def __init__(self, namespace=None):
        socketio.ClientNamespace.__init__(self, namespace)
        self.algo_interface = AlgorithmIterface(self)
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = MarketClient('/livefeed', ['NIFTY'])
        self.c_sio.register_namespace(ns)
        ns.on_tick_data = self.on_tick_data
        ns.on_atm_option_feed = self.on_atm_option_feed
        ns.on_hist = self.on_hist
        ns.on_all_option_data = self.on_option_tick_data
        ns.on_hist_option_data = self.on_hist_option_data
        ns.on_set_trade_date = self.on_set_trade_date
        self.request_data = ns.request_data

    def refresh(self):
        self.algo_interface.clean()
        self.algo_interface = AlgorithmIterface(self)

    def on_set_trade_date(self, trade_day):
        print('algo client set_trade_day', trade_day)
        self.algo_interface.set_trade_date(trade_day)
        self.request_data()

    def on_tick_data(self, feed):
        #print('on_price' , feed)
        self.algo_interface.on_tick_price(feed)

    def on_hist_option_data(self, feed):
        print('hist option data+++++++++++++++++++++')
        symbol = feed['symbol']
        recs = feed['data']
        f_recs = {}
        for rec in recs:
            inst = str(rec['strike'])+"_"+rec['type']
            rec['open'] = rec['ltp']
            rec['high'] = rec['ltp']
            rec['low'] = rec['ltp']
            rec['close'] = rec['ltp']
            rec['instrument'] = inst
        b_df = pd.DataFrame(recs)
        ts_list = list(b_df['ltt'].unique())
        ts_list.sort()
        #print(ts_list)

        hist_recs = []
        for ts in ts_list:
            s_df = b_df[b_df['ltt'] == ts][['instrument', 'oi', 'volume', 'open', 'high', 'low', 'close']]
            s_df.set_index('instrument', inplace=True)
            recs_kk = s_df.to_dict('index')
            #print(recs_kk)
            hist_recs.append({'timestamp': int(ts // 60 * 60) + 60, 'symbol': symbol, 'records': recs_kk})

        #print('hist options feed', feed)
        self.algo_interface.on_hist_option_price({'symbol': symbol, 'hist': hist_recs})

    def on_option_tick_data(self, feed):
        if type(feed) == str:
            feed = json.loads(feed)
        symbol = feed['symbol']
        recs = feed['data']
        recs_mid = int(len(recs)/2)
        ts = recs[recs_mid]['ltt']
        epoch_minute = int(ts // 60 * 60) + 60
        f_recs = {}
        for rec in recs:
            rec['close'] = rec['ltp']
            inst = str(rec['strike'])+"_"+rec['type']
            f_recs[inst] = rec

        self.algo_interface.on_option_tick_data({'timestamp': epoch_minute, 'symbol': symbol, 'records': f_recs})

    def on_hist(self, feed):
        print('on hist price+++++++++++++++++++++')
        self.algo_interface.on_hist_price(feed)

    def on_atm_option_feed(self, feed):
        pass
        # print('algo atm_option_feed =========================', feed)
        #self.portfolio_manager.option_price_input(feed)

    def on_connect(self):
        print('Algo runner  connected to oms')
        """
        for symbol in enabled_symbols:
            self.emit('join_tick_feed', symbol)
        self.emit('join_oms')
        """

    def on_oms_entry_order(self, order_info):
        print('Algo oms entry placed')
        self.emit('place_oms_entry_order', order_info)

    def on_oms_exit_order(self, order_info):
        print('Algo oms exit placed')
        self.emit('place_oms_exit_order', order_info)

    def on_oms_entry_success(self, order_info):
        print('Algo oms entry success', order_info)

    def on_oms_exit_success(self, order_info):
        print('Algo oms exit success', order_info)

    def on_pattern_signal(self, pattern_info):
        #print('on_pattern_signal', pattern_info)
        p_tmp = json.dumps(pattern_info, cls=NpEncoder)
        self.emit('send_pattern_signal', p_tmp)

    def on_disconnect(self):
        pass

    def connect_feed(self):
        try:
            self.c_sio.connect(feed_socket_service, wait_timeout=100, auth={'internal_app_id': 'FEEDTD136148'})
            fetcher_started = True
            print('fetcher success')
        except Exception as e:
            print('connection fail')
            print(e)
            time.sleep(2)
            self.connect_feed()
    """
    This one doesn't work because separate sio
    
    def connect_to_oms(self):
        try:
            sio.connect('http://localhost:8081/', wait_timeout=100, auth={'internal_app_id': 'CALG136148'})
            # sio.emit('join_feed', default_symbols[0])
            print('oms connection success')
        except Exception as e:
            print('oms connection fail')
            print(e)
            time.sleep(2)
            self.connect_to_oms()
    """