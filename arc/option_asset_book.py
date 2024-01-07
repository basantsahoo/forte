from arc.spot_book import SpotBook
from option_market.option_matrix import OptionMatrix
from db.market_data import get_prev_day_avg_volume
from option_market.utils import get_average_volume_for_day
from helper.data_feed_utils import convert_to_option_ion, convert_to_spot_ion
from entities.base import BaseSignal

class OptionAssetBook:
    def __init__(self, market_book, asset):
        self.market_book = market_book
        self.asset = asset
        self.spot_book = SpotBook(self, asset)
        self.option_matrix = OptionMatrix(asset, feed_speed=1, throttle_speed=1, live_mode=market_book.live_mode, volume_delta_mode=market_book.volume_delta_mode, print_cross_stats=market_book.print_cross_stats)
        self.option_matrix.signal_generator.signal_dispatcher = self.pattern_signal

    def day_change_notification(self, trade_day):
        closing_oi_df = get_prev_day_avg_volume(self.asset, trade_day)
        closing_oi_df = closing_oi_df[['instrument', 'closing_oi']]
        self.option_matrix.process_closing_oi(trade_day, closing_oi_df.to_dict("record"))
        avg_volume_recs = get_average_volume_for_day(self.asset, trade_day)
        self.option_matrix.process_avg_volume(trade_day, avg_volume_recs)
        self.spot_book.day_change_notification(trade_day)
        #self.spot_book.set_transition_matrix()

    def spot_feed_stream(self, feed_list):
        feed_list = [convert_to_spot_ion(feed) for feed in feed_list]
        self.option_matrix.process_spot_feed(feed_list)
        self.spot_book.feed_stream(feed_list)

    def option_feed_stream(self, feed_list):
        feed_list = [convert_to_option_ion(feed) for feed in feed_list]
        self.option_matrix.process_option_feed(feed_list)

    def clean(self):
        self.spot_book.clean()

    def pattern_signal(self, signal: BaseSignal):
        print('asset book pattern_signal')
        self.market_book.pattern_signal(signal)
