from arc.algo_settings import algorithm_setup

from datetime import datetime
import time
from arc.algo_portfolio import AlgoPortfolioManager
from arc.insight import InsightBook
from db.market_data import (get_all_days, get_daily_tick_data, prev_day_data, get_prev_week_candle, get_nth_day_profile_data)
import helper.utils as helper_utils
#from strategies_bkp.range_break import RangeBreakDownStrategy
#from strategies_bkp.sma_cross_over_buy import SMACrossBuy
import traceback
from research.strategies.price_action_aggregator import PatternAggregator

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

    def set_trade_date_from_time(self, epoch_tick_time):
        start_time = datetime.now()
        trade_day = helper_utils.day_from_epoc_time(epoch_tick_time)
        self.portfolio_manager = AlgoPortfolioManager(place_live_orders=True, data_interface=self)
        for symbol in list(algorithm_setup.keys()):
            insight_book = InsightBook(symbol, trade_day, record_metric=False)
            insight_book.pm = self.portfolio_manager
            self.last_epoc_minute_data[symbol] = {'timestamp': None}
            self.insight_books.append(insight_book)
            for strategy in algorithm_setup[symbol]['strategies']:
                insight_book.add_strategy(eval(strategy))
        self.trade_day = trade_day
        self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())

    def on_tick_price(self, feed):
        feed = list(feed.values())[0]
        #print(feed)
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
        if self.last_epoc_minute_data[symbol]['timestamp'] is None or (epoch_minute == self.last_epoc_minute_data[symbol]['timestamp']):
            self.last_epoc_minute_data[symbol] = feed
        else:
            for insight_book in self.insight_books:
                if insight_book.ticker == symbol:
                    #print('sending from interface')
                    insight_book.price_input_stream(self.last_epoc_minute_data[symbol])
            self.last_epoc_minute_data[symbol] = feed
        self.portfolio_manager.price_input(feed)

    def place_entry_order(self, symbol, order_side, qty, strategy_id, order_id, order_type ):
        print('place_entry_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type
                      }

        #self.socket.on_oms_entry_order(order_info)


    def place_exit_order(self, symbol, order_side, qty, strategy_id, order_id, order_type ):
        print('place_exit_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type
                      }

        #self.socket.on_oms_exit_order(order_info)

    def notify_pattern_signal(self, ticker, pattern, pattern_match_idx):
        #print('notify_pattern_signal', pattern, pattern_match_idx)
        pattern_info = {'pattern': pattern, 'symbol': ticker, 'info': pattern_match_idx}
        self.socket.on_pattern_signal(pattern_info)


