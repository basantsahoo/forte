import time
import os
from settings import market_profile_db
import socketio
import asyncio
from arc.algo_settings import algorithm_setup
from arc.data_interface import AlgorithmIterface
import asyncio
from profile.utils import NpEncoder
import json
import pytz
from datetime import datetime
enabled_symbols = list(algorithm_setup.keys())
print(enabled_symbols)


class MarketClient:
    def __init__(self):
        self.sio = socketio.Client(reconnection_delay=5)
        ns = socketio.ClientNamespace('/livefeed')
        self.sio.register_namespace(ns)

    def on_tick_data(self, feed):
        print('on_price' , feed)

    def on_connect(self):
        print('Algo runner  connected')
        for symbol in enabled_symbols:
            self.emit('join_tick_feed', symbol)

    def on_disconnect(self):
        pass

    def connect_to_server(self):
        try:
            self.sio.connect('http://localhost:8080/',  wait_timeout=100, auth={'internal_app_id':'CALG136148'})
            #sio.emit('join_feed', default_symbols[0])
            print('connection success')
        except Exception as e:
            print('connection fail')
            print(e)
            time.sleep(2)
            self.connect_to_server()




