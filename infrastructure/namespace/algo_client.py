import time
import os
from settings import market_profile_db
import socketio
import asyncio
from infrastructure.arc.algo_settings import algorithm_setup
from infrastructure.arc.data_interface import AlgorithmIterface
import asyncio
from dynamics.profile.utils import NpEncoder
import json
import pytz
from datetime import datetime
from infrastructure.namespace.market_client import MarketClient
enabled_symbols = list(algorithm_setup.keys())
print(enabled_symbols)

sio = socketio.Client(reconnection_delay=5)

class AlgoClient(socketio.ClientNamespace):
    def __init__(self,namespace=None):
        socketio.ClientNamespace.__init__(self, namespace)
        self.algo_interface = AlgorithmIterface(self)
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = MarketClient('/livefeed', ['NIFTY'])
        self.c_sio.register_namespace(ns)
        ns.on_tick_data = self.on_tick_data
        ns.on_atm_option_feed = self.on_atm_option_feed

    def refresh(self):
        self.algo_interface.clean()
        self.algo_interface = AlgorithmIterface(self)

    def on_tick_data(self, feed):
        #print('on_price' , feed)
        self.algo_interface.on_tick_price(feed)

    def on_atm_option_feed(self, feed):
        print('algo atm_option_feed =========================', feed)
        #self.portfolio_manager.option_price_input(feed)

    def on_hist(self, hist):
        print(hist)
        pass


    def on_connect(self):
        print('Algo runner  connected')
        for symbol in enabled_symbols:
            self.emit('join_tick_feed', symbol)
        self.emit('join_oms')

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
            self.c_sio.connect('http://localhost:8080/', wait_timeout=100, auth={'internal_app_id': 'FEEDTD136148'})
            fetcher_started = True
            print('fetcher success')
        except Exception as e:
            print('connection fail')
            print(e)
            time.sleep(2)
            self.connect_feed()

    def connect_to_oms(self):
        try:
            sio.connect('http://localhost:8081/', wait_timeout=100, auth={'internal_app_id': 'CALG136148'})
            # sio.emit('join_feed', default_symbols[0])
            print('oms connection success')
        except Exception as e:
            print('oms connection fail')
            print(e)
            time.sleep(2)
            connect_to_oms()
