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
    def __init__(self, timestamp=None, instrument=None, elder_sibling=None, volume_delta_mode=False):
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
        self.volume_delta_mode = volume_delta_mode

    def update_ion(self, new_ion):
        self.ion = new_ion
        """
        if self.timestamp == 1703131200 and self.instrument=='48600_CE':
            print(self.ion.oi)
        """
    def copy_price_from_sibling(self):
        pass

    def fresh_born(self, parent):
        try:
            self.elder_sibling = self.get_elder_sibling(parent)
        except:
            pass

    def validate_ion_data(self):
        if self.elder_sibling is not None:
            if self.ion.category == 'option':
                if not self.ion.price_is_valid():
                    self.ion.price = self.elder_sibling.ion.price
                if not self.ion.volume_is_valid():
                    self.ion.volume = self.elder_sibling.ion.volume
                    self.ion.ref_volume = self.elder_sibling.ion.ref_volume
                if not self.ion.oi_is_valid():
                    self.ion.oi = self.elder_sibling.ion.oi
                if self.volume_delta_mode:
                    self.ion.volume = self.ion.ref_volume - self.elder_sibling.ion.ref_volume
            elif self.ion.category == 'spot':
                if not self.ion.price_is_valid():
                    self.ion.open = self.elder_sibling.ion.open
                    self.ion.high = self.elder_sibling.ion.high
                    self.ion.low = self.elder_sibling.ion.low
                    self.ion.close = self.elder_sibling.ion.close


    def get_elder_sibling(self, parent):
        all_keys = list(parent.trading_data.keys())
        prev_key = max([key for key in all_keys if key < self.timestamp])
        return parent.trading_data[prev_key]

    def analyse(self):
        self.analyser.compute()




class OptionIon:
    def __init__(self, price, volume, oi):
        self.category = 'option'
        self.price = price
        self.volume = volume
        self.oi = oi
        self.ref_volume = volume

    def price_is_valid(self):
        return type(self.price) == int or type(self.price) == float

    def volume_is_valid(self):
        return type(self.volume) == int or type(self.volume) == float

    def oi_is_valid(self):
        return type(self.oi) == int or type(self.oi) == float

    def default_field(self):
        return self.volume

    @classmethod
    def from_raw(cls, ion_data):
        [price, volume, oi] = ion_data.split("|")
        return cls(float(price), int(volume), int(oi))


class SpotIon:
    def __init__(self, open, high, low, close):
        self.category = 'spot'
        self.open = open
        self.high = high
        self.low = low
        self.close = close

    def price_is_valid(self):
        return (self.open > 0) and (self.high > 0) and (self.low > 0) and (self.close > 0)

    def volume_is_valid(self):
        return True

    def oi_is_valid(self):
        return True

    def default_field(self):
        return self.close

    @classmethod
    def from_raw(cls, ion_data):
        [open, high, low, close] = ion_data.split("|")
        return cls(float(open), float(high), float(low), float(close))

