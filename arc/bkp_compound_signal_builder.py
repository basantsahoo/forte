from entities.base import Signal
class CompoundSignalBuilder:
    def __init__(self, asset_book):
        self.signal_dict = {}
        self.asset_book = asset_book
        self.last_ts = None
        self.down_break_level_type_1 = set()
        self.down_break_level_type_2 = set()
        self.down_break_level_type_3 = set()
        self.market_params = {}

    def add_signal(self, ts, signal):
        print('adding signal ', signal.category, signal.indicator)
        if ts not in self.signal_dict:
            self.signal_dict[ts] = []
        self.signal_dict[ts].append(signal)
        self.last_ts = ts

    def frame_change_action(self):
        self.build_signal()

    def release_signal(self, signal):
        self.asset_book.pattern_signal(signal)

    def build_signal(self):
        self.market_params = self.asset_book.spot_book.activity_log.get_market_params()
        """
        self.build_bottom_type_2()
        self.build_bottom_type_1()
        self.build_down_break_type_1()
        self.build_down_break_reversal()
        
        """
       # self.print_signals_last_ts()
        self.bearish_engulfing_high_put_volume()
        #self.print_signals()

    def get_n_period_signals(self, ts, n_period=2):
        all_ts = list(self.signal_dict.keys())
        filtered_ts = [x for x in all_ts if x<= ts]
        filtered_ts.sort()
        n_period_ts = filtered_ts[-n_period:]
        n_period_signals = [self.signal_dict[ts] for ts in n_period_ts]
        return n_period_signals

    def check_signal_present(self, signal_array, signal_tuple, default_signal_val=None):
        signal_found = False
        signal_value = default_signal_val
        signal_obj = None
        for signal in signal_array:
            if (signal.category, signal.indicator) == signal_tuple:
                signal_found = True
                signal_value = signal.strength
                signal_obj = signal
                break
        #return signal_found, signal_value

        return {'found': signal_found, 'value':signal_value, 'signal':signal_obj}

    def not_none_eval(self,val1, val2, ):
        if val1 is not None and val2 is not None:
            return True
        else:
            return False

    def build_bottom_type_2(self):
        try:
            one_period_signals = self.get_n_period_signals(self.last_ts, 1)
            one_bullish_candle = self.check_signal_present(one_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']
            if one_bullish_candle:
                print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        except Exception as e:
            print(e)


    def build_bottom_type_1(self):
        try:
            one_period_signals = self.get_n_period_signals(self.last_ts, 1)
            two_period_signals = self.get_n_period_signals(self.last_ts, 2)
            EMA_1_10 = self.check_signal_present(one_period_signals[0], ('TECHNICAL', 'EMA_1_10'))['value']
            SMA_1_10 = self.check_signal_present(one_period_signals[0], ('TECHNICAL', 'SMA_1_10'))['value']
            one_bullish_candle_resp = self.check_signal_present(one_period_signals[0], ('CANDLE_1', 'CDL_DIR_P'))
            one_bullish_candle = one_bullish_candle_resp['found']
            #one_bullish_candle = self.check_signal_present(one_period_signals[0], ('CANDLE_1', 'CDL_DIR_P'))['found']
            one_big_candle = self.check_signal_present(one_period_signals[0], ('CANDLE_1', 'CDL_SZ_L'))['found']
            one_body_large = self.check_signal_present(one_period_signals[0], ('CANDLE_1', 'CDL_BD_L'))['found']
            two_bearish_candle_resp = self.check_signal_present(two_period_signals[0], ('CANDLE_1', 'CDL_DIR_N'))
            two_bearish_candle = two_bearish_candle_resp['found']
            #two_bearish_candle = self.check_signal_present(two_period_signals[0], ('CANDLE_1', 'CDL_DIR_N'))['found']
            two_big_candle = self.check_signal_present(two_period_signals[0], ('CANDLE_1', 'CDL_SZ_L'))['found']
            two_body_large = self.check_signal_present(two_period_signals[0], ('CANDLE_1', 'CDL_BD_L'))['found']
            one_high_volume_candle = self.check_signal_present(one_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']
            two_high_volume_candle = self.check_signal_present(two_period_signals[0], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']
            #print(two_bearish_candle, two_big_candle, two_body_large)
            if self.not_none_eval(EMA_1_10, SMA_1_10) and EMA_1_10 < SMA_1_10 and one_bullish_candle and one_big_candle and one_body_large\
                    and two_bearish_candle and two_big_candle and two_body_large\
                    and (one_high_volume_candle or two_high_volume_candle):
                print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                local_low = min(one_bullish_candle_resp['signal'].info['low'],
                                 two_bearish_candle_resp['signal'].info['low'])
                key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [local_low],
                              'spot_short_target_levels': [], 'spot_short_stop_loss_levels': []}

                pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                             indicator='BOTTOM_TYPE_1',
                             signal=1,
                             strength=1,
                             signal_time=self.last_ts,
                             notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                             info={}, key_levels=key_levels)
                self.release_signal(pat)

        except Exception as e:
            print(e)


    def build_down_break_type_1(self):
        try:
            print('build_down_break_type_1 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            three_period_signals = self.get_n_period_signals(self.last_ts, 3)
            EMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'EMA_1_10'))['value']
            SMA_1_10 = self.check_signal_present(three_period_signals[0], ('TECHNICAL', 'SMA_1_10'))['value']
            one_bearish_candle_resp = self.check_signal_present(three_period_signals[-1], ('CANDLE_1', 'CDL_DIR_N'))
            one_bearish_candle = one_bearish_candle_resp['found']
            one_big_candle = self.check_signal_present(three_period_signals[-1], ('CANDLE_1', 'CDL_SZ_L'))['found']
            one_body_large = self.check_signal_present(three_period_signals[-1], ('CANDLE_1', 'CDL_BD_L'))['found']
            two_bullish_candle_resp = self.check_signal_present(three_period_signals[-2], ('CANDLE_1', 'CDL_DIR_P'))
            two_bullish_candle = two_bullish_candle_resp['found']
            two_big_candle = self.check_signal_present(three_period_signals[-2], ('CANDLE_1', 'CDL_SZ_L'))['found']
            two_body_large = self.check_signal_present(three_period_signals[-2], ('CANDLE_1', 'CDL_BD_L'))['found']
            three_bearish_candle_resp = self.check_signal_present(three_period_signals[-3], ('CANDLE_1', 'CDL_DIR_N'))
            three_bearish_candle = three_bearish_candle_resp['found']
            three_big_candle = self.check_signal_present(three_period_signals[-3], ('CANDLE_1', 'CDL_SZ_L'))['found']
            three_body_large = self.check_signal_present(three_period_signals[-3], ('CANDLE_1', 'CDL_BD_L'))['found']

            one_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[-1], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']
            two_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[-2], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']
            three_high_volume_candle_type_1 = self.check_signal_present(three_period_signals[-3], ('OPTION_MARKET', 'HIGH_VOL_1'))['found']

            one_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[-1], ('OPTION_MARKET', 'HIGH_VOL_2'))['found']
            two_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[-2], ('OPTION_MARKET', 'HIGH_VOL_2'))['found']
            three_high_volume_candle_type_2 = self.check_signal_present(three_period_signals[-3], ('OPTION_MARKET', 'HIGH_VOL_2'))['found']


            one_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[-1], ('OPTION_MARKET', 'HIGH_VOL_3'))['found']
            two_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[-2], ('OPTION_MARKET', 'HIGH_VOL_3'))['found']
            three_high_volume_candle_type_3 = self.check_signal_present(three_period_signals[-3], ('OPTION_MARKET', 'HIGH_VOL_3'))['found']

            print(one_bearish_candle)
            print(one_big_candle)
            print(one_body_large)

            print(two_bullish_candle)
            print(two_big_candle)
            print(two_body_large)


            print(three_bearish_candle)
            print(three_big_candle)
            print(three_body_large)
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.not_none_eval(EMA_1_10, SMA_1_10) and EMA_1_10 < SMA_1_10:
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_1 or two_high_volume_candle_type_1 or three_high_volume_candle_type_1):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_high = max(one_bearish_candle_resp['signal'].info['high'], two_bullish_candle_resp['signal'].info['high'], three_bearish_candle_resp['signal'].info['high'])
                    self.down_break_level_type_1.add(local_high)
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_2 or two_high_volume_candle_type_2 or three_high_volume_candle_type_2):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_high = min(one_bearish_candle_resp['signal'].info['high'], two_bullish_candle_resp['signal'].info['high'], three_bearish_candle_resp['signal'].info['high'])
                    self.down_break_level_type_2.add(local_high)
                if one_bearish_candle and two_bullish_candle and three_bearish_candle \
                        and ((one_big_candle and one_body_large) or (two_big_candle and two_body_large) or (three_big_candle and three_body_large)) \
                        and (one_high_volume_candle_type_3 or two_high_volume_candle_type_3 or three_high_volume_candle_type_3)\
                        and self.market_params['price_location'] < 30:
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    local_high = max(one_bearish_candle_resp['signal'].info['high'],
                                     two_bullish_candle_resp['signal'].info['high'],
                                     three_bearish_candle_resp['signal'].info['high'])
                    key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [],
                                  'spot_short_target_levels': [], 'spot_short_stop_loss_levels': [local_high]}
                    print(key_levels)
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                                 indicator='DOWN_BREAK_3',
                                 signal=1,
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 info=last_tick, key_levels=key_levels)
                    self.release_signal(pat)
                    self.down_break_level_type_3.add(local_high)

        except Exception as e:
            print(e)

    def build_down_break_reversal(self):
        try:
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            for level in self.down_break_level_type_1:
                if last_tick['close'] > level:
                    self.down_break_level_type_1.remove(level)
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                                 indicator='DOWN_BREAK_REVERSAL_1',
                                 signal=1,
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 info=last_tick)
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    self.release_signal(pat)
            for level in self.down_break_level_type_2:
                if last_tick['close'] > level:
                    self.down_break_level_type_2.remove(level)
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                                 indicator='DOWN_BREAK_REVERSAL_2',
                                 signal=1,
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 info=last_tick)
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    self.release_signal(pat)
            for level in self.down_break_level_type_3.copy():
                if last_tick['close'] > level:
                    self.down_break_level_type_3.remove(level)
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                                 indicator='DOWN_BREAK_REVERSAL_3',
                                 signal=1,
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 info=last_tick)
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    self.release_signal(pat)


        except Exception as e:
            print(e)

    def bearish_engulfing_high_put_volume(self):
        try:
            print('bearish_engulfing_high_put_volume ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            ten_period_signals = self.get_n_period_signals(self.last_ts, 10)
            EMA_1_10 = self.check_signal_present(ten_period_signals[-1], ('TECHNICAL', 'EMA_1_10'))['value']
            SMA_1_10 = self.check_signal_present(ten_period_signals[-1], ('TECHNICAL', 'SMA_1_10'))['value']
            one_bearish_candle_resp = self.check_signal_present(ten_period_signals[-1], ('CANDLE_1', 'CDL_DIR_N'))
            one_bearish_candle = one_bearish_candle_resp['found']
            one_body_large = self.check_signal_present(ten_period_signals[-1], ('CANDLE_1', 'CDL_BD_L'))['found']

            one_high_put_volume_candle_type_1 = self.check_signal_present(ten_period_signals[-1], ('OPTION_MARKET', 'HIGH_VOL_PUT_1'))['found']
            bearish_engulfing = False #CANDLE_1 CDLENGULFING_BUY
            local_high = None
            for idx in range(len(ten_period_signals)-2, -1, -1):
                #print("idx====", idx)
                bearish_engulfing_resp = self.check_signal_present(ten_period_signals[idx], ('CANDLE_1', 'CDLENGULFING_SELL'))
                bearish_engulfing = bearish_engulfing_resp['found']
                if bearish_engulfing:
                    #print(bearish_engulfing_resp['signal'].info['candle'])
                    local_high = max(bearish_engulfing_resp['signal'].info['candle'])
                    print('one_bearish_candle found+++++', one_bearish_candle)
                    print('one_body_large found+++++', one_body_large)
                    print('one_high_put_volume_candle_type_1 found+++++', one_high_put_volume_candle_type_1)
                    break
            last_tick = self.asset_book.spot_book.spot_processor.last_tick
            if self.not_none_eval(EMA_1_10, SMA_1_10) and EMA_1_10 < SMA_1_10:
                if bearish_engulfing and one_high_put_volume_candle_type_1 and one_bearish_candle and one_body_large:

                    key_levels = {'spot_long_target_levels': [], 'spot_long_stop_loss_levels': [],
                                  'spot_short_target_levels': [], 'spot_short_stop_loss_levels': [local_high]}
                    pat = Signal(asset=self.asset_book.spot_book.asset, category='CANDLE_' + str(1), instrument="",
                                 indicator='BEARISH_ENGULFING_HIGH_PUT_VOLUME',
                                 signal=1,
                                 strength=1,
                                 signal_time=self.last_ts,
                                 notice_time=self.asset_book.spot_book.spot_processor.last_tick['timestamp'],
                                 info=last_tick, key_levels=key_levels)
                    self.release_signal(pat)

        except Exception as e:
            print(e)

    def print_signals(self):
        for ts in self.signal_dict.keys():
            for signal in self.signal_dict[ts]:
                print(signal.category, signal.indicator)

    def print_signals_last_ts(self):
        print('print_signals_last_ts++++++++++++++++++++++ start==')
        for signal in self.signal_dict[self.last_ts]:
            print(signal.category, signal.indicator)
        print('print_signals_last_ts++++++++++++++++++++++ end==')