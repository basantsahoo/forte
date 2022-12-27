import socketio
import asyncio
import time
import requests
import rx
import rx.operators as ops
from fyers_api import fyersModel
from fyers_api import accessToken
from fyers_api.Websocket import ws
from fyers.historical_data import FyersFeed
from fyers.authenication import get_access_token
from config import live_feed, back_test_day
from fyers.settings import app_id, secret_key
from settings import  log_dir
from db.db_engine import get_db_engine
from db.market_data import get_daily_tick_data
import helper.utils as helper_utils


"""
Fyers socket for live tick
"""
default_symbols = ['NSE:NIFTY50-INDEX', 'NSE:NIFTYBANK-INDEX']

sio = socketio.Client(reconnection_delay=5)
class FyersLiveFeed(socketio.ClientNamespace):
    def __init__(self,namespace=None):
        socketio.ClientNamespace.__init__(self,namespace)
        self.fyer_access_token = ''
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.fyersSocket = None
        self.obs = None
        self.price_lst = []
        if live_feed:
            self.fyer_access_token = get_access_token()
            print(self.fyer_access_token)

    def get_data_original(self, sym, trade_day):
        tick_df = get_daily_tick_data(sym, trade_day)
        #print(tick_df.head())
        tick_df['symbol'] = sym
        converted = tick_df.to_dict("records")
        print(converted[0:5])
        print(len(converted))
        return (x for x in converted)

    def get_data(self, sym, trade_day):
        import numpy as np
        import time
        from random import randrange, uniform
        import numpy as np
        from datetime import datetime
        import pytz
        tz = pytz.timezone('Asia/Kolkata')
        now = tz.localize(datetime.now(), is_dst=None)
        now = now.replace(hour=9, minute=15, second=0, microsecond=0)
        start_time = 1658979900  # int(now.timestamp())
        end_time = start_time + 6.25 * 60 * 60

        mu = 0.0005
        sigma = 0.0001
        dt = 1 / (6.25 * 60 * 60)
        np.random.seed(100)

        nifty_0 = 39000 if 'BANK' in sym else 18000
        returns = np.random.normal(loc=mu * dt, scale=sigma, size=int(6.25 * 60 * 60))
        nifty_price = nifty_0 * (1 + returns).cumprod()
        nifty_ticks = (
            {'symbol': 'NSE:NIFTYBANK-INDEX' if 'BANK' in sym else 'NSE:NIFTY50-INDEX', 'timestamp': x, 'close': np.round(nifty_price[x - start_time], 2),
             'open': np.round(nifty_price[x - start_time], 2), 'high': np.round(nifty_price[x - start_time], 2),
             'low': np.round(nifty_price[x - start_time], 2), 'volume': 0} for x in
            range(start_time, int(end_time)))

        return nifty_ticks

    def price_received_live(self,feed):
        #print(feed)
        try:
            self.emit('input_feed', feed)
        except Exception as e:
            print(e)
            print('Error sending data to server')


    async def fyer_connect(self):
        print('fyer_connect+++++++++++++++++++++++++++++++++++')
        symbols =  [helper_utils.get_fyers_index_symbol(symbol) for symbol in default_symbols]
        data_type = "symbolData"
        self.fyersSocket = ws.FyersSocket(access_token=app_id + ":" + self.fyer_access_token, run_background=False, log_path=log_dir)
        self.fyersSocket.websocket_data = self.price_received_live
        self.fyersSocket.subscribe(symbol=symbols, data_type=data_type)

    def on_connect(self):
        #global counter
        #counter += 1
        #print('counter on_connect', counter)
        print('I am connected')
        if live_feed:
            if self.fyersSocket is None:
                self.loop.run_until_complete(self.fyer_connect())
        else:
            self.price_lst = []
            for sym in default_symbols:
                self.price_lst.append(self.get_data(sym, back_test_day))
            self.obs = rx.interval(1).pipe(ops.map(lambda i: next(self.get_price())))
            self.obs.subscribe(on_next=lambda s: self.price_received_local(s))
        print('I am connected as well')

    def on_disconnect(self):
        if live_feed:
            #self.fyersSocket.unsubscribe(default_symbols)
            #self.fyersSocket.websocket_data = None
            #self.fyersSocket = None
            pass
        else:
            #self.obs.run()
            self.obs = None



    def price_received_local(self,feed):
        print('priceReceived local+++++++++++++++')
        #print(feed)
        try:
            self.emit('input_feed', feed)
        except Exception as e:
            print(e)
            print('Error sending data to server')


    def get_price(self):
        yield [next(pl) for pl in self.price_lst ]


def connect_to_server():
    #global counter
    #counter +=1
    #print('counter connect_to_server', counter)
    try:
        sio.connect('http://localhost:8080/',  wait_timeout=100, auth={'internal_app_id':'FEEDFY136148'})
        print('connection success')
    except Exception as e:
        print('connection fail')
        print(e)
        time.sleep(2)
        connect_to_server()



def stop():
    sio.disconnect()


def start():
    #global counter
    #counter +=1
    #print('counter start', counter)

    ns = FyersLiveFeed('/livefeed')
    sio.register_namespace(ns)
    connect_to_server()

""" These can be removed"""
price_lst2 = []
counter = 0
def get_data_2(sym, trade_day):
    tick_df = get_daily_tick_data(sym, trade_day)
    tick_df['symbol'] = sym
    converted = tick_df.to_dict("records")
    print(len(converted))
    return (x for x in converted)

def get_price():
    global price_lst2
    yield [next(pl) for pl in price_lst2 ]

def price_received_local(feed):
    print('priceReceived+++++++++++++++')
    print(feed)

    try:
        sio.emit('input_feed', feed)
    except Exception as e:
        print(e)
        print('Error sending data to server')

def test_run_hist_data():
    if not live_feed:
        global price_lst2
        price_lst2 = []
        for sym in default_symbols:
            price_lst2.append(get_data_2(sym, back_test_day))
        #gen = get_price()
        obs = rx.interval(1).pipe(ops.map(lambda i: next(get_price())))
        obs.subscribe(on_next=lambda s: price_received_local(s))
        while True:
            pass
