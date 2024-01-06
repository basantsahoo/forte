import os
import pandas as pd
import numpy as np
import time
from datetime import datetime
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from tabulate import tabulate
from talib import stream
from option_market.technical.cross_over import DownCrossOver, BuildUpFollowingMomentum, OptionVolumeIndicator, OptionMomemntumIndicator
from config import oi_denomination
from beepy import beep
from subprocess import call


class OptionSignalGenerator:
    def __init__(self, matrix, live_mode=False):
        self.option_matrix = matrix
        self.trade_hold_period = 30
        self.roll_period = 30
        self.max_oi = 0
        self.attention_oi = 1
        self.minutes_past = 0
        self.live_mode = live_mode
        self.inform_hour = 15
        self.call_down_cross_over = DownCrossOver('CALL_DOWN_CROSS', 0.05, call_back_fn=self.dispatch_signal)
        self.put_down_cross_over = DownCrossOver('PUT_DOWN_CROSS', 0.05, call_back_fn=self.dispatch_signal)
        self.build_up_calculator = BuildUpFollowingMomentum('BUILDUP', call_back_fn=self.dispatch_signal)
        self.option_volume_indicator = OptionVolumeIndicator('OPTION_VOLUME', call_back_fn=self.dispatch_signal)
        self.bullish_option_momentum_indicator = OptionMomemntumIndicator('BULLISH_MOMENTUM', info_fn=self.get_info, call_back_fn=self.dispatch_signal)
        self.bearish_option_momentum_indicator = OptionMomemntumIndicator('BEARISH_MOMENTUM', info_fn=self.get_info, call_back_fn=self.dispatch_signal)
        self.signal_dispatcher = None

    def get_info(self):
        return {'timestamp': self.option_matrix.last_time_stamp,
                'asset': self.option_matrix.asset}
    def generate(self):
        #self.print_instant_info()
        self.print_stats()
        self.run_external_generators()
        #self.generate_intra_day_call_oi_drop_signal()
        #self.run_dynamic_analysis()
        pass

    def print_instant_info(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        if self.option_matrix.last_time_stamp == 1703843700:
            for key, cell in day_capsule.transposed_data[1703843700].items():
                info = cell.ion.oi if cell.ion.category == 'option' else cell.ion.close
                print(key, " ", cell.instrument, " ", cell.timestamp, " ", info)


    def print_stats(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()

        if self.live_mode and self.option_matrix.last_time_stamp and call_oi_series:
            aggregate_stats = day_capsule.cross_analyser.get_aggregate_stats(self.option_matrix.last_time_stamp)
            aggregate_stat_table = self.get_aggregate_stats_table(aggregate_stats)
            print(tabulate(aggregate_stat_table, headers='firstrow', tablefmt='fancy_grid'))
            cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)
            call_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'CE'}
            put_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'PE'}
            """
            if aggregate_stats['call_volume_scale'] > 2 and aggregate_stats['put_volume_scale'] > 2:
                self.play_both_sound()
            else:
                if aggregate_stats['put_volume_scale'] > 2:
                    self.play_put_sound()

                elif aggregate_stats['call_volume_scale'] > 2:
                    self.play_call_sound()
            """
            #print('spot===', day_capsule.cross_analyser.get_instrument_ion_field_series()[-1])
            if self.option_matrix.print_cross_stats:
                print('Call stats==')
                call_cross_stats_table = self.get_cross_stats_table(call_cross_stats)
                print(tabulate(call_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

                print('put stats==')
                put_cross_stats_table = self.get_cross_stats_table(put_cross_stats)
                print(tabulate(put_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

    def play_call_sound(self):
        #beep(sound='coin')
        #os.system('afplay /System/Library/Sounds/Sosumi.aiff')
        #os.system('say "Call time."')
        #call(["afplay", "/System/Library/Sounds/Sosumi.aiff'"])
        print('\007')
        time.sleep(0.5)
    def play_put_sound(self):
        #beep(sound='robot_error')
        #os.system('afplay /System/Library/Sounds/Glass.aiff')
        #os.system('say "No Call time."')
        #call(["aplay", "/System/Library/Sounds/Glass.aiff'"])
        print('\007')
        time.sleep(0.5)
    def play_both_sound(self):
        #beep(sound='success')
        #os.system('afplay /System/Library/Sounds/Hero.aiff')
        #os.system('say "Draw time."')
        #call(["aplay", "/System/Library/Sounds/Hero.aiff'"])
        print('\007')
        time.sleep(0.5)

    def get_cross_stats_table(self, cross_stats):
        cross_stats_table = []
        inst_keys = [key[:-3] for key in list(cross_stats.keys())]
        cross_stats_table.append([""] + inst_keys)
        first_item = list(cross_stats.values())[0]
        for key in first_item.keys():
            lst = [key]
            for inst_data in cross_stats.values():
                lst.append(inst_data[key])
            cross_stats_table.append(lst)
        return cross_stats_table

    def get_aggregate_stats_table(self, aggregate_stats):
        table = [
            ['', 'Call', 'Put', 'Total'],
            ['Max', aggregate_stats['max_call_oi'], aggregate_stats['max_put_oi'], aggregate_stats['max_total_oi']],
            ['POI', aggregate_stats['poi_call_oi'], aggregate_stats['poi_put_oi'], aggregate_stats['poi_total_oi']],
            ['Drop', aggregate_stats['call_drop'], aggregate_stats['put_drop'], aggregate_stats['total_drop']],
            ['Buildup', aggregate_stats['call_build_up'], aggregate_stats['put_build_up'], aggregate_stats['total_build_up']],
            ['Addition(T-1)', aggregate_stats['call_addition'], aggregate_stats['put_addition'], aggregate_stats['total_addition']],
            ['Volume', aggregate_stats['call_volume_scale'], aggregate_stats['put_volume_scale'], aggregate_stats['total_volume_scale']],
            ['pcr_minus_1', '', '', aggregate_stats['pcr_minus_1']]
        ]
        return table


    def run_external_generators(self):
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()
        aggregate_stats = day_capsule.cross_analyser.get_aggregate_stats(self.option_matrix.last_time_stamp)
        cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)

        put_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'PE'}
        call_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'CE'}
        self.bullish_option_momentum_indicator.evaluate(aggregate_stats['call_volume_scale'], call_vwap, put_vwap)
        self.bearish_option_momentum_indicator.evaluate(aggregate_stats['put_volume_scale'], put_vwap, call_vwap)

    def run_external_generators_old(self):
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()

        spot_series = day_capsule.cross_analyser.get_instrument_ion_field_series()
        vol_series = day_capsule.cross_analyser.get_instrument_ion_field_series('22200_CE')
        #print(vol_series)
        """"""
        self.call_down_cross_over.evaluate(call_oi_series, put_oi_series)
        self.put_down_cross_over.evaluate(put_oi_series, call_oi_series)
        self.build_up_calculator.evaluate(spot_series, call_oi_series, put_oi_series)
        self.option_volume_indicator.evaluate(call_volume_series, put_volume_series)


    def dispatch_signal(self, signal):
        #print(signal.name, TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        print('------------------------------------', signal.category)
        if self.signal_dispatcher:
            self.signal_dispatcher(signal)


    def generate_intra_day_call_oi_drop_signal(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        last_oi = call_oi_series[-1] if call_oi_series else 1
        if last_oi > self.max_oi:
            self.max_oi = last_oi
        if last_oi > self.attention_oi:
            self.attention_oi = last_oi
        signal = 0
        if len(call_oi_series) >= self.roll_period / self.option_matrix.option_data_throttler.aggregation_factor:
            #print(call_oi_series)
            mean_oi = np.mean(call_oi_series[-int(self.roll_period / self.option_matrix.option_data_throttler.aggregation_factor):-1])
            if (last_oi * 1.00 / mean_oi) - 1 > 0.01:
                # print('Buildup++++++')
                pass
            elif (last_oi * 1.00 / self.attention_oi) - 1 < -0.05:
                print('covering----', last_oi)
                print(self.option_matrix.option_data_throttler.last_frame_start)
                if last_oi == 0:
                    for ts, cross in day_capsule.transposed_data.items():
                        for inst, cell in cross.items():
                            if inst != 'spot':
                                print(ts," ", inst," ", cell.ion.oi)

                # print((last_oi * 1.00 / self.attention_oi) - 1)
                self.attention_oi = last_oi
                #self.attention_oi = max(last_oi,1) #Hack for divisible by 0
                signal = 1

            else:
                # print('balance====')
                pass

        return signal
