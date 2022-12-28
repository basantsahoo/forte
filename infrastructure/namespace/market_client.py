import time
import os
from settings import market_profile_db
import socketio
import asyncio
import asyncio
import json
import pytz
from datetime import datetime
from infrastructure.arc.algo_settings import algorithm_setup
import asyncio
from dynamics.profile.utils import NpEncoder
import json
import pytz
from datetime import datetime
enabled_symbols = list(algorithm_setup.keys())

class MarketClient(socketio.ClientNamespace):
    def __init__(self,namespace=None, subscribed_symbols=[]):
        socketio.ClientNamespace.__init__(self, namespace)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.subscribed_symbols = subscribed_symbols
        if not subscribed_symbols:
            self.subscribed_symbols = enabled_symbols
        """
        self.sio = socketio.Client(reconnection_delay=5)
        ns = socketio.ClientNamespace(feed)
        self.sio.register_namespace(ns)
        """
    def on_tick_data(self, feed):
        print('on_price' , feed)

    def on_connect(self):
        print('Market client  connected')
        for symbol in self.subscribed_symbols:
            self.emit('join_tick_feed', symbol)

    def on_disconnect(self):
        pass

    """
    def connect_to_server(self):
        try:
            self.sio.connect('http://localhost:8080/',  wait_timeout=100, auth={'internal_app_id':'CALG136148'})
            #sio.emit('join_feed', default_symbols[0])
            print('connection success 111')
        except Exception as e:
            print('connection fail')
            print(e)
            time.sleep(2)
            self.connect_to_server()
    """



