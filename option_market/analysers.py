from collections import OrderedDict
from entities.trading_day import TradeDateTime
from config import oi_denomination
import numpy as np

class CellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['oi_delta_pct'] = np.round(self.cell.analytics['oi_delta']/self.cell.ion.oi - 1, 2)
            self.cell.analytics['volume'] = self.cell.ion.volume


class IntradayCrossAssetAnalyser:
    def __init__(self, capsule):
        self.capsule = capsule
        self.call_oi = OrderedDict()
        self.put_oi = OrderedDict()
        self.call_volume = OrderedDict()
        self.put_volume = OrderedDict()

    def compute(self, timestamp_list=[]):
        self.compute_oi_volume(timestamp_list)

    def compute_oi_volume(self, timestamp_list=[]):
        transposed_data = self.capsule.transposed_data
        #print('timestamp_list=====', timestamp_list)
        if not timestamp_list:
            timestamp_list = transposed_data.keys()
        #print(timestamp_list)
        for ts in timestamp_list:
            ts_data = transposed_data[ts]
            call_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
            call_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])

            self.call_oi[ts] = call_oi
            self.put_oi[ts] = put_oi
            self.call_volume[ts] = call_volume
            self.put_volume[ts] = put_volume
            """
            if self.call_oi[ts] == 0:
                print([cell.ion for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            """
            #print(self.call_oi[ts])

    def get_total_call_oi_series(self):
        return list(self.call_oi.values())

    def get_total_put_oi_series(self):
        return list(self.put_oi.values())

    def get_total_call_volume_series(self):
        return list(self.call_volume.values())

    def get_total_put_volume_series(self):
        return list(self.put_volume.values())

    def get_ts_series(self):
        return list(self.capsule.transposed_data.keys())

    def get_instrument_series(self, instrument='spot', field = None):
        #print(instrument)
        instrument_capsule = self.capsule.trading_data.get(instrument, None)
        series = []
        if instrument_capsule is not None:
            if field is not None:
                series = [cell.ion.get_field(field) for cell in list(instrument_capsule.trading_data.values())]

        return series

    def get_cross_instrument_stats(self, timestamp):
        transposed_data = self.capsule.transposed_data
        timestamp_list = transposed_data.keys()
        ts_data = transposed_data[timestamp]
        change_dct = {}
        for cell in ts_data.values():
            ts_oi = self.call_oi[timestamp]  if cell.instrument[-2::] == 'CE' else self.put_oi[timestamp]
            ts_volume = self.call_volume[timestamp] if cell.instrument[-2::] == 'CE' else self.put_volume[timestamp]
            volume_series = self.get_instrument_series(cell.instrument, 'volume')
            #print(volume_series)
            median_volume = volume_series[0]/100 #np.median(volume_series)
            change_dct[cell.instrument] = {
                'oi_dlt' : np.round(cell.analytics.get('oi_delta', None)/oi_denomination, 2),
                'oi_dlt_pct': cell.analytics.get('oi_delta_pct', None),
                'oi_share': np.round(float(cell.ion.oi/ts_oi), 4),
                'vol_share': np.round(float(cell.ion.volume / ts_volume), 4),
                'vol_scale': np.round(float(cell.ion.volume / median_volume), 2),
            }

        return change_dct


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

    def analyse(self):
        print('matrix analyse')
        """
        self.calculate_info()
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        print(day_capsule.trading_data)
        for instrument, capsule in day_capsule.trading_data.items():
            pass
        """