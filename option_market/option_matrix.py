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
from datetime import datetime
from db.market_data import get_daily_option_ion_data
from collections import OrderedDict
from entities.trading_day import TradeDateTime
from option_market.building_blocks import Capsule, Cell, Ion
from option_market.analysers import IntradayCrossAssetAnalyser
from option_market.analysers import OptionMatrixAnalyser


class OptionIonBuilder:
    def __init__(self, asset, trade_day):
        ion_data_df = get_daily_option_ion_data(asset, trade_day)
        ion_data_df['trade_date'] = trade_day
        self.ion_data = ion_data_df.to_dict("records")

class MultiDayOptionDataLoader:
    def __init__(self, asset="NIFTY", trade_days=[]):
        self.option_ions = OrderedDict()
        start = datetime.now()
        for day in trade_days:
            ob = OptionIonBuilder(asset, day)
            self.option_ions[day] = ob.ion_data
        end = datetime.now()
        print('option data loading took===', (end-start).total_seconds())
        self.data_present = True

    def generate_next_feed(self):
        if list(self.option_ions.keys()):
            day_key = list(self.option_ions.keys())[0]
            next_feed = self.option_ions[day_key].pop(0)
            if not self.option_ions[day_key]:
                del self.option_ions[day_key]
            return [next_feed]
        else:
            self.data_present = False
            return []


class PriceThrottler:
    def __init__(self, matrix, feed_speed, throttle_speed=0):
        self.matrix = matrix
        self.feed_speed = feed_speed
        self.throttle_speed = throttle_speed if throttle_speed > 1 else 1
        self.last_frame_end = None
        self.ion_dict = {}

    def throttle(self, instrument_data_list):
        for instrument_data in instrument_data_list:
            timestamp = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            current_frame = int(timestamp/(self.throttle_speed * 60)) * 60
            if self.last_frame_end != current_frame:
                self.last_frame_end = current_frame
                self.push()
            instrument = instrument_data['instrument']
            epoc_minute = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])

    def push(self):
        pass

class OptionMatrix:

    def __init__(self, instant_compute=True, feed_speed=1, throttle_speed=15):
        self.capsule = Capsule()
        self.instant_compute = instant_compute
        self.matrix_analyser = OptionMatrixAnalyser(self)
        self.current_date = None
        self.last_time_stamp = None
        self.signal_generator = OptionSignalGenerator(self)
        self.price_throttler = PriceThrottler(self, feed_speed, throttle_speed)

    def process_feed(self, instrument_data_list):
        self.price_throttler.throttle(instrument_data_list)

    def get_day_capsule(self, trade_date):
        return self.capsule.trading_data[trade_date]

    def get_instrument_capsule(self, instrument_data):
        return self.capsule.trading_data[instrument_data['trade_date']].trading_data[instrument_data['instrument']]

    def get_timestamp_cell(self, instrument_data):
        timestamp = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
        return self.capsule.trading_data[instrument_data['trade_date']].trading_data[instrument_data['instrument']].trading_data[timestamp]

    def process_feed_2(self, instrument_data_list):
        timestamp_set = set()
        for instrument_data in instrument_data_list:
            timestamp = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            if self.last_time_stamp != timestamp:
                self.last_time_stamp = timestamp
                self.signal_generator.generate()

            trade_date = instrument_data['trade_date']
            self.current_date = trade_date
            instrument = instrument_data['instrument']

            timestamp_set.add(timestamp)
            if not self.capsule.in_trading_data(trade_date):
                capsule = Capsule()
                cross_analyser = IntradayCrossAssetAnalyser(capsule)
                capsule.cross_analyser = cross_analyser
                self.capsule.insert_trading_data(trade_date, capsule)
            day_capsule = self.get_day_capsule(trade_date)

            if not day_capsule.in_trading_data(instrument):
                day_capsule.insert_trading_data(instrument, Capsule())

            instrument_capsule = self.get_instrument_capsule(instrument_data)

            if not instrument_capsule.in_trading_data(timestamp):
                ion_cell = Cell(timestamp=timestamp, instrument=instrument)
                instrument_capsule.insert_trading_data(timestamp, ion_cell)
                day_capsule.insert_transposed_data(timestamp, instrument, ion_cell)
                ion_cell.fresh_born(instrument_capsule)
            else:
                ion_cell = self.get_timestamp_cell(timestamp)
            #print(instrument_data['ion'])
            ion = Ion.from_raw(instrument_data['ion'])
            ion_cell.update_ion(ion)
            ion_cell.validate_ion_data()
            ion_cell.analyse()
            if self.instant_compute:
                day_capsule.cross_analyser.compute(list(timestamp_set))
            #print(ion_cell.analytics)


class OptionSignalGenerator:

    def __init__(self, matrix):
        self.option_matrix = matrix
        self.candle_minutes = 15
        self.trade_hold_period = 30
        self.roll_period = 30


    def generate(self):
        self.generate_intra_day_oi_drop_signal()

    def generate_intra_day_oi_drop_signal(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        """
        if len(self.total_oi_series) >= roll_period / candle_minutes:
            last_oi = self.total_oi_series[-1]
            mean_oi = np.mean(self.total_oi_series[-int(roll_period / candle_minutes):-1])
            if (last_oi * 1.00 / mean_oi) - 1 > 0.01:
                # print('Buildup++++++')
                pass
            elif (last_oi * 1.00 / self.attention_oi) - 1 < -0.05:
                print('covering----')
                # print((last_oi * 1.00 / self.attention_oi) - 1)
                self.attention_oi = last_oi
                signal = 1
            else:
                # print('balance====')
                pass
        return signal
        """

