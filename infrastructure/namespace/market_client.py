import time
import socketio
import asyncio


class MarketClient(socketio.ClientNamespace):
    def __init__(self, namespace=None, subscribed_symbols=[]):
        socketio.ClientNamespace.__init__(self, namespace)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.subscribed_symbols = subscribed_symbols
        if not subscribed_symbols:
            self.subscribed_symbols = ['NIFTY']
        """
        self.sio = socketio.Client(reconnection_delay=5)
        ns = socketio.ClientNamespace(feed)
        self.sio.register_namespace(ns)
        """
    def on_tick_data(self, feed):
        pass
        #print('on_price' , feed)

    def on_hist(self, feed):
        pass
        #print('on_hist' , feed)

    def on_hist_option_data(self, feed):
        pass

    def on_atm_option_feed(self, feed):
        #print('on_atm_option_feed', feed)
        pass

    def on_all_option_data(self, feed):
        pass

    def on_connect(self):
        print('Market client  connected')
        self.emit('get_trade_date')

    def on_set_trade_date(self, trade_day):
        print('Market on_set_trade_date')

    def request_data(self):
        for symbol in self.subscribed_symbols:
            self.emit('get_price_chart_data', symbol)
            time.sleep(2)
            self.emit('get_hist_option_data', symbol)
            time.sleep(2)
        for symbol in self.subscribed_symbols:
            self.emit('join_tick_feed', symbol)
            self.emit('request_data', symbol)
            self.emit('join_options_feed', symbol)
        self.emit('join_tick_feed', 'atm_option_room')

    def on_connect_2(self):
        print('Market client  connected')
        for symbol in self.subscribed_symbols:
            self.emit('get_price_chart_data', symbol)
            time.sleep(12)
            self.emit('get_hist_option_data', symbol)
            time.sleep(5)
        for symbol in self.subscribed_symbols:
            self.emit('join_tick_feed', symbol)
            self.emit('request_data', symbol)
            self.emit('join_options_feed', symbol)
        self.emit('join_tick_feed', 'atm_option_room')

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



class OptionMatrixMarketClient(MarketClient):
    def request_hist_data(self):
        for symbol in self.subscribed_symbols:
            self.emit('get_hist_spot_data', symbol)
            time.sleep(2)
            self.emit('get_hist_option_data', symbol)
            time.sleep(1)

    def request_live_data(self):
        for symbol in self.subscribed_symbols:
            self.emit('join_tick_feed', symbol)
            self.emit('join_options_feed', symbol)
            self.emit('join_tick_feed', 'atm_option_room')
