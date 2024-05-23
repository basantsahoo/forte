from arc.spot_book import SpotBook
from dynamics.option_market.option_matrix import OptionMatrix
from db.market_data import get_prev_day_avg_volume
from dynamics.option_market.utils import get_average_volume_for_day
from helper.data_feed_utils import convert_to_option_ion, convert_to_spot_ion
from entities.base import Signal
from arc.clock import Clock
from arc.compound_signal_builder import CompoundSignalBuilder
from entities.trading_day import NearExpiryWeek, TradeDateTime

class OptionAssetBook:
    def __init__(self, market_book, asset):
        self.market_book = market_book
        self.asset = asset
        self.spot_book = SpotBook(self, asset)
        self.clock = None
        self.option_matrix = OptionMatrix(asset, feed_speed=1, throttle_speed=1, live_mode=market_book.live_mode, volume_delta_mode=market_book.volume_delta_mode, print_cross_stats=market_book.print_cross_stats)
        self.option_matrix_5_min = OptionMatrix(asset, feed_speed=1, throttle_speed=5, live_mode=market_book.live_mode, volume_delta_mode=market_book.volume_delta_mode, print_cross_stats=market_book.print_cross_stats, period="5min")
        self.option_matrix.signal_generator.signal_dispatcher = self.pattern_signal
        self.option_matrix_5_min.signal_generator.signal_dispatcher = self.pattern_signal
        self.last_periodic_update = None
        self.periodic_update_sec = 60
        self.compound_signal_generator = CompoundSignalBuilder(self)

    def get_lowest_candle(self, instr, after_ts=None, is_option=False):
        lowest_candle = None
        if not is_option:
            inst_ts = self.spot_book.spot_processor.spot_ts.copy()
            if after_ts is not None:
                inst_ts = {key: val for (key, val) in inst_ts.items() if key > after_ts}
            lowest = min([val['close'] for val in inst_ts.values()])
            for (ts, candle) in reversed(inst_ts.items()):
                # print(candle)
                if candle['close'] == lowest:
                    lowest_candle = candle
                    break
        return lowest_candle

    def get_highest_candle(self, instr, after_ts=None, is_option=False):
        highest_candle = None
        if not is_option:
            inst_ts = self.spot_book.spot_processor.spot_ts.copy()
            if after_ts is not None:
                inst_ts = {key: val for (key, val) in inst_ts.items() if key > after_ts}
            highest = max([val['close'] for val in inst_ts.values()])
            for (ts, candle) in reversed(inst_ts.items()):
                # print(candle)
                if candle['close'] == highest:
                    highest_candle = candle
                    break
        return highest_candle

    def day_change_notification(self, trade_day):
        if self.clock is None:
            self.clock = Clock()
            self.clock.initialize_from_trade_day(trade_day)
            self.clock.subscribe_to_frame_change(self.frame_change_action)
        else:
            self.clock.on_day_change(trade_day)
        """
        if NearExpiryWeek(TradeDateTime(trade_day), self.asset).start_date.date_string != trade_day:
            closing_oi_df = get_prev_day_avg_volume(self.asset, trade_day)
            closing_oi_df = closing_oi_df[['instrument', 'closing_oi']]
            #print(closing_oi_df.to_dict('records'))
            self.option_matrix.process_closing_oi(trade_day, closing_oi_df.to_dict("record"))
            self.option_matrix_5_min.process_closing_oi(trade_day, closing_oi_df.to_dict("record"))
        else:
            self.option_matrix.process_closing_oi(trade_day, [])
            self.option_matrix_5_min.process_closing_oi(trade_day, [])
        
        avg_volume_recs = get_average_volume_for_day(self.asset, trade_day)
        self.option_matrix.process_avg_volume(trade_day, avg_volume_recs)
        self.option_matrix_5_min.process_avg_volume(trade_day, avg_volume_recs)
        """
        self.spot_book.day_change_notification(trade_day)
        #self.spot_book.set_transition_matrix()

    def spot_feed_stream_1(self, feed_list):
        feed_list = [convert_to_spot_ion(feed) for feed in feed_list]
        #Looping to accomodate hist data from websocket. Yet to test
        for feed in feed_list:
            self.clock.check_frame_change(feed['timestamp'])
            self.option_matrix.process_spot_feed([feed])
            self.option_matrix_5_min.process_spot_feed([feed])
            self.spot_book.feed_stream_1([feed])

    #def spot_feed_stream_2(self, feed_list):
        if self.last_periodic_update is None:
            self.last_periodic_update = self.clock.current_frame
        if self.clock.current_frame - self.last_periodic_update > self.periodic_update_sec:
            self.last_periodic_update = self.clock.current_frame
            self.spot_book.update_periodic()

    def option_feed_stream(self, feed_list):
        feed_list = [convert_to_option_ion(feed) for feed in feed_list]
        data_dct = {ion_d['instrument']: ion_d['oi'] for ion_d in feed_list}
        """
        print("**************************************")
        print(datetime.now())
        print("Tick data===========", data_dct)
        """
        self.option_matrix.process_option_feed(feed_list)
        self.option_matrix_5_min.process_option_feed(feed_list)

    def set_volume_delta_mode(self, volume_delta_mode):
        self.option_matrix.volume_delta_mode = volume_delta_mode
        self.option_matrix_5_min.volume_delta_mode = volume_delta_mode


    def clean(self):
        self.spot_book.clean()
        self.compound_signal_generator.clean()

    def pattern_signal(self, signal: Signal):
        #print('asset book pattern_signal')
        if signal.category in ['PRICE_ACTION_INTRA_0', 'TECHNICAL_0', 'CANDLE_1', 'CANDLE_2', 'CANDLE_5', 'TIME_SIGNAL']:
            print(signal.category, signal.indicator)
        signal.spot_market_info = self.spot_book.spot_processor.get_market_params()
        #signal.option_market_info = self.option_matrix.signal_generator.get_info()
        self.market_book.pattern_signal(self.asset, signal)
        last_tick = self.spot_book.spot_processor.last_tick
        self.compound_signal_generator.add_signal(last_tick['timestamp'], signal)

    def frame_change_action(self, current_frame, next_frame):
        #print('frame_change_action++++++++++++++++++ 111')
        self.option_matrix.frame_change_action(current_frame, next_frame)
        self.option_matrix_5_min.frame_change_action(current_frame, next_frame)
        #print('frame_change_action++++++++++++++++++ 222')
        self.spot_book.frame_change_action(current_frame, next_frame)
        self.compound_signal_generator.frame_change_action()
        self.market_book.strategy_manager.on_minute_data_pre(self.asset)
        self.market_book.strategy_manager.on_minute_data_post(self.asset)
