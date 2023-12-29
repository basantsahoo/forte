"""
OptionMatrix:
capsule (
    trading_data:{
        '2023-12-01':capsule(
                        trading_data:{
                            '4200_CE':capsule(
                                          trading_data:{
                                              epoc1: cell(
                                                        ion
                                                        analytics
                                                    )
                                          }
                                    )
                        },
                        transposed_data: {
                            epoc1: {
                                '4200_CE': cell
                            }
                        },
                        cross_analyser: None
                    )
    }
    analytics:{}
    )
"""


import pandas as pd
import numpy as np
from datetime import datetime
from db.market_data import get_daily_option_ion_data
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from option_market.building_blocks import Capsule, Cell, Ion
from option_market.analysers import IntradayCrossAssetAnalyser
from option_market.analysers import OptionMatrixAnalyser
from option_market.data_loader import MultiDayOptionDataLoader
from entities.trading_day import TradeDateTime

class PriceThrottler:
    def __init__(self, matrix, feed_speed, throttle_speed=0):
        self.matrix = matrix
        self.feed_speed = feed_speed if feed_speed > 1 else 1
        self.throttle_speed = throttle_speed if throttle_speed > 1 else 1
        self.aggregation_factor = self.throttle_speed/feed_speed
        #print(self.aggregation_factor)
        self.pushed_frame_start = None
        self.last_frame_start = None
        self.ion_dict = {}
        self.current_date = None

    def update_ion_cell(self, current_frame, instrument, ion):
        if instrument not in self.ion_dict:
            ion_cell = Cell(timestamp=current_frame, instrument=instrument)
            ion_cell.update_ion(ion)
            self.ion_dict[instrument] = ion_cell
        else:
            ion_cell = self.ion_dict[instrument]
            if self.aggregation_factor > 1:
                ion.volume = ion.volume + ion_cell.ion.volume
            ion_cell.update_ion(ion)



    def throttle(self, instrument_data_list):
        for instrument_data in instrument_data_list:
            trade_date = instrument_data['trade_date']
            self.current_date = trade_date
            epoc_minute = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            current_frame = int(int(epoc_minute/(self.aggregation_factor * 60)) * self.aggregation_factor * 60)
            if self.last_frame_start != current_frame:
                #print(current_frame)
                self.push()
                self.pushed_frame_start = self.last_frame_start
                self.last_frame_start = current_frame
            instrument = instrument_data['instrument']
            ion = Ion.from_raw(instrument_data['ion'])
            self.update_ion_cell(current_frame, instrument, ion)

    def push(self):
        self.matrix.add_cells(self.current_date, list(self.ion_dict.values()))
        self.ion_dict = {}
        self.matrix.generate_signal()


class OptionMatrix:

    def __init__(self,  feed_speed=1, throttle_speed=15, instant_compute=True, live_mode=False):
        self.capsule = Capsule()
        self.instant_compute = instant_compute
        self.matrix_analyser = OptionMatrixAnalyser(self)
        self.current_date = None
        self.signal_generator = OptionSignalGenerator(self, live_mode)
        self.price_throttler = PriceThrottler(self, feed_speed, throttle_speed)
        self.live_mode = live_mode
        self.counter = 0
        self.last_time_stamp = None

    def process_feed(self, instrument_data_list):
        self.current_date = instrument_data_list[0]['trade_date']
        self.price_throttler.throttle(instrument_data_list)

    def get_day_capsule(self, trade_date):
        return self.capsule.trading_data[trade_date]

    def get_instrument_capsule(self, trade_date, instrument):
        return self.capsule.trading_data[trade_date].trading_data[instrument]

    def add_cells(self, trade_date, cell_list):
        self.counter += 1
        if cell_list:
            self.last_time_stamp = cell_list[0].timestamp
            #print(cell_list[0].instrument)
            print("==========================================", self.counter)
        timestamp_set = set()
        if not self.capsule.in_trading_data(trade_date):
            capsule = Capsule()
            cross_analyser = IntradayCrossAssetAnalyser(capsule)
            capsule.cross_analyser = cross_analyser
            self.capsule.insert_trading_data(trade_date, capsule)
        day_capsule = self.get_day_capsule(trade_date)
        for cell in cell_list:
            if not day_capsule.in_trading_data(cell.instrument):
                day_capsule.insert_trading_data(cell.instrument, Capsule())
            instrument_capsule = self.get_instrument_capsule(trade_date, cell.instrument)
            instrument_capsule.insert_trading_data(cell.timestamp, cell)
            day_capsule.insert_transposed_data(cell.timestamp, cell.instrument, cell)
            cell.fresh_born(instrument_capsule)
            timestamp_set.add(cell.timestamp)
        if self.instant_compute:
            day_capsule.cross_analyser.compute(list(timestamp_set))

    def generate_signal(self):
        if self.instant_compute:
            self.signal_generator.generate()

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
        self.generate_intra_day_call_oi_drop_signal()

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
        if self.live_mode and self.option_matrix.last_time_stamp:
            print(self.option_matrix.last_time_stamp)
            t_time = TradeDateTime(self.option_matrix.last_time_stamp)
            print('time == ', t_time.date_time.hour, ":", t_time.date_time.minute)
            max_total_oi = max(total_oi)
            poi_total_oi =  total_oi[-1]
            poi_call_oi = call_oi_series[-1]
            poi_put_oi =  put_oi_series[-1]
            call_drop_pct = np.round( poi_call_oi * 1.00 / max(call_oi_series) -1, 2)
            put_drop_pct = np.round(poi_put_oi * 1.00 / max(put_oi_series) -1, 2)
            total_drop_pct = np.round(poi_total_oi * 1.00 / max_total_oi - 1, 2)
            pcr_minus_1 = np.round(poi_put_oi/poi_call_oi -1, 2)
            #print('max_total_oi == ', max_total_oi, 'poi_total_oi == ', poi_total_oi)
            #print('poi_call_oi == ', poi_call_oi, 'poi_put_oi == ', poi_put_oi)
            #print('call_drop_pct == ', call_drop_pct, 'put_drop_pct == ', put_drop_pct)
            #print('pcr_minus_1 == ',  pcr_minus_1)
            from tabulate import tabulate
            table = [
                ['', 'Call', 'Put', 'Total'],
                ['Max', max(call_oi_series)/10000000, max(put_oi_series)/10000000, max_total_oi/10000000],
                ['POI', poi_call_oi/10000000, poi_put_oi/10000000, poi_total_oi/10000000],
                ['Drop', call_drop_pct, put_drop_pct, total_drop_pct],
                ['pcr_minus_1', '', '', pcr_minus_1]
            ]
            print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))

        return signal
