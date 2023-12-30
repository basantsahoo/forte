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
from option_market.building_blocks import Capsule, Cell
from option_market.analysers import IntradayCrossAssetAnalyser
from option_market.analysers import OptionMatrixAnalyser
from option_market.throttlers import OptionFeedThrottler, FeedThrottler
from option_market.signal_generator import OptionSignalGenerator

from option_market.data_loader import MultiDayOptionDataLoader
from entities.trading_day import TradeDateTime
from tabulate import tabulate


class OptionMatrix:

    def __init__(self,  feed_speed=1, throttle_speed=15, instant_compute=True, live_mode=False):
        self.capsule = Capsule()
        self.instant_compute = instant_compute
        self.matrix_analyser = OptionMatrixAnalyser(self)
        self.current_date = None
        self.signal_generator = OptionSignalGenerator(self, live_mode)
        self.option_data_throttler = OptionFeedThrottler(self, feed_speed, throttle_speed)
        self.data_throttler = FeedThrottler(self, feed_speed, throttle_speed)
        self.live_mode = live_mode
        self.counter = 0
        self.last_time_stamp = None

    def process_option_feed(self, instrument_data_list):
        self.current_date = instrument_data_list[0]['trade_date']
        self.option_data_throttler.throttle(instrument_data_list)

    def process_feed_without_signal(self, instrument_data_list):
        #self.current_date = instrument_data_list[0]['trade_date']
        self.data_throttler.throttle(instrument_data_list)

    def get_day_capsule(self, trade_date):
        return self.capsule.trading_data[trade_date]

    def get_instrument_capsule(self, trade_date, instrument):
        return self.capsule.trading_data[trade_date].trading_data[instrument]

    def add_cells(self, trade_date, cell_list):
        self.counter += 1
        if cell_list:
            self.last_time_stamp = cell_list[0].timestamp
            #print(self.counter)
            """
            if self.last_time_stamp == 1703843580:
                for cell in cell_list:
                    print(cell.instrument, " ", cell.timestamp, " ", cell.ion.oi)
            """
            #print(cell_list[0].instrument)
            #print("==========================================", self.counter)
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
            cell.validate_ion_data()
            timestamp_set.add(cell.timestamp)
        if self.instant_compute:
            day_capsule.cross_analyser.compute(list(timestamp_set))

    def generate_signal(self):
        if self.instant_compute:
            self.signal_generator.generate()


