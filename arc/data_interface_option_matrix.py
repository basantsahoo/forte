from live_algo.algo_settings import algorithm_setup
import json
from datetime import datetime
import time
from arc.algo_portfolio import AlgoPortfolioManager
from arc.oms_manager import OMSManager
from arc.option_market_book import OptionMarketBook
from arc.strategy_manager import StrategyManager
import helper.utils as helper_utils
from pathlib import Path
from entities.trading_day import TradeDateTime
from servers.server_settings import cache_dir
from diskcache import Cache
from arc.oms_manager import OMSManager

strat_config_path = str(Path(__file__).resolve().parent.parent) + "/live_algo/" + 'deployed_strategies.json'
with open(strat_config_path, 'r') as bt_config:
    strat_config = json.load(bt_config)


#from live_algo.friday_candle_first_30_mins import FridayCandleBuyFullDay, FridayCandleSellFullDay

from research.option_strategies.high_call_volume_buy import HighCallVolumeBuy
from research.option_strategies.high_put_volume_buy import HighPutVolumeBuy

class AlgorithmIterface:
    def __init__(self, socket=None):
        self.trade_day = None
        self.socket = socket
        self.market_book = None
        self.portfolio_manager = None
        self.last_epoc_minute_data = {}
        self.systems_loaded = False
        self.setup_in_progress = False
        market_cache = Cache(cache_dir + 'oms_cache')
        self.oms_manager = OMSManager(place_live_orders=True, market_cache=market_cache)
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
        assets = list(set([strategy['symbol'] for strategy in strat_config['strategies']]))
        self.portfolio_manager = AlgoPortfolioManager(place_live_orders=False, data_interface=self)
        market_book = OptionMarketBook(trade_day, assets=assets, record_metric=False, live_mode=True, volume_delta_mode=True)
        self.market_book = market_book
        market_book.pm = self.portfolio_manager
        strategy_manager = StrategyManager(market_book=market_book, record_metric=False)

        for symbol in assets:
            self.last_epoc_minute_data[symbol] = {'timestamp': None}
            self.last_epoc_minute_data[symbol+"_O"] = {'timestamp': None}
            for deployed_strategy in strat_config['strategies']:
                strategy_class = eval(deployed_strategy['class'])
                strategy_manager.add_strategy(strategy_class, deployed_strategy)
            market_book.strategy_manager = strategy_manager
            print('all strategy added+++++')
        self.trade_day = trade_day
        self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())

    def load_system(self, trade_day=None, process_signal_switch=False, volume_delta_mode=False):
        start_time = datetime.now()
        if not self.systems_loaded:
            assets = list(set([strategy['symbol'] for strategy in strat_config['strategies']]))
            self.portfolio_manager = AlgoPortfolioManager(place_live_orders=False, data_interface=self)
            market_book = OptionMarketBook(trade_day=trade_day, assets=assets, record_metric=False, live_mode=True, volume_delta_mode=volume_delta_mode)
            self.market_book = market_book
            market_book.pm = self.portfolio_manager
            strategy_manager = StrategyManager(market_book=market_book, record_metric=False)

            for symbol in assets:
                self.last_epoc_minute_data[symbol] = {'timestamp': None}
                self.last_epoc_minute_data[symbol+"_O"] = {'timestamp': None}
                for deployed_strategy in strat_config['strategies']:
                    strategy_class = eval(deployed_strategy['class'])
                    strategy_manager.add_strategy(strategy_class, deployed_strategy)
                market_book.strategy_manager = strategy_manager
                print('all strategy added+++++')
            self.systems_loaded = True
        self.market_book.strategy_manager.process_signal_switch = process_signal_switch
        self.market_book.set_volume_delta_mode(volume_delta_mode)
        self.trade_day = trade_day
        if trade_day is not None:
            self.market_book.do_day_set_up(trade_day)
            self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())


    def on_hist_spot_data(self, hist_feed):
        #print('on_hist_spot_data', hist_feed)
        symbol = hist_feed['asset']
        hist = hist_feed['data']
        pm_feed = {'feed_type': hist_feed['feed_type'], 'asset': hist_feed['asset'], 'data': hist_feed['data'][-1::]}
        self.last_epoc_minute_data[symbol] = hist[-1]
        self.portfolio_manager.feed_stream(pm_feed)
        self.market_book.feed_stream(hist_feed)

    def on_hist_option_data(self, hist_feed):
        #print('on_hist_option_data', hist_feed)
        symbol = hist_feed['asset']+"_O"
        hist = hist_feed['data']
        pm_feed = {'feed_type': hist_feed['feed_type'], 'asset': hist_feed['asset'], 'data': hist_feed['data'][-1::]}
        self.last_epoc_minute_data[symbol] = hist[-1]
        #print(self.last_epoc_minute_data[symbol])
        self.portfolio_manager.feed_stream(pm_feed)
        self.market_book.feed_stream(hist_feed)


    def on_spot_tick_data(self, feed):
        epoch_minute = TradeDateTime.get_epoc_minute(feed['data'][0]['timestamp'])
        symbol = feed['asset']
        if self.setup_in_progress:
            return
        if self.last_epoc_minute_data[symbol]['timestamp'] is None:
            self.last_epoc_minute_data[symbol] = feed['data'][0]
            return
        # new minute started so send previous minute data to insight book
        if epoch_minute > self.last_epoc_minute_data[symbol]['timestamp']:
            self.market_book.feed_stream(feed)
        self.last_epoc_minute_data[symbol] = feed['data'][0]
        self.portfolio_manager.feed_stream(feed)


    def on_option_tick_data(self, feed):
        #print('on_option_tick_data', feed)
        if self.setup_in_progress:
            return
        self.market_book.feed_stream(feed)
        self.portfolio_manager.feed_stream(feed)

    def place_entry_order(self, symbol, order_side, qty, strategy_id, order_id, order_type,option_flag ,cover):
        if self.socket.hist_loaded:
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
            resp = self.oms_manager.place_entry_order(order_info)
            print(resp)
            # Use following instead of oms_manager if oms server is running separately
            #self.socket.on_oms_entry_order(order_info)


    def place_exit_order(self, symbol, order_side, qty, strategy_id, order_id, order_type,option_flag ):
        if self.socket.hist_loaded:
            print('place_exit_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type)
            order_info = {'symbol': symbol,
                          'order_side':order_side,
                          'qty': qty,
                          'strategy_id': strategy_id,
                          'order_id': order_id,
                          'order_type': order_type,
                          'option_flag': option_flag
                          }
            resp = self.oms_manager.place_exit_order(order_info)
            print(resp)

            # Use following instead of oms_manager if oms server is running separately
            #self.socket.on_oms_exit_order(order_info)

    def notify_pattern_signal(self, ticker, pattern, pattern_match_idx=None):
        #print('notify_pattern_signal', pattern, pattern_match_idx)
        pattern_info = {'pattern': pattern, 'symbol': ticker, 'info': pattern_match_idx}
        self.socket.on_pattern_signal(pattern_info)


