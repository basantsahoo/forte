from entities.base import Signal
import traceback
class CompoundSignalBuilder:
    def __init__(self, asset_book):
        self.signal_dict = {}
        self.asset_book = asset_book
        self.last_ts = None
        self.down_break_level_type_1 = set()
        self.down_break_level_type_2 = set()
        self.down_break_level_type_3 = set()
        self.up_break_level_type_1 = set()
        self.up_break_level_type_2 = set()
        self.up_break_level_type_3 = set()

        self.market_params = {}

    def clean(self):
        self.signal_dict = {}
        self.down_break_level_type_1 = set()
        self.down_break_level_type_2 = set()
        self.down_break_level_type_3 = set()
        self.up_break_level_type_1 = set()
        self.up_break_level_type_2 = set()
        self.up_break_level_type_3 = set()

        self.market_params = {}

    def add_signal(self, ts, signal):
        #print('adding signal ', signal.category, signal.indicator, signal.period)
        if ts not in self.signal_dict:
            self.signal_dict[ts] = {}
        self.signal_dict[ts][signal.key()] = signal
        self.last_ts = ts

    def frame_change_action(self):
        self.build_signal()

    def release_signal(self, signal):
        self.asset_book.pattern_signal(signal)

    def build_signal(self):
        self.market_params = self.asset_book.spot_book.spot_processor.get_market_params()

        #self.build_bottom_type_1()
        self.build_down_break_type_1()
        self.build_down_break_reversal()
        self.bearish_engulfing_high_put_volume()
        self.build_up_break_type_1()
        self.build_up_break_reversal()


        #self.print_signals_last_ts()
        #self.print_signals()

    def get_n_period_signals(self, ts, n_period=2):
        all_ts = list(self.signal_dict.keys())
        filtered_ts = [x for x in all_ts if x<= ts]
        filtered_ts.sort()
        n_period_ts = filtered_ts[-n_period:]
        n_period_ts.reverse()
        n_period_signals = {idx: self.signal_dict[n_period_ts[idx]] for idx in range(len(n_period_ts))}
        #n_period_signals = [self.signal_dict[ts] for ts in n_period_ts]
        return n_period_signals

    def check_signal_present(self, signal_dct, signal_tuple, default_signal_val=None):
        signal_found = False
        signal_value = default_signal_val
        signal_obj = None
        if signal_tuple in signal_dct.keys():
            signal = signal_dct[signal_tuple]
            signal_found = True
            signal_value = signal.strength
            signal_obj = signal
        return {'found': signal_found, 'value':signal_value, 'signal':signal_obj}

    def not_none_eval(self,val1, val2, ):
        if val1 is not None and val2 is not None:
            return True
        else:
            return False


    def build_bottom_type_1(self):
        try:
            two_period_signals = self.get_n_period_signals(self.last_ts, 2)
            EMA_1_10 = self.check_signal_present(two_period_signals[0], ('TECHNICAL', 'EMA_1_10', "1min"))['value']
            SMA_1_10 = self.check_signal_present(two_period_signals[0], ('TECHNICAL', 'SMA_1_10', "1min"))['value']
            one_bullish_candle_resp = self.check_signal_present(two_period_signals[0], ('CANDLE_PATTERN', 'CDL_DIR_P', "1min"))
            one_bullish_candle = one_bullish_candle_resp['found']
            #one_bullish_candle = self.check_signal_present(one_period_signals[0], ('CANDLE_1', 'CDL_DIR_P'))['found']
            one_big_candle = self.check_signal_present(two_period_signals[0], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            one_body_large = self.check_signal_present(two_period_signals[0], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            two_bearish_candle_resp = self.check_signal_present(two_period_signals[1], ('CANDLE_PATTERN', 'CDL_DIR_N', "1min"))
            two_bearish_candle = two_bearish_candle_resp['found']
            #two_bearish_candle = self.check_signal_present(two_period_signals[0], ('CANDLE_1', 'CDL_DIR_N'))['found']
            two_big_candle = self.check_signal_present(two_period_signals[1], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            two_body_large = self.check_signal_present(two_period_signals[1], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            one_high_volume_candle = self.check_signal_present(two_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_1', "1min"))['found']
            two_high_volume_candle = self.check_signal_present(two_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_1', "1min"))['found']
            #print(two_bearish_candle, two_big_candle, two_body_large)

            if self.not_none_eval(EMA_1_10, SMA_1_10) and one_bullish_candle and one_big_candle and one_body_large\
                    and two_bearish_candle and two_big_candle and two_body_large\
                    and (one_high_volume_candle or two_high_volume_candle):
                local_low = min(one_bullish_candle_resp['signal'].signal_info['low'],
                                 two_bearish_candle_resp['signal'].signal_info['low'])
                key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [local_low],
                              'spot_short_target_levels': [], 'spot_short_stop_loss_levels': []}

                pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                             indicator='BOTTOM_TYPE_1_1MIN',
                             strength=1,
                             signal_time=self.last_ts,
                             notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                             signal_info={}, key_levels=key_levels, period="1min")
                self.release_signal(pat)

        except Exception as e:
            print('build_bottom_type_1 exception')
            print(e)


    def build_down_break_type_1(self):
        try:
            three_period_signals = self.get_n_period_signals(self.last_ts, 3)
            EMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'EMA_1_10', "1min"))['value']
            SMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'SMA_1_10', "1min"))['value']
            one_bearish_candle_resp = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_DIR_N', "1min"))
            one_bearish_candle = one_bearish_candle_resp['found']
            one_big_candle = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            one_body_large = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            two_bullish_candle_resp = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_DIR_P', "1min"))
            two_bullish_candle = two_bullish_candle_resp['found']
            two_big_candle = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            two_body_large = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            three_bearish_candle_resp = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_DIR_N', "1min"))
            three_bearish_candle = three_bearish_candle_resp['found']
            three_big_candle = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            three_body_large = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']

            one_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_1', "1min"))['found']
            two_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_1', "1min"))['found']
            three_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_1', "1min"))['found']

            one_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_2', "1min"))['found']
            two_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_2', "1min"))['found']
            three_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_2', "1min"))['found']


            one_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_3', "1min"))['found']
            two_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_3', "1min"))['found']
            three_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_3', "1min"))['found']
            """
            print("one_bearish_candle==", one_bearish_candle)
            print("one_big_candle==", one_big_candle)
            print("one_body_large==", one_body_large)

            print("two_bullish_candle==", two_bullish_candle)
            print("two_big_candle==", two_big_candle)
            print("two_body_large==", two_body_large)

            print("three_bearish_candle==", three_bearish_candle)
            print("three_big_candle==", three_big_candle)
            print("three_body_large==", two_body_large)

            print("one_high_volume_candle_type_3==", one_high_volume_candle_type_3)
            print("two_high_volume_candle_type_3==", two_high_volume_candle_type_3)
            print("three_high_volume_candle_type_3==", three_high_volume_candle_type_3)
            print("EMA==", EMA_1_10)
            print("SMA==", SMA_1_10)

            print("price_location===", self.market_params['price_location'])
            """
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.not_none_eval(EMA_1_10, SMA_1_10) and EMA_1_10 < SMA_1_10:
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_1 or two_high_volume_candle_type_1 or three_high_volume_candle_type_1):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_high = max(one_bearish_candle_resp['signal'].signal_info['high'], two_bullish_candle_resp['signal'].signal_info['high'], three_bearish_candle_resp['signal'].signal_info['high'])
                    self.down_break_level_type_1.add(local_high)
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_2 or two_high_volume_candle_type_2 or three_high_volume_candle_type_2):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_high = min(one_bearish_candle_resp['signal'].signal_info['high'], two_bullish_candle_resp['signal'].signal_info['high'], three_bearish_candle_resp['signal'].signal_info['high'])
                    self.down_break_level_type_2.add(local_high)
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_3 or two_high_volume_candle_type_3 or three_high_volume_candle_type_3)\
                        and self.market_params.get('CDL_DIR_N_daily', 0):
                    local_high = max(one_bearish_candle_resp['signal'].signal_info['high'],
                                     two_bullish_candle_resp['signal'].signal_info['high'],
                                     three_bearish_candle_resp['signal'].signal_info['high'])
                    if self.market_params.get('CDL_DIR_N_daily', 0):
                        key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [],
                                      'spot_short_target_levels': [], 'spot_short_stop_loss_levels': [local_high]}
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='DOWN_BREAK_TYPE_3_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, key_levels=key_levels, period="1min")

                        self.release_signal(pat)
                    self.down_break_level_type_3.add(local_high)

        except Exception as e:
            print(e)

    def build_down_break_reversal(self):
        try:
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.down_break_level_type_1.copy():
                    if last_tick['close'] > level:
                        self.down_break_level_type_1.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='DOWN_BREAK_REVERSAL_TYPE_1_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)
            if self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.down_break_level_type_2.copy():
                    if last_tick['close'] > level:
                        self.down_break_level_type_2.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='DOWN_BREAK_REVERSAL_TYPE_2_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)
            if self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.down_break_level_type_3.copy():
                    if last_tick['close'] > level:
                        self.down_break_level_type_3.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='DOWN_BREAK_REVERSAL_TYPE_3_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)

        except Exception as e:
            print(e)

    def bearish_engulfing_high_put_volume(self):
        try:
            #print('bearish_engulfing_high_put_volume ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            ten_period_signals = self.get_n_period_signals(self.last_ts, 10)
            EMA_1_10 = self.check_signal_present(ten_period_signals[0], ('TECHNICAL', 'EMA_1_10', "1min"))['value']
            SMA_1_10 = self.check_signal_present(ten_period_signals[0], ('TECHNICAL', 'SMA_1_10', "1min"))['value']
            one_bearish_candle_resp = self.check_signal_present(ten_period_signals[0], ('CANDLE_PATTERN', 'CDL_DIR_N', "1min"))
            one_bearish_candle = one_bearish_candle_resp['found']
            one_body_large = self.check_signal_present(ten_period_signals[0], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']

            one_high_put_volume_candle_type_1 = self.check_signal_present(ten_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_PUT_1', "1min"))['found']
            bearish_engulfing = False #CANDLE_1 CDLENGULFING_BUY
            local_high = None
            for idx in range(0, 9):
                #print("idx====", idx)
                bearish_engulfing_resp = self.check_signal_present(ten_period_signals[idx], ('CANDLE_PATTERN', 'CDLENGULFING_SELL', "1min"))
                bearish_engulfing = bearish_engulfing_resp['found']
                if bearish_engulfing:
                    #print(bearish_engulfing_resp['signal'].signal_info['candle'])
                    local_high = bearish_engulfing_resp['signal'].signal_info['high']
                    print('one_bearish_candle found+++++', one_bearish_candle)
                    print('one_body_large found+++++', one_body_large)
                    print('one_high_put_volume_candle_type_1 found+++++', one_high_put_volume_candle_type_1)
                    break
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.not_none_eval(EMA_1_10, SMA_1_10):
                if bearish_engulfing and one_high_put_volume_candle_type_1 and one_bearish_candle and one_body_large:

                    key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [],
                                  'spot_short_target_levels': [], 'spot_short_stop_loss_levels': [local_high]}
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                 indicator='BEARISH_ENGULFING_HIGH_PUT_VOLUME',
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 signal_info=last_tick, key_levels=key_levels, period="1min")
                    self.release_signal(pat)

        except Exception as e:
            print(e)

    def print_signals(self):
        for ts in self.signal_dict.keys():
            for signal in self.signal_dict[ts]:
                print(signal.key())

    def print_signals_last_ts(self):
        print('print_signals_last_ts++++++++++++++++++++++ start==')
        for signal in self.signal_dict[self.last_ts]:
            print(signal.key())
        print('print_signals_last_ts++++++++++++++++++++++ end==')


    def build_up_break_type_1(self):
        try:
            three_period_signals = self.get_n_period_signals(self.last_ts, 3)
            EMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'EMA_1_10', "1min"))['value']
            SMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'SMA_1_10', "1min"))['value']
            one_bullish_candle_resp = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_DIR_P', "1min"))
            one_bullish_candle = one_bullish_candle_resp['found']
            one_big_candle = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            one_body_large = self.check_signal_present(three_period_signals[0], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            two_bearish_candle_resp = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_DIR_N', "1min"))
            two_bearish_candle = two_bearish_candle_resp['found']
            two_big_candle = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            two_body_large = self.check_signal_present(three_period_signals[1], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']
            three_bullish_candle_resp = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_DIR_P', "1min"))
            three_bullish_candle = three_bullish_candle_resp['found']
            three_big_candle = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_SZ_L', "1min"))['found']
            three_body_large = self.check_signal_present(three_period_signals[2], ('CANDLE_PATTERN', 'CDL_BD_L', "1min"))['found']

            one_high_volume_candle_type_4 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_4', "1min"))['found']
            two_high_volume_candle_type_4 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_4', "1min"))['found']
            three_high_volume_candle_type_4 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_4', "1min"))['found']

            one_high_volume_candle_type_5 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_5', "1min"))['found']
            two_high_volume_candle_type_5 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_5', "1min"))['found']
            three_high_volume_candle_type_5 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_5', "1min"))['found']


            one_high_volume_candle_type_6 = self.check_signal_present(three_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_6', "1min"))['found']
            two_high_volume_candle_type_6 = self.check_signal_present(three_period_signals[1], ('OPTION_MARKET', 'HIGH_VOL_6', "1min"))['found']
            three_high_volume_candle_type_6 = self.check_signal_present(three_period_signals[2], ('OPTION_MARKET', 'HIGH_VOL_6', "1min"))['found']
            """
            print("one_bullish_candle==", one_bullish_candle)
            print("one_big_candle==", one_big_candle)
            print("one_body_large==", one_body_large)

            print("two_bearish_candle==", two_bearish_candle)
            print("two_big_candle==", two_big_candle)
            print("two_body_large==", two_body_large)

            print("three_bullish_candle==", three_bullish_candle)
            print("three_big_candle==", three_big_candle)
            print("three_body_large==", two_body_large)

            print("one_high_volume_candle_type_6==", one_high_volume_candle_type_6)
            print("two_high_volume_candle_type_6==", two_high_volume_candle_type_6)
            print("three_high_volume_candle_type_6==", three_high_volume_candle_type_6)
            print("EMA==", EMA_1_10)
            print("SMA==", SMA_1_10)

            print("price_location===", self.market_params['price_location'])
            """
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.not_none_eval(EMA_1_10, SMA_1_10):
                if one_bullish_candle and two_bearish_candle and three_bullish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_4 or two_high_volume_candle_type_4 or three_high_volume_candle_type_4):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_low = min(one_bullish_candle_resp['signal'].signal_info['low'], two_bearish_candle_resp['signal'].signal_info['low'], three_bullish_candle_resp['signal'].signal_info['low'])
                    self.up_break_level_type_1.add(local_low)
                if one_bullish_candle and two_bearish_candle and three_bullish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_5 or two_high_volume_candle_type_5 or three_high_volume_candle_type_5):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_low = max(one_bullish_candle_resp['signal'].signal_info['low'], two_bearish_candle_resp['signal'].signal_info['low'], three_bullish_candle_resp['signal'].signal_info['low'])
                    self.up_break_level_type_2.add(local_low)
                if one_bullish_candle and two_bearish_candle and three_bullish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_6 or two_high_volume_candle_type_6 or three_high_volume_candle_type_6):
                    local_low = min(one_bullish_candle_resp['signal'].signal_info['low'],
                                     two_bearish_candle_resp['signal'].signal_info['low'],
                                     three_bullish_candle_resp['signal'].signal_info['low'])
                    if self.market_params.get('CDL_BD_L_daily', 0):
                        key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [local_low],
                                      'spot_short_target_levels': [], 'spot_short_stop_loss_levels': []}
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='UP_BREAK_TYPE_3_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, key_levels=key_levels, period="1min")

                        self.release_signal(pat)
                    self.up_break_level_type_3.add(local_low)

        except Exception as e:
            print(traceback.format_exc())
            print(e)

    def build_up_break_reversal(self):
        try:
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if True: #self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.up_break_level_type_1.copy():
                    if last_tick['close'] < level:
                        self.up_break_level_type_1.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='UP_BREAK_REVERSAL_TYPE_1_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)
            if True: #self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.up_break_level_type_2.copy():
                    if last_tick['close'] < level:
                        self.up_break_level_type_2.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='UP_BREAK_REVERSAL_TYPE_2_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)
            if True: #self.market_params.get('CDL_BD_L_daily', 0):
                for level in self.up_break_level_type_3.copy():
                    if last_tick['close'] < level:
                        self.up_break_level_type_3.remove(level)
                        pat = Signal(asset=self.asset_book.spot_book.asset, category='COMPOUND', instrument=None,
                                     indicator='UP_BREAK_REVERSAL_TYPE_3_1MIN',
                                     strength=1,
                                     signal_time=self.last_ts,
                                     notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                     signal_info=last_tick, period="1min")
                        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.release_signal(pat)

        except Exception as e:
            print(e)
