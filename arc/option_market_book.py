import numpy as np
from datetime import datetime
import time
from dynamics.profile import utils as profile_utils
from arc.strategy_manager import StrategyManager
from arc.option_asset_book import OptionAssetBook
from entities.trading_day import TradeDateTime
from arc.time_book import TimeBook

class OptionMarketBook:
    def __init__(self,
                 trade_day=None,
                 assets=[],
                 record_metric=True,
                 insight_log=False,
                 live_mode=False,
                 volume_delta_mode=False,
                 print_cross_stats=False):
        self.live_mode = live_mode
        self.volume_delta_mode = volume_delta_mode
        self.print_cross_stats = print_cross_stats
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
            self.asset_books[asset] = OptionAssetBook(self, asset)
        self.time_book = TimeBook(self)
        if trade_day is not None:
            self.do_day_set_up(trade_day)
            self.last_tick_timestamp = self.tpo_brackets[0]

    def feed_stream(self, feed):
        #print("new feed")
        #print(feed['data'][-1])
        self.time_book.check_frame_change(feed['data'][-1]['timestamp'])
        if self.trade_day != feed['data'][-1]['trade_date']:
            print('trade dat change')
            self.do_day_set_up(feed['data'][-1]['trade_date'])
        if feed['feed_type'] == 'spot':
            self.set_curr_tpo(feed['data'][-1]['timestamp'])
            self.asset_books[feed['asset']].spot_feed_stream_1(feed['data'])

            #self.strategy_manager.on_minute_data_pre(feed['asset'])
            self.asset_books[feed['asset']].spot_feed_stream_2(feed['data'])
            if not self.strategy_setup_done:
                self.set_up_strategies()
                self.strategy_setup_done = True
            self.strategy_manager.process_custom_signal()
        elif feed['feed_type'] == 'option':
            self.asset_books[feed['asset']].option_feed_stream(feed['data'])
            #self.strategy_manager.on_minute_data_post(feed['asset'])
        #print('market_book feed_stream', feed)

    def do_day_set_up(self, trade_day):
        print('do_day_set_up++++++++++', trade_day)
        self.trade_day = trade_day
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
        for asset_book in self.asset_books.values():
            asset_book.day_change_notification(trade_day)
        self.day_setup_done = True

    def set_volume_delta_mode(self, volume_delta_mode):
        for asset_book in self.asset_books.values():
            asset_book.set_volume_delta_mode(volume_delta_mode)

    def set_up_strategies(self):
        if not self.strategy_setup_done:
            self.strategy_manager.set_up_strategies()
            self.strategy_setup_done = True


    def get_asset_book(self, symbol):
        return self.asset_books[symbol]

    def pattern_signal(self, asset, signal):
        #print(signal.category, signal.indicator)
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
            self.pm.data_interface.notify_pattern_signal(asset, signal)

        #print('self.intraday_trend')


    def clean(self):
        self.market_data = None
        self.pm = None


    def set_curr_tpo(self, epoch_minute):
        #print('set_curr_tpo+++++++++++++++++++++', epoch_minute)
        ts_idx = profile_utils.get_next_lowest_index(self.tpo_brackets, epoch_minute)
        ts_idx = 13 if ts_idx < 0 else ts_idx + 1
        self.curr_tpo = ts_idx
        self.last_tick_timestamp = epoch_minute


    def get_time_to_close(self):
        #print('market_close_ts=====', datetime.fromtimestamp(self.market_close_ts))
        return (self.market_close_ts - self.last_tick_timestamp) / 60 #-1 # - 1 is done as hack

    def get_time_since_market_open(self):
        return (self.last_tick_timestamp - self.market_start_ts) / 60
