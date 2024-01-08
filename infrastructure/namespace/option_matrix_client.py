import time
import socketio
from live_algo.algo_settings import algorithm_setup
import json
import pandas as pd
from infrastructure.namespace.market_client import OptionMatrixMarketClient
from servers.server_settings import feed_socket_service
enabled_symbols = list(algorithm_setup.keys())
from entities.trading_day import TradeDateTime
from helper.data_feed_utils import convert_hist_option_feed, convert_hist_spot_feed
sio = socketio.Client(reconnection_delay=5)
from arc.data_interface_option_matrix import AlgorithmIterface
from dynamics.profile.utils import NpEncoder

class OptionMatrixClient(socketio.ClientNamespace):
    def __init__(self, namespace=None, asset='NIFTY'):
        socketio.ClientNamespace.__init__(self, namespace)
        self.asset = asset
        self.algo_interface = AlgorithmIterface(self)
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = OptionMatrixMarketClient('/livefeed', [self.asset])
        self.c_sio.register_namespace(ns)
        ns.on_all_option_data = self.on_option_tick_data
        ns.on_hist_option_data = self.on_hist_option_data
        ns.on_set_trade_date = self.on_set_trade_date
        ns.on_tick_data = self.on_tick_data
        ns.on_hist = self.on_hist

        self.request_data = ns.request_data
        self.trade_day = None

    def refresh(self):
        self.algo_interface.clean()
        self.algo_interface = AlgorithmIterface(self)


    def on_set_trade_date(self, trade_day):
        self.trade_day = trade_day
        print('algo client set_trade_day', trade_day)
        self.algo_interface.set_trade_date(trade_day)
        self.request_data()


    def on_hist_option_data(self, feed):
        feed = convert_hist_option_feed(feed, self.trade_day)
        print('hist option data+++++++++++++++++++++')
        self.algo_interface.on_hist_option_data(feed)

    def on_option_tick_data(self, feed):
        feed = convert_hist_option_feed(feed, self.trade_day)
        self.algo_interface.on_option_tick_data(feed)


    def map_to_spot_recs(self, feed):
        #print(feed)
        fdd = {
            'instrument': 'spot',
            'ion': str(feed['open']) + '|' + str(feed['high']) + '|' + str(feed['low']) + '|' + str(feed['close']),
            'timestamp' : feed.get('timestamp', feed.get('lt')),
            'trade_date': self.trade_day
        }
        return fdd


    def on_tick_data(self, feed):
        #print(feed)
        feed = {'symbol': list(feed.values())[0]['symbol'], 'hist': feed}
        feed = convert_hist_spot_feed(feed, self.trade_day)
        self.algo_interface.on_hist_spot_data(feed)
        #self.option_matrix.process_feed_without_signal([feed])

    def on_hist(self, feed):
        feed = json.loads(feed)
        print('on_hist+++++++++')
        feed = convert_hist_spot_feed(feed, self.trade_day)


        self.algo_interface.on_hist_spot_data(feed)

    def on_pattern_signal(self, pattern_info):
        #print('on_pattern_signal', pattern_info)
        #p_tmp = json.dumps(pattern_info, cls=NpEncoder)
        p_tmp = pattern_info
        #self.emit('send_pattern_signal', p_tmp)

    def on_connect(self):
        print('Algo runner  connected to oms')
        """
        for symbol in enabled_symbols:
            self.emit('join_tick_feed', symbol)
        self.emit('join_oms')
        """

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
