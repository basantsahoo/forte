import json
from datetime import datetime
from arc.algo_portfolio import AlgoPortfolioManager
from arc.oms_manager import OMSManager
from arc.option_market_book import OptionMarketBook
from strat_machine.strategy_manager import StrategyManager
from trade_master.strategy_trade_manager_pool import StrategyTradeManagerPool
from pathlib import Path
from entities.trading_day import TradeDateTime
from servers.server_settings import cache_dir
from diskcache import Cache
from os import listdir
from os.path import isfile, join
from backtest_structure.bt_strategies import *

strat_config_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/" + 'live_strategies.json'

with open(strat_config_path, 'r') as bt_config:
    strat_config = json.load(bt_config)


#from live_algo.friday_candle_first_30_mins import FridayCandleBuyFullDay, FridayCandleSellFullDay

class AlgorithmIterface:
    def __init__(self, socket=None, process_id=1000):
        self.process_id = process_id
        #market_cache = Cache(cache_dir + "/P_" + str(self.process_id) + "/" + 'oms_cache')
        self.trade_day = None
        self.socket = socket
        self.market_book = None
        self.portfolio_manager = None
        self.last_epoc_minute_data = {}
        self.systems_loaded = False
        self.setup_in_progress = False
        market_cache = Cache(cache_dir + 'oms_cache')
        self.oms_manager = OMSManager(place_live_orders=True, market_cache=market_cache)
        self.strat_config = strat_config
        self.strat_config['strategy_info'] = {}
        self.strat_config['trade_manager_info'] = {}
        self.strat_config['combinator_info'] = {}

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
        self.set_up_strategy_manager(trade_day, volume_delta_mode=False)
        self.trade_day = trade_day
        self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())

    def load_system(self, trade_day=None, process_signal_switch=False, volume_delta_mode=False):
        print('===================Algo interface load system====', process_signal_switch)
        start_time = datetime.now()
        if not self.systems_loaded:
            self.set_up_strategy_manager(trade_day, volume_delta_mode)
            self.systems_loaded = True
        self.market_book.strategy_manager.process_signal_switch = process_signal_switch
        self.market_book.set_volume_delta_mode(volume_delta_mode)
        self.trade_day = trade_day
        if trade_day is not None:
            self.market_book.do_day_set_up(trade_day)
            self.setup_in_progress = False
        end_time = datetime.now()
        print('setup time', (end_time - start_time).total_seconds())

    def set_up_strategy_manager(self, trade_day, volume_delta_mode=False):
        # Strategies
        strategies_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/strategies/"
        strategyfiles = [f for f in listdir(strategies_path) if isfile(join(strategies_path, f))]
        for fl in strategyfiles:
            with open(strategies_path + fl, 'r') as bt_config:
                strategy_info = json.load(bt_config)
                if strategy_info['id'] in self.strat_config['strategies']:
                    self.strat_config['strategy_info'][strategy_info['id']] = strategy_info
        trade_manager_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/trade_managers/"
        trade_manager_files = [f for f in listdir(trade_manager_path) if isfile(join(trade_manager_path, f))]
        for fl in trade_manager_files:
            with open(trade_manager_path + fl, 'r') as bt_config:
                tm_info = json.load(bt_config)
                if tm_info['strategy_id'] in self.strat_config['strategies']:
                    self.strat_config['trade_manager_info'][tm_info['strategy_id']] = tm_info

        # Combinators
        combinators_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/combinators/"
        combinator_files = [f for f in listdir(combinators_path) if isfile(join(combinators_path, f))]
        for fl in combinator_files:
            with open(combinators_path + fl, 'r') as bt_config:
                combinator_info = json.load(bt_config)
                if combinator_info['id'] in self.strat_config['combinators']:
                    self.strat_config['combinator_info'][combinator_info['id']] = combinator_info

        #print(self.strat_config['combinator_info'])
        combination_strategies = [x for combinator in self.strat_config['combinator_info'].values() for x in combinator['combinations']]
        #print(combination_strategies)
        strategies_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/combinators/strategies/"
        strategyfiles = [f for f in listdir(strategies_path) if isfile(join(strategies_path, f))]
        for fl in strategyfiles:
            with open(strategies_path + fl, 'r') as bt_config:
                strategy_info = json.load(bt_config)
                if strategy_info['id'] in combination_strategies:
                    self.strat_config['strategy_info'][strategy_info['id']] = strategy_info

        trade_manager_path = str(Path(__file__).resolve().parent.parent) + "/live_deployments/combinators/trade_managers/"
        trade_manager_files = [f for f in listdir(trade_manager_path) if isfile(join(trade_manager_path, f))]
        for fl in trade_manager_files:
            with open(trade_manager_path + fl, 'r') as bt_config:
                tm_info = json.load(bt_config)
                if tm_info['strategy_id'] in combination_strategies:
                    self.strat_config['trade_manager_info'][tm_info['strategy_id']] = tm_info
        subscribed_assets = list(set([tm['asset'] for tm in self.strat_config['trade_manager_info'].values()]))

        self.portfolio_manager = AlgoPortfolioManager(place_live_orders=True, data_interface=self)
        market_book = OptionMarketBook(trade_day=trade_day, assets=subscribed_assets, record_metric=False, live_mode=True,
                                       volume_delta_mode=volume_delta_mode)
        self.portfolio_manager.market_book = market_book
        self.market_book = market_book
        market_book.pm = self.portfolio_manager
        strategy_manager = StrategyManager(market_book=market_book, record_metric=False)
        trade_pool = StrategyTradeManagerPool(market_book=market_book, strategy_manager=strategy_manager)
        market_book.strategy_manager = strategy_manager

        for deployed_strategy in self.strat_config['strategy_info'].values():
            start = datetime.now()
            strategy_class = eval(deployed_strategy['class'])
            strategy_manager.add_strategy(strategy_class, deployed_strategy)

        for deployed_tm in self.strat_config['trade_manager_info'].values():
            start = datetime.now()
            # print('deployed_strategy=====', deployed_strategy)
            trade_pool.add(deployed_tm)
            end = datetime.now()
            # print('strategy init took', (end - start).total_seconds())

        for deployed_combinator in self.strat_config['combinator_info'].values():
            strategy_manager.add_combinator(deployed_combinator)
            end = datetime.now()
            print('Combinator init took', (end - start).total_seconds())
        strategy_manager.clean_up_combinators()
        strategy_manager.clean_up_strategies()

        for symbol in subscribed_assets:
            self.last_epoc_minute_data[symbol] = {'timestamp': None}
            self.last_epoc_minute_data[symbol + "_O"] = {'timestamp': None}

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

    def place_entry_order(self, order_info, order_type):
        #print('place_entry_order in data interface')
        if True: #self.socket.hist_loaded:
            #print('place_entry_order in data interface', order_info)
            resp = self.oms_manager.place_entry_order(order_info, order_type)
            print(resp)
            # Use following instead of oms_manager if oms server is running separately
            #self.socket.on_oms_entry_order(order_info)


    def place_exit_order(self, order_info, order_type):
        if True: #self.socket.hist_loaded:
            #print('place_exit_order in data interface')
            resp = self.oms_manager.place_exit_order(order_info, order_type)
            print(resp)

            # Use following instead of oms_manager if oms server is running separately
            #self.socket.on_oms_exit_order(order_info)

    def notify_pattern_signal(self, ticker, pattern, pattern_match_idx=None):
        #print('notify_pattern_signal', pattern, pattern_match_idx)
        pattern_info = {'pattern': pattern, 'symbol': ticker, 'info': pattern_match_idx}
        self.socket.on_pattern_signal(pattern_info)


