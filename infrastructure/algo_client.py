import time
import os
from settings import market_profile_db
import socketio
import asyncio
from arc.algo_settings import algorithm_setup
from arc.data_interface import AlgorithmIterface
import asyncio
from dynamics.profile.utils import NpEncoder
import json
import pytz
from datetime import datetime
enabled_symbols = list(algorithm_setup.keys())
print(enabled_symbols)

sio = socketio.Client(reconnection_delay=5)
class AlgoClient(socketio.ClientNamespace):
    def __init__(self,namespace=None):
        socketio.ClientNamespace.__init__(self, namespace)
        self.algo_interface = AlgorithmIterface(self)

    def refresh(self):
        self.algo_interface.clean()
        self.algo_interface = AlgorithmIterface(self)

    def on_tick_data(self, feed):
        #print('on_price' , feed)
        self.algo_interface.on_tick_price(feed)

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

def connect_to_server():
    try:
        sio.connect('http://localhost:8080/',  wait_timeout=100, auth={'internal_app_id':'CALG136148'})
        #sio.emit('join_feed', default_symbols[0])
        print('connection success')
    except Exception as e:
        print('connection fail')
        print(e)
        time.sleep(2)
        connect_to_server()

def refresh(ns):
    #print('refresh 1')
    #loop = asyncio.get_running_loop()
    tz_ist = pytz.timezone('Asia/Kolkata')
    #clean_up = True
    while True:
        now = datetime.now(tz_ist)
        if (now.hour == 15 and now.minute >= 45) or (now.hour == 8 and now.minute >= 45):
            #print('refresh 2')
            #clean_up=False
            ns.refresh()
        sio.sleep(15*60)

def start():
    ns = AlgoClient('/livefeed')
    sio.register_namespace(ns)
    task = sio.start_background_task(refresh, ns)
    connect_to_server()


start()
#asyncio.run(start())

