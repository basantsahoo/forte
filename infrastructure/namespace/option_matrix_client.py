import time
import socketio
import json
from infrastructure.namespace.market_client import OptionMatrixMarketClient
from servers.server_settings import feed_socket_service
from entities.trading_day import TradeDateTime, NearExpiryWeek
from helper.data_feed_utils import convert_hist_option_feed, convert_hist_spot_feed
sio = socketio.Client(reconnection_delay=5)
from arc.data_interface_option_matrix import AlgorithmIterface
from arc.data_loader import MultiDayOptionDataLoader, DayHistTickDataLoader


class OptionMatrixClient(socketio.ClientNamespace):
    def __init__(self, namespace=None, asset='NIFTY', full_week=False):
        socketio.ClientNamespace.__init__(self, namespace)
        self.asset = asset
        self.algo_interface = AlgorithmIterface(self)
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = OptionMatrixMarketClient('/livefeed', [self.asset])
        self.c_sio.register_namespace(ns)
        ns.on_all_option_data = self.on_option_tick_data
        ns.on_hist_option_data = self.on_hist_option_data
        if full_week:
            ns.on_set_trade_date = self.on_set_trade_date_w_hist
        else:
            ns.on_set_trade_date = self.on_set_trade_date
        ns.on_tick_data = self.on_tick_data
        ns.on_hist = self.on_hist
        ns.on_atm_option_feed = self.on_atm_option_feed
        self.hist_tick_data_loader = DayHistTickDataLoader(asset=asset)
        self.request_day_hist_data = ns.request_hist_data
        self.request_live_data = ns.request_live_data
        self.trade_day = None
        self.hist_loaded = True

    def refresh(self):
        self.algo_interface.clean()
        self.algo_interface = AlgorithmIterface(self)

    def on_set_trade_date(self, trade_day):
        self.trade_day = trade_day
        print('algo client set_trade_day', trade_day)
        self.algo_interface.set_trade_date(trade_day)
        #self.algo_interface.load_system(trade_day=trade_day, process_signal_switch=True)
        self.request_day_hist_data()

    def on_set_trade_date_w_hist(self, trade_day):
        self.trade_day = trade_day
        print('algo client set_trade_day', trade_day)
        week = NearExpiryWeek(TradeDateTime(trade_day))
        prev_trade_days_of_week = week.get_prev_trade_days_of_week(TradeDateTime(trade_day))
        if prev_trade_days_of_week:
            self.algo_interface.load_system(process_signal_switch=False, volume_delta_mode=False)
            week_data_loader = MultiDayOptionDataLoader(asset=self.asset, trade_days=[t_day.date_string for t_day in prev_trade_days_of_week])
            while week_data_loader.data_present:
                feed_ = week_data_loader.generate_next_feed()
                if feed_:
                    if feed_:
                        if feed_['feed_type'] == 'spot':
                            self.algo_interface.on_hist_spot_data(feed_)
                        elif feed_['feed_type'] == 'option':
                            self.algo_interface.on_hist_option_data(feed_)
        self.algo_interface.load_system(trade_day=trade_day, process_signal_switch=True, volume_delta_mode=True)
        self.request_day_hist_data()

    def on_hist(self, feed):
        feed = json.loads(feed)
        print('on_hist+++++++++')#, feed)
        feed = convert_hist_spot_feed(feed, self.trade_day)
        self.hist_loaded = False
        self.hist_tick_data_loader.set_spot_ion_data(self.trade_day, feed['data'])


    def on_hist_option_data(self, feed):
        feed = convert_hist_option_feed(feed, self.trade_day)
        print('hist option data+++++++++++++++++++++')
        self.hist_loaded = False
        self.hist_tick_data_loader.set_option_ion_data(self.trade_day, feed['data'])

        self.process_hist_tick_data()

    def process_hist_tick_data(self):
        while self.hist_tick_data_loader.data_present:
            feed = self.hist_tick_data_loader.generate_next_feed()
            if feed:
                if feed['feed_type'] == 'spot':
                    self.algo_interface.on_hist_spot_data(feed)

                elif feed['feed_type'] == 'option':
                    self.algo_interface.on_hist_option_data(feed)
        self.hist_loaded = True
        self.request_live_data()

    def on_option_tick_data(self, feed):
        if self.hist_loaded:
            feed = convert_hist_option_feed(feed, self.trade_day)
            self.algo_interface.on_option_tick_data(feed)

    def on_atm_option_feed(self, feed):
        #print('on_atm_option_feed++++++')
        self.algo_interface.oms_manager.option_price_input(feed)


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
        if self.hist_loaded:
            feed = {'symbol': list(feed.values())[0]['symbol'], 'hist': feed}
            feed = convert_hist_spot_feed(feed, self.trade_day)
            self.algo_interface.on_hist_spot_data(feed)
        #self.option_matrix.process_feed_without_signal([feed])




    def on_pattern_signal(self, pattern_info):
        #print('on_pattern_signal', pattern_info)
        #p_tmp = json.dumps(pattern_info, cls=NpEncoder)
        p_tmp = pattern_info
        #self.emit('send_pattern_signal', p_tmp)

    def on_connect(self):
        print('Algo runner  connected to oms')

    def on_disconnect(self):
        pass

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
