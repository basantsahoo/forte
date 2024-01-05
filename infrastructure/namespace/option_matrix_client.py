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
from db.market_data import get_prev_day_avg_volume
sio = socketio.Client(reconnection_delay=5)
from option_market.utils import get_average_volume_for_day

class OptionMatrixClient(socketio.ClientNamespace):
    def __init__(self, namespace=None, asset='NIFTY'):
        socketio.ClientNamespace.__init__(self, namespace)
        self.asset = asset
        option_matrix = OptionMatrix(asset, feed_speed=1, throttle_speed=1, live_mode=True, volume_delta_mode=True, print_cross_stats=True)
        #throttler = OptionFeedThrottler(option_matrix, feed_speed=1, throttle_speed=1)
        #option_matrix.option_data_throttler = throttler
        self.option_matrix = option_matrix
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


    def on_set_trade_date_old(self, trade_day):
        print('algo client set_trade_day', trade_day)
        self.trade_day = trade_day #'2024-01-03'
        self.trade_day = '2024-01-04'
        avg_volume_df = get_prev_day_avg_volume(self.asset, self.trade_day)
        #print(avg_volume_df.to_dict("record"))

        self.option_matrix.process_avg_volume(self.trade_day, avg_volume_df.to_dict("record"))
        self.request_data()

    def on_set_trade_date(self, trade_day):
        print('algo client set_trade_day', trade_day)
        self.trade_day = trade_day #'2024-01-03'
        #self.trade_day = '2024-01-04'
        closing_oi_df = get_prev_day_avg_volume(self.asset, self.trade_day)
        #print(closing_oi_df['avg_volume'].sum())
        closing_oi_df = closing_oi_df[['instrument', 'closing_oi']]
        self.option_matrix.process_closing_oi(self.trade_day, closing_oi_df.to_dict("record"))
        avg_volume_recs = get_average_volume_for_day(self.asset, self.trade_day)
        #print(avg_volume_recs)
        #print(avg_volume_df.to_dict("record"))

        self.option_matrix.process_avg_volume(self.trade_day, avg_volume_recs)
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
        """
        all_ts = set([rec['timestamp'] for rec in hist_recs])

        filtered_recs =[rec for rec in hist_recs if rec['timestamp'] == min(all_ts)]
        print(filtered_recs)
        """
        #time.sleep(1500)
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
        #self.option_matrix.process_feed_without_signal([feed])

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
