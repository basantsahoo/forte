from collections import OrderedDict
from entities.trading_day import TradeDateTime
from config import oi_denomination
import numpy as np
from option_market.technical.cross_over import OptionVolumeIndicator

class OptionCellAnalyser:
    def __init__(self, cell):
        self.cell = cell


    def compute(self):
        #print(self.cell.__dict__)
        #print(self.cell.ion.__dict__)

        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2) if self.cell.ion.past_closing_oi else 0
            #self.cell.analytics['volume_scale'] = self.cell.ion.volume/self.cell.ion.past_avg_volume
            self.cell.analytics['max_oi'] = max(self.cell.ion.oi, self.cell.elder_sibling.analytics['max_oi'])
            self.cell.analytics['cumulative_volume'] = self.cell.ion.volume + self.cell.elder_sibling.analytics['cumulative_volume']

            #print(self.cell.instrument, self.cell.analytics['cumulative_volume'])
            if self.cell.elder_sibling.analytics['cumulative_volume']:
                self.cell.analytics['vwap'] = (self.cell.ion.price * self.cell.ion.volume
                                               + self.cell.elder_sibling.analytics['vwap']
                                               * self.cell.elder_sibling.analytics['cumulative_volume'])/(self.cell.ion.volume + self.cell.elder_sibling.analytics['cumulative_volume'])
            else:
                self.cell.analytics['vwap'] = self.cell.ion.price
            self.cell.analytics['vwap_delta'] = self.cell.analytics['vwap'] - self.cell.elder_sibling.analytics['vwap']

        else:
            #print(self.cell.__dict__)
            #print(self.cell.ion.__dict__)
            self.cell.analytics['price_delta'] = 0
            self.cell.analytics['oi_delta'] = 0
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2) if self.cell.ion.past_closing_oi else 0
            #self.cell.analytics['volume_scale'] = self.cell.ion.volume/self.cell.ion.past_avg_volume
            self.cell.analytics['max_oi'] = self.cell.ion.oi
            self.cell.analytics['cumulative_volume'] = self.cell.ion.volume
            self.cell.analytics['vwap'] = self.cell.ion.price
            self.cell.analytics['vwap_delta'] = 0

    def update_analytics(self, field, value):
        self.cell.analytics[field] = value

class SpotCellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.close - self.cell.elder_sibling.ion.close
        else:
            self.cell.analytics['price_delta'] = 0

    def update_analytics(self, field, value):
        self.cell.analytics[field] = value

"""
class OptionMatrixAnalyser:

    def __init__(self, option_matrix=None):
        self.option_matrix = option_matrix
        self.call_oi_delta_grid = {}
        self.put_oi_delta_grid = {}
        self.call_volume_grid = {}
        self.put_volume_grid = {}

    def analyse(self):
        if self.option_matrix is not None:
            self.analyse()

    def calculate_info(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        ts_list = day_capsule.cross_analyser.get_ts_series()
        for idx in range(1, len(ts_list)):
            for instrument, instrument_capsule in day_capsule.trading_data.items():
                curr_cell = instrument_capsule.trading_data[ts_list[idx]]
                prev_cell = instrument_capsule.trading_data[ts_list[idx-1]]
                print(curr_cell)
"""
"""
    def analyse(self):
        print('matrix analyse')
"""
"""
        self.calculate_info()
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        print(day_capsule.trading_data)
        for instrument, capsule in day_capsule.trading_data.items():
            pass
"""