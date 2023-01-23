from arc.algo_settings import algorithm_setup
import json
from datetime import datetime
import time
from arc.algo_portfolio import AlgoPortfolioManager
#from infrastructure.arc.insight import InsightBook
from arc.insight import InsightBook
import helper.utils as helper_utils
#from live_algo.friday_candle_first_30_mins import FridayCandleBuyFullDay, FridayCandleSellFullDay


class AlgorithmIterface:
    def __init__(self, socket=None):
        self.trade_day = None
        self.socket = socket
        self.insight_books = []
        self.portfolio_manager = None
        self.last_epoc_minute_data = {}
        self.setup_in_progress = False
        #self.set_trade_date_from_time(1656386364) #remove this -- it's only for test
        print('new data interface created++++++')

    def clean(self):
        for insight_book in self.insight_books:
            insight_book.clean()
            insight_book.pm = None
        self.insight_books = []
        self.portfolio_manager = None

    def set_trade_date(self, trade_day):
        print('set_trade_date+++++++')
        start_time = datetime.now()
        self.portfolio_manager = AlgoPortfolioManager(place_live_orders=True, data_interface=self)
        for symbol in list(algorithm_setup.keys()):
            insight_book = InsightBook(symbol, trade_day, record_metric=False)
            print('insight_book created')
            insight_book.pm = self.portfolio_manager
            self.last_epoc_minute_data[symbol] = {'timestamp': None}
            self.last_epoc_minute_data[symbol+"_O"] = {'timestamp': None}
            self.insight_books.append(insight_book)

            for s_id in range(len(algorithm_setup[symbol]['strategies'])):
                print('adding strategy=====', algorithm_setup[symbol]['strategies'][s_id])
                strategy_class = eval(algorithm_setup[symbol]['strategies'][s_id])
                strategy_kwargs = algorithm_setup[symbol]['strategy_kwargs'][s_id]
                insight_book.add_strategy(strategy_class, strategy_kwargs)
            """
            for strategy in algorithm_setup[symbol]['strategies']:
                print('adding strategy +++++', strategy)
                insight_book.add_strategy(eval(strategy))
            """
            print('all strategy added+++++')
        self.trade_day = trade_day
        self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())

    def set_trade_date_from_time(self, epoch_tick_time):
        print('set_trade_date_from_time+++++++')
        start_time = datetime.now()
        trade_day = helper_utils.day_from_epoc_time(epoch_tick_time)
        self.set_trade_date(trade_day)


    def on_hist_price(self, hist_feed):
        print('di +++++ on_hist_price +++++')
        hist_feed = json.loads(hist_feed)
        symbol = hist_feed['symbol']
        hist = hist_feed['hist']
        #hist = [{**v, **{'timestamp':int(k), 'symbol':symbol}} for (k, v) in hist.items()]
        hist = [{ky: vl for ky, vl in {**v, **{'timestamp': int(k), 'symbol': symbol}}.items() if ky not in ('lt', 'ht')} for (k, v) in hist.items()]
        #print(hist)
        epoch_minute = hist[0]['timestamp']
        #print(hist[0])
        if self.trade_day is None and not self.setup_in_progress:
            self.setup_in_progress = True
            self.set_trade_date_from_time(epoch_minute)
            self.last_epoc_minute_data[symbol] = hist[-1]
            self.portfolio_manager.price_input(hist[-1])
            for insight_book in self.insight_books:
                if insight_book.ticker == symbol:
                    insight_book.hist_spot_feed(hist)

    def on_hist_option_price(self, hist_feed):
        print('di +++++ on_hist_option_price +++++', len(hist_feed['hist']))
        symbol = hist_feed['symbol']+"_O"
        hist = hist_feed['hist']
        #print(hist)
        epoch_minute = hist[0]['timestamp']
        #print(hist[0])
        if self.trade_day is None and not self.setup_in_progress:
            self.setup_in_progress = True
            self.set_trade_date_from_time(epoch_minute)
        self.last_epoc_minute_data[symbol] = hist[-1]
        self.portfolio_manager.option_price_input(hist[-1])
        time.sleep(0.5)
        for insight_book in self.insight_books:

            if insight_book.ticker == hist_feed['symbol']:
                print('sending hist to insight')
                insight_book.hist_option_feed(hist)


    def on_tick_price(self, feed):
        feed = list(feed.values())[0]
        #print('tick feed====', feed)
        epoch_tick_time = feed['timestamp']
        epoch_minute = feed['timestamp'] #int(epoch_tick_time // 60 * 60)
        symbol = feed['symbol']
        if self.setup_in_progress:
            return
        if self.trade_day is None:
            self.setup_in_progress = True
            self.set_trade_date_from_time(epoch_tick_time)
            return
        #print(self.last_epoc_minute_data[symbol]['timestamp'], epoch_minute)
        #if self.last_epoc_minute_data[symbol]['timestamp'] is None or (epoch_minute == self.last_epoc_minute_data[symbol]['timestamp']):
        if self.last_epoc_minute_data[symbol]['timestamp'] is None:
            self.last_epoc_minute_data[symbol] = feed
            return
        # new minute started so send previous minute data to insight book
        if epoch_minute != self.last_epoc_minute_data[symbol]['timestamp']:
            for insight_book in self.insight_books:
                if insight_book.ticker == symbol:
                    #print('sending from interface')
                    insight_book.spot_minute_data_stream(self.last_epoc_minute_data[symbol])
        self.last_epoc_minute_data[symbol] = feed
        self.portfolio_manager.price_input(feed)


    def on_option_tick_data(self, feed):
        epoch_tick_time = feed['timestamp']
        epoch_minute = feed['timestamp'] #int(epoch_tick_time // 60 * 60)
        symbol = feed['symbol'] + "_O"
        if self.setup_in_progress:
            return
        if self.trade_day is None:
            self.setup_in_progress = True
            self.set_trade_date_from_time(epoch_tick_time)
            return
        if self.last_epoc_minute_data[symbol]['timestamp'] is None:
            self.last_epoc_minute_data[symbol] = feed
            return
        # new minute started so send previous minute data to insight book
        if epoch_minute != self.last_epoc_minute_data[symbol]['timestamp']:
            for insight_book in self.insight_books:
                if insight_book.ticker == feed['symbol']:
                    #print('sending from interface')
                    insight_book.option_minute_data_stream(self.last_epoc_minute_data[symbol])
        self.last_epoc_minute_data[symbol] = feed
        self.portfolio_manager.option_price_input(feed)

    def place_entry_order(self, symbol, order_side, qty, strategy_id, order_id, order_type,option_flag ,cover):
        print('place_entry_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type,option_flag,cover)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type,
                      'option_flag':option_flag,
                      'cover': cover
                      }

        self.socket.on_oms_entry_order(order_info)


    def place_exit_order(self, symbol, order_side, qty, strategy_id, order_id, order_type,option_flag ):
        print('place_exit_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type,
                      'option_flag': option_flag
                      }

        self.socket.on_oms_exit_order(order_info)

    def notify_pattern_signal(self, ticker, pattern, pattern_match_idx):
        #print('notify_pattern_signal', pattern, pattern_match_idx)
        pattern_info = {'pattern': pattern, 'symbol': ticker, 'info': pattern_match_idx}
        self.socket.on_pattern_signal(pattern_info)


