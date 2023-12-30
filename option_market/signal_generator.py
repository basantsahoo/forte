
import pandas as pd
import numpy as np
from datetime import datetime
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from entities.trading_day import TradeDateTime
from tabulate import tabulate


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

    def generate(self):
        self.print_stats()
        self.generate_intra_day_call_oi_drop_signal()

    def print_stats(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        if self.live_mode and self.option_matrix.last_time_stamp:
            t_time = TradeDateTime(self.option_matrix.last_time_stamp)
            print('time == ', t_time.date_time.hour, ":", t_time.date_time.minute)
            max_total_oi = max(total_oi)
            poi_total_oi = total_oi[-1]
            poi_call_oi = call_oi_series[-1]
            poi_put_oi =  put_oi_series[-1]
            call_drop_pct = np.round( poi_call_oi * 1.00 / max(call_oi_series) -1, 2)
            put_drop_pct = np.round(poi_put_oi * 1.00 / max(put_oi_series) -1, 2)
            total_drop_pct = np.round(poi_total_oi * 1.00 / max_total_oi - 1, 2)
            pcr_minus_1 = np.round(poi_put_oi/poi_call_oi -1, 2)

            table = [
                ['', 'Call', 'Put', 'Total'],
                ['Max', max(call_oi_series)/10000000, max(put_oi_series)/10000000, max_total_oi/10000000],
                ['POI', poi_call_oi/10000000, poi_put_oi/10000000, poi_total_oi/10000000],
                ['Drop', call_drop_pct, put_drop_pct, total_drop_pct],
                ['pcr_minus_1', '', '', pcr_minus_1]
            ]
            print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))
        """
        if self.option_matrix.last_time_stamp == 1703843700:
            for key, cell in day_capsule.transposed_data[1703843700].items():
                print(key, " ", cell.instrument, " ", cell.timestamp, " ", cell.ion.oi)
        """

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
        if len(call_oi_series) >= self.roll_period / self.option_matrix.price_throttler.aggregation_factor:
            #print(call_oi_series)
            mean_oi = np.mean(call_oi_series[-int(self.roll_period / self.option_matrix.price_throttler.aggregation_factor):-1])
            if (last_oi * 1.00 / mean_oi) - 1 > 0.01:
                # print('Buildup++++++')
                pass
            elif (last_oi * 1.00 / self.attention_oi) - 1 < -0.05:
                print('covering----', last_oi)
                """
                if last_oi == 0:
                    for ts, cross in day_capsule.transposed_data.items():
                        for inst, cell in cross.items():
                            print(ts," ", inst," ", cell.ion.oi)
                """
                # print((last_oi * 1.00 / self.attention_oi) - 1)
                self.attention_oi = last_oi
                #self.attention_oi = max(last_oi,1) #Hack for divisible by 0
                signal = 1
                print(self.option_matrix.price_throttler.last_frame_start)
            else:
                # print('balance====')
                pass

        return signal