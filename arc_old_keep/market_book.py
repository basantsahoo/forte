import numpy as np
from datetime import datetime
import time
from dynamics.profile import utils as profile_utils
from arc_old_keep.asset_book import AssetBook
from entities.trading_day import TradeDateTime

class MarketBook:
    def __init__(self, trade_day=None, assets=[],  record_metric=True, candle_sw=0, insight_log=False):
        self.day_setup_done = False
        self.trade_day = trade_day
        self.pm = None
        self.record_metric = record_metric
        self.log_enabled = insight_log
        self.run_aggregator=False
        self.curr_tpo = None
        self.last_periodic_update = None
        self.periodic_update_sec = 60
        self.ib_periods = []
        self.market_start_ts = None
        self.market_close_ts = None
        self.tpo_brackets = []
        self.asset_books = {}
        self.strategy_manager = None
        self.strategy_setup_done = False
        self.last_tick_timestamp = None
        for asset in assets:
            self.asset_books[asset] = AssetBook(self, asset, candle_sw)

        if trade_day is not None:
            self.set_day_tpos(trade_day)
            self.last_tick_timestamp = self.tpo_brackets[0]
            self.day_setup_done = True

    def set_trade_date_from_time(self, epoch_tick_time):
        self.last_tick_timestamp = epoch_tick_time
        tick_date_time = datetime.fromtimestamp(epoch_tick_time)
        trade_day = tick_date_time.strftime('%Y-%m-%d')
        self.trade_day = trade_day
        self.set_day_tpos(trade_day)
        self.day_setup_done = True

    def set_day_tpos(self, trade_day):
        start_str = trade_day + " 09:15:00"
        ib_end_str = trade_day + " 10:15:00"
        end_str = trade_day + " 15:30:00"
        start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S")))
        ib_end_ts = int(time.mktime(time.strptime(ib_end_str, "%Y-%m-%d %H:%M:%S")))
        self.ib_periods = [start_ts, ib_end_ts]
        self.market_start_ts = start_ts
        self.market_close_ts = end_ts
        self.tpo_brackets = np.arange(start_ts, end_ts, 1800)

    def update_periodic(self):
        #print('update periodic')
        for asset_book in self.asset_books.values():
            print(asset_book)
            asset_book.update_periodic()

    def set_up_strategies(self):
        self.strategy_manager.set_up_strategies()

    def get_asset_book(self, symbol):
        return self.asset_books[symbol]

    def hist_spot_feed(self, hist_feed):
        print('hist_feed_input++++++++++++', len(hist_feed))
        for price in hist_feed:
            epoch_tick_time = price['timestamp']
            epoch_minute = TradeDateTime.get_epoc_minute(epoch_tick_time)
            key_list = ['timestamp', 'open', 'high', "low", "close"]
            feed_small = {key: price[key] for key in key_list}
            if not self.day_setup_done:
                self.set_trade_date_from_time(epoch_tick_time)
            #self.market_data[epoch_minute] = feed_small
            asset_book = self.get_asset_book(price['symbol'])
            asset_book.spot_processor.process_minute_data(price)
        #self.last_tick = feed_small
        self.set_curr_tpo(epoch_minute)
        asset_book.spot_minute_data_stream(price)
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        self.set_up_strategies()
        self.candle_5_processor.create_candles()
        self.candle_15_processor.create_candles()
        for candle_detector in self.candle_pattern_detectors:
            candle_detector.evaluate(notify=False)
        asset_book.spot_processor.process_spot_signals(notify=False)

    def spot_minute_data_stream(self, price, iv=None):
        print('insight price_input_stream++++++++++++++++++++++++++++++++++++ insight book')
        print(price)
        epoch_tick_time = price['timestamp']
        epoch_minute = int(epoch_tick_time // 60 * 60) + 1
        key_list = ['timestamp','open', 'high', "low", "close"]
        feed_small = {key: price[key] for key in key_list}
        #self.last_tick = feed_small
        #print(epoch_tick_time)
        if not self.day_setup_done:
            self.set_trade_date_from_time(epoch_tick_time)

        self.last_tick_timestamp = max(self.last_tick_timestamp, epoch_tick_time)
        #self.market_data[epoch_minute] = feed_small

        asset_book = self.get_asset_book(price['symbol'])
        if not asset_book.day_setup_done:
            asset_book.set_trade_date_from_time(epoch_tick_time)
        asset_book.spot_processor.process_minute_data(price)
        self.set_curr_tpo(epoch_minute)
        self.strategy_manager.on_minute_data_pre(price['symbol'])
        asset_book.spot_minute_data_stream(price)
        if not self.strategy_setup_done:
            self.set_up_strategies()
            self.strategy_setup_done = True
        if self.last_periodic_update is None:
            self.last_periodic_update = epoch_minute
        if price['timestamp'] - self.last_periodic_update > self.periodic_update_sec:
            self.last_periodic_update = epoch_minute
            self.update_periodic()
        self.strategy_manager.process_custom_signal()
        self.strategy_manager.on_minute_data_post()

    def option_minute_data_stream(self, option_data):
        #print('option price_input_stream+++++++++++++++++++++++++++++++++++++++++++++++++++++++++ insight book')
        #print(option_data)
        epoch_tick_time = option_data['timestamp']
        if not self.day_setup_done:
            self.set_trade_date_from_time(epoch_tick_time)
        asset_book = self.get_asset_book(option_data['symbol'])
        asset_book.option_processor.process_input_stream(option_data)

    def hist_option_feed(self, hist_feed):
        for option_data in hist_feed:
            asset_book = self.get_asset_book(option_data['symbol'])
            asset_book.option_processor.process_input_stream(option_data, notify=False)


    def pattern_signal(self, signal):
        self.strategy_manager.register_signal(signal)

        """
        if pattern == 'OPTION_PRICE_DROP':
            print('pattern_signal+++++++', pattern, pattern_match_idx)
        """
        """
        if pattern == 'DT':
            print('pattern_signal+++++++', pattern, pattern_match_idx)
        """
        """
        if pattern == 'TREND':
            #print('TREND+++++', pattern, pattern_match_idx)
            self.activity_log.update_sp_trend(pattern_match_idx['trend'])
            for wave in pattern_match_idx['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
            #print(self.intraday_waves)
        """
        """
        for strategy in self.strategies:
            strategy.register_signal(pattern, pattern_match_idx)
            #strategy.process_signal(pattern, pattern_match_idx)
        """
        if self.pm.data_interface is not None:
            self.pm.data_interface.notify_pattern_signal(self.ticker, signal)

        #print('self.intraday_trend')


    def clean(self):
        self.market_data = None
        self.pm = None


    def set_curr_tpo(self, epoch_minute):
        ts_idx = profile_utils.get_next_lowest_index(self.tpo_brackets, epoch_minute)
        ts_idx = 13 if ts_idx < 0 else ts_idx + 1
        self.curr_tpo = ts_idx


    def get_time_to_close(self):
        #print('market_close_ts=====', datetime.fromtimestamp(self.market_close_ts))
        return (self.market_close_ts - self.last_tick_timestamp) / 60 #-1 # - 1 is done as hack

    def get_time_since_market_open(self):
        return (self.last_tick_timestamp - self.market_start_ts) / 60
