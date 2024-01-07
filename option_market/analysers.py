from collections import OrderedDict
from entities.trading_day import TradeDateTime
from config import oi_denomination
import numpy as np
from option_market.technical.cross_over import OptionVolumeIndicator

class OptionCellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute_o(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['oi_delta_pct'] = np.round(self.cell.analytics['oi_delta']/self.cell.ion.oi, 2)
            self.cell.analytics['volume'] = self.cell.ion.volume


    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2)
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
            self.cell.analytics['price_delta'] = 0
            self.cell.analytics['oi_delta'] = 0
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2)
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

class IntradayCrossAssetAnalyser:
    def __init__(self, capsule, avg_volumes, closing_oi):
        self.capsule = capsule
        self.call_oi = OrderedDict()
        self.put_oi = OrderedDict()
        self.call_volume = OrderedDict()
        self.put_volume = OrderedDict()
        self.avg_volumes = avg_volumes
        self.closing_oi = closing_oi
        self.aggregate_stats = {}
        #print(closing_oi.items())

    def compute(self, timestamp_list=[]):
        self.compute_stats(timestamp_list)

    def compute_stats(self, timestamp_list=[]):
        transposed_data = self.capsule.transposed_data
        #print('timestamp_list=====', timestamp_list)
        if not timestamp_list:
            timestamp_list = transposed_data.keys()
        #print(timestamp_list)
        for ts in timestamp_list:
            t_time = TradeDateTime(ts)
            print('time ==========================================================================',
                  t_time.date_time.hour, ":", t_time.date_time.minute)

            self.aggregate_stats[ts] = {}
            ts_data = transposed_data[ts]
            call_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
            call_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])

            self.call_oi[ts] = call_oi
            self.put_oi[ts] = put_oi
            self.call_volume[ts] = call_volume
            self.put_volume[ts] = put_volume


            call_oi_series = self.get_total_call_oi_series()
            put_oi_series = self.get_total_put_oi_series()
            total_oi_series = [x + y for x, y in zip(call_oi_series, put_oi_series)]
            call_volume_series = self.get_total_call_volume_series()
            put_volume_series = self.get_total_put_volume_series()
            total_volume_series = [x + y for x, y in zip(call_volume_series, put_volume_series)]

            prev_call_median_volume = sum([value for key, value in self.avg_volumes.items() if key[-2::] == 'CE'])
            prev_put_median_volume = sum([value for key, value in self.avg_volumes.items() if key[-2::] == 'PE'])
            prev_median_total_volume = prev_call_median_volume + prev_put_median_volume
            day_normalization_factor = 1 if len(total_volume_series) < 30 else (np.median(total_volume_series) / prev_median_total_volume)

            start_call_oi = self.get_total_call_closing_oi()
            start_put_oi = self.get_total_put_closing_oi()
            start_total_oi = start_call_oi + start_put_oi

            max_total_oi = max(total_oi_series)
            poi_total_oi = total_oi_series[-1]
            poi_call_oi = call_oi_series[-1]
            poi_put_oi = put_oi_series[-1]
            t_2_call_oi = call_oi_series[-2] if len(call_oi_series) > 2 else start_call_oi
            t_2_put_oi = put_oi_series[-2] if len(put_oi_series) > 2 else start_put_oi
            t_2_total_oi = total_oi_series[-2] if len(total_oi_series) > 2 else start_total_oi
            #print('prev_median_total_volume', prev_median_total_volume)
            call_volume_scale = OptionVolumeIndicator.calc_scale(call_volume_series, prev_median_total_volume * 0.5,
                                                          day_normalization_factor)
            put_volume_scale = OptionVolumeIndicator.calc_scale(put_volume_series, prev_median_total_volume * 0.5,
                                                             day_normalization_factor)
            total_volume_scale = OptionVolumeIndicator.calc_scale(total_volume_series, prev_median_total_volume,
                                             day_normalization_factor)

            self.aggregate_stats[ts]['max_call_oi'] = np.round(max(call_oi_series) / oi_denomination, 2)
            self.aggregate_stats[ts]['max_put_oi'] = np.round(max(put_oi_series) / oi_denomination, 2)
            self.aggregate_stats[ts]['max_total_oi'] = np.round(max_total_oi / oi_denomination, 2)
            self.aggregate_stats[ts]['poi_call_oi'] = np.round(poi_call_oi / oi_denomination, 2)
            self.aggregate_stats[ts]['poi_put_oi'] = np.round(poi_put_oi / oi_denomination, 2)
            self.aggregate_stats[ts]['poi_total_oi'] = np.round(poi_total_oi / oi_denomination, 2)
            self.aggregate_stats[ts]['call_drop'] = np.round(poi_call_oi * 1.00 / max(call_oi_series) - 1, 2)
            self.aggregate_stats[ts]['put_drop'] = np.round(poi_put_oi * 1.00 / max(put_oi_series) - 1, 2)
            self.aggregate_stats[ts]['total_drop'] = np.round(poi_total_oi * 1.00 / max_total_oi - 1, 2)
            self.aggregate_stats[ts]['call_build_up'] = np.round((call_oi_series[-1] - start_call_oi) / start_total_oi, 2)
            self.aggregate_stats[ts]['put_build_up'] = np.round((put_oi_series[-1] - start_put_oi) / start_total_oi, 2)
            self.aggregate_stats[ts]['total_build_up'] = np.round(total_oi_series[-1] / start_total_oi - 1, 2)
            self.aggregate_stats[ts]['call_addition'] = np.round((call_oi_series[-1] - t_2_call_oi) / start_total_oi, 4)
            self.aggregate_stats[ts]['put_addition'] = np.round((put_oi_series[-1] - t_2_put_oi) / start_total_oi, 4)
            self.aggregate_stats[ts]['total_addition'] = np.round((total_oi_series[-1] - t_2_total_oi) / start_total_oi, 4)
            self.aggregate_stats[ts]['call_volume_scale'] = call_volume_scale
            self.aggregate_stats[ts]['put_volume_scale'] = put_volume_scale
            self.aggregate_stats[ts]['total_volume_scale'] = total_volume_scale
            self.aggregate_stats[ts]['pcr_minus_1'] = np.round(poi_put_oi / poi_call_oi - 1, 2)

            self.calc_cross_instrument_stats(ts)

    def calc_cross_instrument_stats(self, timestamp):
        transposed_data = self.capsule.transposed_data
        timestamp_list = transposed_data.keys()
        ts_data = transposed_data[timestamp]
        change_dct = {}
        start_call_oi = self.get_total_call_closing_oi()
        start_put_oi = self.get_total_put_closing_oi()
        start_total_oi = start_call_oi + start_put_oi
        for cell in ts_data.values():
            ts_oi = self.call_oi[timestamp]  if cell.instrument[-2::] == 'CE' else self.put_oi[timestamp]
            ts_volume = self.call_volume[timestamp] if cell.instrument[-2::] == 'CE' else self.put_volume[timestamp]
            #median_volume = self.get_median_volume(cell.instrument)
            cell.analyser.update_analytics('oi_share', np.round(float(cell.ion.oi/ts_oi), 4))
            cell.analyser.update_analytics('vol_share', np.round(float(cell.ion.volume / ts_volume), 4))
            vol_share_change = cell.analytics.get('vol_share', 0) - cell.elder_sibling.analytics.get('vol_share', 0) if cell.elder_sibling else 0
            cell.analyser.update_analytics('vol_share_change', vol_share_change)
            vol_share_change_series = self.get_instrument_stats_series(cell.instrument, 'vol_share_change')
            change_dct[cell.instrument] = {
                'oi_dlt': np.round(cell.analytics['oi_delta']/oi_denomination, 4),
                'day_oi_delta_pct': cell.analytics.get('day_oi_delta_pct', None),
                'oi_drop': np.round(cell.ion.oi / cell.analytics['max_oi'] - 1, 2),
                'oi_share': cell.analytics.get('oi_share', None), #np.round(float(cell.ion.oi/ts_oi), 4),
                'oi_share_chg': cell.analytics.get('oi_share', 0) - cell.elder_sibling.analytics.get('oi_share', 0) if cell.elder_sibling else 0,
                'oi_build_up_factor': np.round((cell.ion.oi - cell.ion.past_closing_oi)/start_total_oi, 4),
                'vol_share': cell.analytics.get('vol_share', None),
                'vol_share_change': cell.analytics['vol_share_change'],
                'vol_share_flow': np.round(sum(vol_share_change_series[-10::]), 4),
                # 'vol_scale': np.round(float(cell.ion.volume / median_volume), 2),
                #'price_delta': np.round(cell.analytics.get('price_delta', 0), 2),
                'vwap_delta': np.round(cell.analytics['vwap_delta'], 2),
                'price_delta': np.round(cell.analytics['price_delta'], 2),
            }

        self.capsule.analytics[timestamp] = change_dct

    def get_total_call_closing_oi(self):
        return sum([oi for inst, oi in self.closing_oi.items() if inst[-2::] == 'CE'])

    def get_total_put_closing_oi(self):
        return sum([oi for inst, oi in self.closing_oi.items() if inst[-2::] == 'PE'])

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

    def get_instrument_ion_field_series(self, instrument='spot', field = None):
        #print(instrument)
        instrument_capsule = self.capsule.trading_data.get(instrument, None)
        series = []
        if instrument_capsule is not None:
            series = [cell.ion.get_field(field) for cell in list(instrument_capsule.trading_data.values())]

        return series

    def get_instrument_stats_series(self, instrument, field):
        instrument_capsule = self.capsule.trading_data.get(instrument, None)
        series = []
        if instrument_capsule is not None:
            series = [cell.analytics[field] for cell in list(instrument_capsule.trading_data.values())]

        return series
    """
    def get_median_volume(self, inst):
        volume_series = self.get_instrument_ion_field_series(inst, 'volume')
        if len(volume_series) < 30:
            median_volume = self.avg_volumes[inst]
        else:
            median_volume = np.median(volume_series)
        return median_volume
    """
    def get_cross_instrument_stats(self, timestamp):
        return self.capsule.analytics[timestamp]

    def get_aggregate_stats(self, timestamp):
        return self.aggregate_stats[timestamp]
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