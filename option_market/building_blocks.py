from collections import OrderedDict
from option_market.analysers import CellAnalyser

class Capsule:
    def __init__(self):
        self.trading_data = OrderedDict()
        self.analytics = {}
        self.transposed_data = {}
        self.cross_analyser = None

    def in_trading_data(self, key):
        return key in list(self.trading_data.keys())

    def insert_trading_data(self, key, data):
        self.trading_data[key] = data

    def insert_analytics(self, key, data):
        self.analytics[key] = data

    def insert_transposed_data(self, key1, key2, data):
        if key1 not in self.transposed_data:
            self.transposed_data[key1] = {}
        self.transposed_data[key1][key2] = data

    def analyse(self):
        if self.cross_analyser is not None:
            self.cross_analyser.compute()



class Cell:
    def __init__(self, timestamp=None, instrument=None, elder_sibling=None):
        """
        :param timestamp:  required for instrument time series
        :param instrument: required for cross section of time stamp
        :param elder_sibling: required for updating values
        """
        self.timestamp = timestamp
        self.instrument = instrument
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
        prev_key = max([key for key in all_keys if key < self.timestamp])
        return parent.trading_data[prev_key]

    def analyse(self):
        self.analyser.compute()




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


