import os
import pandas as pd
import numpy as np
import time
from datetime import datetime
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from tabulate import tabulate
from talib import stream
from option_market.technical.cross_over import DownCrossOver, BuildUpFollowingMomentum, OptionVolumeIndicator
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

    def generate(self):
        #self.print_instant_info()
        self.print_stats()
        #self.generate_intra_day_call_oi_drop_signal()
        #self.run_external_generators()
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
        #print(day_capsule.cross_analyser.call_oi)
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        total_oi_series = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()
        total_volume_series = [x + y for x, y in zip(call_volume_series, put_volume_series)]

        prev_call_median_volume = sum([value for key, value in day_capsule.cross_analyser.avg_volumes.items() if key[-2::] == 'CE'])
        prev_put_median_volume = sum([value for key, value in day_capsule.cross_analyser.avg_volumes.items() if key[-2::] == 'PE'])
        prev_median_total_volume = prev_call_median_volume + prev_put_median_volume

        day_normalization_factor = 1 if len(total_volume_series) < 3000 else (np.median(total_volume_series) / prev_median_total_volume)

        if self.live_mode and self.option_matrix.last_time_stamp and call_oi_series:

            start_call_oi = day_capsule.cross_analyser.total_closing_call_oi
            start_put_oi = day_capsule.cross_analyser.total_closing_put_oi
            start_total_oi = start_call_oi + start_put_oi
            print('start_call_oi====', start_call_oi)
            print('start_put_oi====', start_put_oi)
            t_time = TradeDateTime(self.option_matrix.last_time_stamp)
            print('time ==========================================================================',
                  t_time.date_time.hour, ":", t_time.date_time.minute)
            max_total_oi = max(total_oi_series)
            poi_total_oi = total_oi_series[-1]
            poi_call_oi = call_oi_series[-1]
            poi_put_oi = put_oi_series[-1]
            call_drop_pct = np.round( poi_call_oi * 1.00 / max(call_oi_series) -1, 2)
            put_drop_pct = np.round(poi_put_oi * 1.00 / max(put_oi_series) -1, 2)
            total_drop_pct = np.round(poi_total_oi * 1.00 / max_total_oi - 1, 2)
            call_build_up = np.round((call_oi_series[-1] - start_call_oi)/start_total_oi, 2)
            put_build_up = np.round((put_oi_series[-1] - start_put_oi)/start_total_oi, 2)
            total_build_up = np.round(total_oi_series[-1] / start_total_oi - 1, 2)
            pcr_minus_1 = np.round(poi_put_oi/poi_call_oi - 1, 2)
            t_2_call_oi = call_oi_series[-2] if len(call_oi_series) > 2 else start_call_oi
            t_2_put_oi = put_oi_series[-2] if len(put_oi_series) > 2 else start_put_oi
            t_total_oi = total_oi_series[-2] if len(total_oi_series) > 2 else start_total_oi
            call_addition = np.round((call_oi_series[-1] - t_2_call_oi)/start_total_oi, 4)
            put_addition = np.round((put_oi_series[-1] - t_2_put_oi) /start_total_oi, 4)
            total_addition = np.round((total_oi_series[-1] - t_total_oi) /start_total_oi, 4)
            #print(call_volume_series)
            call_scale = OptionVolumeIndicator.calc_scale(call_volume_series, prev_median_total_volume * 0.5, day_normalization_factor)
            put_scale = OptionVolumeIndicator.calc_scale(put_volume_series, prev_median_total_volume * 0.5, day_normalization_factor)
            table = [
                ['', 'Call', 'Put', 'Total'],
                ['Max', np.round(max(call_oi_series)/oi_denomination, 2), np.round(max(put_oi_series)/oi_denomination, 2), np.round(max_total_oi/oi_denomination,2)],
                ['POI', np.round(poi_call_oi/oi_denomination,2), np.round(poi_put_oi/oi_denomination,2), np.round(poi_total_oi/oi_denomination,2)],
                ['Drop', call_drop_pct, put_drop_pct, total_drop_pct],
                ['Buildup', call_build_up, put_build_up, total_build_up],
                ['Addition(T-1)', call_addition, put_addition, total_addition],
                ['Volume', call_scale, put_scale, OptionVolumeIndicator.calc_scale(total_volume_series, prev_median_total_volume, day_normalization_factor)],
                ['pcr_minus_1', '', '', pcr_minus_1]
            ]
            print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))
            cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)
            call_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'CE'}
            put_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'PE'}
            """
            if call_scale > 2 and put_scale > 2:
                self.play_both_sound()
            else:
                if put_scale > 2:
                    self.play_put_sound()

                elif call_scale > 2:
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


    def run_external_generators(self):
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
        print(signal.name)


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

    def run_dynamic_analysis(self):
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
