import pandas as pd
from datetime import datetime
from db.market_data import get_daily_option_ion_data
from collections import OrderedDict
from entities.trading_day import TradeDateTime

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

class Capsule:
    def __init__(self):
        self.trading_data = OrderedDict()
        self.analytics = {}

    def in_trading_data(self, key):
        return key in list(self.trading_data.keys())

    def insert_trading_data(self, key, data):
        self.trading_data[key] = data

    def insert_analytics(self, key, data):
        self.analytics[key] = data


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
                        }
                    )
    }
    analytics:{}
    )
"""

class OptionMatrix:

    def __init__(self):
        self.capsule = Capsule()

    def get_day_capsule(self, instrument_data):
        return self.capsule.trading_data[instrument_data['trade_date']]

    def get_instrument_capsule(self, instrument_data):
        return self.capsule.trading_data[instrument_data['trade_date']].trading_data[instrument_data['instrument']]

    def get_timestamp_cell(self, instrument_data):
        timestamp = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
        return self.capsule.trading_data[instrument_data['trade_date']].trading_data[instrument_data['instrument']].trading_data[timestamp]

    def process_feed(self, instrument_data_list):
        for instrument_data in instrument_data_list:
            trade_date = instrument_data['trade_date']
            instrument = instrument_data['instrument']
            timestamp = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            if not self.capsule.in_trading_data(trade_date):
                self.capsule.insert_trading_data(trade_date, Capsule())
            day_capsule = self.get_day_capsule(instrument_data)

            if not day_capsule.in_trading_data(instrument):
                day_capsule.insert_trading_data(instrument, Capsule())

            instrument_capsule = self.get_instrument_capsule(instrument_data)

            if not instrument_capsule.in_trading_data(timestamp):
                ion_cell = Cell(identifier=timestamp)
                instrument_capsule.insert_trading_data(timestamp, ion_cell)
                ion_cell.fresh_born(instrument_capsule)
            else:
                ion_cell = self.get_timestamp_cell(timestamp)
            #print(instrument_data['ion'])
            ion = Ion.from_raw(instrument_data['ion'])
            ion_cell.update_ion(ion)
            ion_cell.validate_ion_data()
            ion_cell.analyse()
            #print(ion_cell.analytics)





class OptionMatrixAnalyser:
    pass


class Cell:
    def __init__(self, identifier=None, elder_sibling=None):
        self.identifier = identifier
        self.ion = None
        self.analytics = {}
        self.elder_sibling = elder_sibling
        self.analyser = CellAnalyser(self)

    def update_ion(self, new_ion):
        self.ion = new_ion

    def copy_price_from_sibling(self):
        pass

    def fresh_born(self, parent):
        try:
            self.elder_sibling = self.get_elder_sibling(parent)
        except:
            pass

    def validate_ion_data(self):
        if self.elder_sibling is not None:
            if not self.ion.price_is_valid():
                self.ion.price = self.elder_sibling.ion.price
            if not self.ion.volume_is_valid():
                self.ion.volume = self.elder_sibling.ion.volume
            if not self.ion.oi_is_valid():
                self.ion.oi = self.elder_sibling.ion.oi

    def get_elder_sibling(self, parent):
        all_keys = list(parent.trading_data.keys())
        prev_key = max([key for key in all_keys if key < self.identifier])
        return parent.trading_data[prev_key]

    def analyse(self):
        self.analyser.compute()


class CellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['volume'] = self.cell.elder_sibling.ion.volume


class Ion:
    def __init__(self, price, volume, oi):
        self.price = price
        self.volume = volume
        self.oi = oi

    def price_is_valid(self):
        return type(self.price) == int or type(self.price) == float

    def volume_is_valid(self):
        return type(self.volume) == int or type(self.volume) == float

    def oi_is_valid(self):
        return type(self.oi) == int or type(self.oi) == float

    @classmethod
    def from_raw(cls, ion_data):
        [price, volume, oi] = ion_data.split("|")
        return cls(float(price), int(volume), int(oi))

class Nucleus:
    def __init__(self):
        self.price_delta = None
        self.oi_delta = None
        self.volume = None

