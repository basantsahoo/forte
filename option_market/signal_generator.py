
import pandas as pd
import numpy as np
from datetime import datetime
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from tabulate import tabulate
from talib import stream
from option_market.technical.cross_over import DownCrossOver, BuildUpFollowingMomentum, OptionVolumeIndicator
from config import oi_denomination

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
        total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()
        total_volume = [x + y for x, y in zip(call_volume_series, put_volume_series)]
        if self.live_mode and self.option_matrix.last_time_stamp and call_oi_series:
            start_call_oi = [x for x in call_oi_series if x > 0][0]
            start_put_oi = [x for x in put_oi_series if x > 0][0]
            start_total_oi = [x for x in total_oi if x > 0][0]


            t_time = TradeDateTime(self.option_matrix.last_time_stamp)
            print('time == ', t_time.date_time.hour, ":", t_time.date_time.minute)
            max_total_oi = max(total_oi)
            poi_total_oi = total_oi[-1]
            poi_call_oi = call_oi_series[-1]
            poi_put_oi =  put_oi_series[-1]
            call_drop_pct = np.round( poi_call_oi * 1.00 / max(call_oi_series) -1, 2)
            put_drop_pct = np.round(poi_put_oi * 1.00 / max(put_oi_series) -1, 2)
            total_drop_pct = np.round(poi_total_oi * 1.00 / max_total_oi - 1, 2)
            call_build_up = np.round(call_oi_series[-1] / start_call_oi - 1, 2)
            put_build_up = np.round(put_oi_series[-1] / start_put_oi - 1, 2)
            total_build_up = np.round(total_oi[-1] / start_total_oi - 1, 2)
            pcr_minus_1 = np.round(poi_put_oi/poi_call_oi - 1, 2)
            #print(call_volume_series)

            table = [
                ['', 'Call', 'Put', 'Total'],
                ['Max', max(call_oi_series)/oi_denomination, max(put_oi_series)/oi_denomination, max_total_oi/oi_denomination],
                ['POI', poi_call_oi/oi_denomination, poi_put_oi/oi_denomination, poi_total_oi/oi_denomination],
                ['Drop', call_drop_pct, put_drop_pct, total_drop_pct],
                ['Buildup', call_build_up, put_build_up, total_build_up],
                ['Volume', OptionVolumeIndicator.calc_scale(call_volume_series), OptionVolumeIndicator.calc_scale(put_volume_series), OptionVolumeIndicator.calc_scale(total_volume)],
                ['pcr_minus_1', '', '', pcr_minus_1]
            ]
            print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))
            cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp-240)
            call_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'CE'}
            put_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'PE'}
            #print('spot===', day_capsule.cross_analyser.get_instrument_series()[-1])
            print('Call stats==')
            call_cross_stats_table = self.get_cross_stats_table(call_cross_stats)
            print(tabulate(call_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

            print('put stats==')
            put_cross_stats_table = self.get_cross_stats_table(put_cross_stats)
            print(tabulate(put_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

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

        spot_series = day_capsule.cross_analyser.get_instrument_series()
        vol_series = day_capsule.cross_analyser.get_instrument_series('22200_CE')
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

        spot_series = day_capsule.cross_analyser.get_instrument_series()
        vol_series = day_capsule.cross_analyser.get_instrument_series('22200_CE')
        #print(vol_series)
        """"""
        self.call_down_cross_over.evaluate(call_oi_series, put_oi_series)
        self.put_down_cross_over.evaluate(put_oi_series, call_oi_series)
        self.build_up_calculator.evaluate(spot_series, call_oi_series, put_oi_series)
        self.option_volume_indicator.evaluate(call_volume_series, put_volume_series)
