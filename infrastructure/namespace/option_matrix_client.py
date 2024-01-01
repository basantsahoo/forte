import time
import socketio
from arc.algo_settings import algorithm_setup
import json
import pandas as pd
from infrastructure.namespace.market_client import OptionMatrixMarketClient
from option_market.option_matrix import OptionMatrix
from option_market.throttlers import OptionFeedThrottler
from servers.server_settings import feed_socket_service
enabled_symbols = list(algorithm_setup.keys())
from entities.trading_day import TradeDateTime

sio = socketio.Client(reconnection_delay=5)

class OptionMatrixClient(socketio.ClientNamespace):
    def __init__(self, namespace=None):
        socketio.ClientNamespace.__init__(self, namespace)
        option_matrix = OptionMatrix(feed_speed=1, throttle_speed=1, live_mode=True, volume_delta_mode=True)
        #throttler = OptionFeedThrottler(option_matrix, feed_speed=1, throttle_speed=1)
        #option_matrix.option_data_throttler = throttler
        self.option_matrix = option_matrix
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = OptionMatrixMarketClient('/livefeed', ['NIFTY'])
        self.c_sio.register_namespace(ns)
        ns.on_all_option_data = self.on_option_tick_data
        ns.on_hist_option_data = self.on_hist_option_data
        ns.on_set_trade_date = self.on_set_trade_date
        ns.on_tick_data = self.on_tick_data
        ns.on_hist = self.on_hist

        self.request_data = ns.request_data
        self.trade_day = None


    def on_set_trade_date(self, trade_day):
        print('algo client set_trade_day', trade_day)
        self.trade_day = trade_day
        self.request_data()

    def map_to_option_recs(self, feed):
        #print(feed)
        recs = feed['data']
        f_recs = []
        for rec in recs:
            fdd = {
                'instrument': str(rec['strike']) + "_" + rec['type'],
                'ion': str(rec['ltp']) + '|' + str(rec['volume']) + '|' + str(rec['oi']),
                'timestamp' : rec['ltt'],
                'trade_date': self.trade_day
            }
            f_recs.append(fdd)
        b_df = pd.DataFrame(f_recs)
        b_df.sort_values(by=['timestamp'])
        hist_recs = b_df.to_dict("records")
        return hist_recs



    def on_hist_option_data(self, feed):
        print('hist option data+++++++++++++++++++++')
        hist_recs = self.map_to_option_recs(feed)
        #print(hist_recs)
        self.option_matrix.process_option_feed(hist_recs)
        """
        self.option_matrix.process_feed_without_signal(hist_recs)
        self.option_matrix.generate_signal()
        """
    def on_option_tick_data(self, feed):
        hist_recs = self.map_to_option_recs(feed)
        self.option_matrix.process_option_feed(hist_recs)


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
        feed = self.map_to_spot_recs(list(feed.values())[0])
        self.option_matrix.process_feed_without_signal([feed])

    def on_hist(self, feed):
        print('on_hist+++++++++')
        feed = json.loads(feed)
        hist = feed['hist']
        hist_values = hist.values()
        hist_feeds = [self.map_to_spot_recs(x) for x in hist_values]
        #print(hist_feeds)
        for feed in hist_feeds:
            feed['timestamp'] = TradeDateTime.get_epoc_minute(feed['timestamp'])
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        t_series = day_capsule.cross_analyser.get_ts_series()
        #print(t_series)
        filtered_hist_feeds = [feed for feed in hist_feeds if feed['timestamp'] in t_series]
        #self.option_matrix.process_feed_without_signal(filtered_hist_feeds)
        #self.option_matrix.generate_signal()

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
