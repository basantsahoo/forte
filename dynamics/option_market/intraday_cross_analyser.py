from collections import OrderedDict
from entities.trading_day import TradeDateTime
from config import oi_denomination
import numpy as np
from dynamics.option_market.technical.cross_over import OptionVolumeIndicator
from helper.utils import create_strike_groups


class IntradayCrossAssetAnalyser:
    def __init__(self, option_capsule, spot_capsule, avg_volumes, closing_oi):
        self.option_capsule = option_capsule
        self.spot_capsule = spot_capsule
        self.call_oi = OrderedDict()
        self.put_oi = OrderedDict()
        self.call_volume = OrderedDict()
        self.put_volume = OrderedDict()
        self.avg_volumes = avg_volumes
        self.closing_oi = closing_oi
        self.aggregate_stats = {}
        self.aggregate_stats = {}
        #print(closing_oi.items())

    def compute(self, timestamp_list=[]):
        self.compute_stats(timestamp_list)

    def compute_stats(self, timestamp_list=[]):
        transposed_data = self.option_capsule.transposed_data
        #print('timestamp_list=====', timestamp_list)
        if not timestamp_list:
            timestamp_list = transposed_data.keys()
        #print(timestamp_list)
        for ts in timestamp_list:
            t_time = TradeDateTime(ts)
            #print('compute_stats time ==========================================================================', t_time.date_time_string)

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
            median_total_volume_series = np.median(total_volume_series)

            prev_call_median_volume = sum([value for key, value in self.avg_volumes.items() if key[-2::] == 'CE'])
            prev_put_median_volume = sum([value for key, value in self.avg_volumes.items() if key[-2::] == 'PE'])
            prev_median_total_volume = prev_call_median_volume + prev_put_median_volume
            day_normalization_factor = 1 #if len(total_volume_series) < 30 else (np.median(total_volume_series) / prev_median_total_volume)

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
            """
            print('prev_median_total_volume =====', prev_median_total_volume)
            print('call_volume =====', call_volume_series[-1])
            print('put_volume =====', put_volume_series[-1])
            print('total_volume_series =====', total_volume_series[-1])
            print('call_volume_scale =====', call_volume_scale)
            print('put_volume_scale =====', put_volume_scale)
            print('total_volume_scale =====', total_volume_scale)
            """
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
            self.aggregate_stats[ts]['sum_call_volume'] = call_volume_series[-1]
            self.aggregate_stats[ts]['sum_put_volume'] = put_volume_series[-1]
            self.aggregate_stats[ts]['median_call_volume'] = np.median(call_volume_series)
            self.aggregate_stats[ts]['median_put_volume'] = np.median(put_volume_series)
            self.aggregate_stats[ts]['pcr_minus_1'] = np.round(poi_put_oi / poi_call_oi - 1, 2)
            self.aggregate_stats[ts]['call_volume_scale_day'] = OptionVolumeIndicator.calc_scale(call_volume_series, np.median(call_volume_series),
                                                          day_normalization_factor)
            self.aggregate_stats[ts]['put_volume_scale_day'] = OptionVolumeIndicator.calc_scale(put_volume_series, np.median(put_volume_series),
                                                          day_normalization_factor)
            self.aggregate_stats[ts]['call_volume_scale_day_2'] = OptionVolumeIndicator.calc_scale(call_volume_series, median_total_volume_series * 0.5, 1)
            self.aggregate_stats[ts]['put_volume_scale_day_2'] = OptionVolumeIndicator.calc_scale(put_volume_series, median_total_volume_series * 0.5, 1)


            ### Calculate Regime
            spot_ltp = self.get_spot_ltp(ts)
            all_instruments = self.get_all_option_instruments()
            put_groups = create_strike_groups(spot_ltp, 'PE', all_instruments)
            call_groups = create_strike_groups(spot_ltp, 'CE', all_instruments)
            near_put_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument in put_groups['near_instruments']])
            far_put_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument in put_groups['far_instruments']])
            near_call_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument in call_groups['near_instruments']])
            far_call_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument in call_groups['far_instruments']])

            near_put_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument in put_groups['near_instruments']])
            far_put_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument in put_groups['far_instruments']])
            near_call_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument in call_groups['near_instruments']])
            far_call_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument in call_groups['far_instruments']])

            self.aggregate_stats[ts]['near_put_oi_share'] = np.round(near_put_oi / total_oi_series[-1], 4)
            self.aggregate_stats[ts]['far_put_oi_share'] = np.round(far_put_oi / total_oi_series[-1], 4)
            self.aggregate_stats[ts]['near_call_oi_share'] = np.round(near_call_oi / total_oi_series[-1], 4)
            self.aggregate_stats[ts]['far_call_oi_share'] = np.round(far_call_oi / total_oi_series[-1], 4)

            self.aggregate_stats[ts]['put_oi_spread'] = self.aggregate_stats[ts]['near_put_oi_share'] - self.aggregate_stats[ts]['far_put_oi_share']
            self.aggregate_stats[ts]['call_oi_spread'] = self.aggregate_stats[ts]['near_call_oi_share'] - self.aggregate_stats[ts]['far_call_oi_share']

            self.aggregate_stats[ts]['near_put_volume_share'] = np.round(near_put_volume / total_volume_series[-1], 4)
            self.aggregate_stats[ts]['far_put_volume_share'] = np.round(far_put_volume / total_volume_series[-1], 4)
            self.aggregate_stats[ts]['near_call_volume_share'] = np.round(near_call_volume / total_volume_series[-1], 4)
            self.aggregate_stats[ts]['far_call_volume_share'] = np.round(far_call_volume / total_volume_series[-1], 4)
            """
            print('near_call_volume =====', near_call_volume)
            print('near_call_volume_share=====', self.aggregate_stats[ts]['near_call_volume_share'], self.aggregate_stats[ts]['near_call_volume_share']/self.aggregate_stats[ts]['near_call_oi_share'])
            print('near_put_volume =====', near_put_volume)
            print('far_call_volume_share=====', self.aggregate_stats[ts]['far_call_volume_share'], self.aggregate_stats[ts]['far_call_volume_share']/self.aggregate_stats[ts]['far_call_oi_share'])
            """
            self.aggregate_stats[ts]['near_put_volume_share_per_oi'] = np.round(near_put_volume / total_volume_series[-1], 4) / self.aggregate_stats[ts]['near_put_oi_share']
            self.aggregate_stats[ts]['far_put_volume_share_per_oi'] = np.round(far_put_volume / total_volume_series[-1], 4) / self.aggregate_stats[ts]['far_put_oi_share']
            self.aggregate_stats[ts]['near_call_volume_share_per_oi'] = np.round(near_call_volume / total_volume_series[-1], 4) / self.aggregate_stats[ts]['near_call_oi_share']
            self.aggregate_stats[ts]['far_call_volume_share_per_oi'] = np.round(far_call_volume / total_volume_series[-1], 4) / self.aggregate_stats[ts]['far_call_oi_share']
            """
            print(self.aggregate_stats[ts]['near_call_volume_share_per_oi'], self.aggregate_stats[ts]['near_put_volume_share_per_oi'])
            print(self.aggregate_stats[ts]['far_call_volume_share_per_oi'], self.aggregate_stats[ts]['far_put_volume_share_per_oi'])
            print('spread====', self.aggregate_stats[ts]['near_call_volume_share_per_oi'] - self.aggregate_stats[ts]['far_call_volume_share_per_oi'])
            """
            self.aggregate_stats[ts]['call_vol_spread'] = np.round(self.aggregate_stats[ts]['near_call_volume_share_per_oi'] - self.aggregate_stats[ts]['far_call_volume_share_per_oi'], 2)
            self.aggregate_stats[ts]['put_vol_spread'] = np.round(self.aggregate_stats[ts]['near_put_volume_share_per_oi'] - self.aggregate_stats[ts]['far_put_volume_share_per_oi'], 2)
            both_near_oi_share = (self.aggregate_stats[ts]['near_put_oi_share'] + self.aggregate_stats[ts]['near_call_oi_share'])
            both_far_oi_share = (self.aggregate_stats[ts]['far_put_oi_share'] + self.aggregate_stats[ts]['far_call_oi_share'])
            both_near_volume_share = (near_call_volume + near_put_volume)/total_volume_series[-1]
            both_far_volume_share = (far_call_volume + far_put_volume) / total_volume_series[-1]
            """
            print("====debug========")
            print("call volume===", near_call_volume/total_volume_series[-1], far_call_volume/total_volume_series[-1])
            print("call oi===", self.aggregate_stats[ts]['near_call_oi_share'],
                  self.aggregate_stats[ts]['far_call_oi_share'])
            print("put volume===", near_put_volume/total_volume_series[-1],
                  far_put_volume/total_volume_series[-1])

            print("put oi===", self.aggregate_stats[ts]['near_put_oi_share'],
                  self.aggregate_stats[ts]['far_put_oi_share'])
            """
            self.aggregate_stats[ts]['total_vol_spread'] = np.round(both_near_volume_share/both_near_oi_share - both_far_volume_share/both_far_oi_share, 2)
            self.aggregate_stats[ts]['near_vol_pcr'] = np.round(self.aggregate_stats[ts]['near_put_volume_share']/self.aggregate_stats[ts]['near_call_volume_share'], 2)
            self.aggregate_stats[ts]['far_vol_pcr'] = np.round(self.aggregate_stats[ts]['far_put_volume_share'] / self.aggregate_stats[ts]['far_call_volume_share'], 2)
            self.aggregate_stats[ts]['vol_spread_pcr'] = np.round((self.aggregate_stats[ts]['near_put_volume_share'] - self.aggregate_stats[ts]['far_put_volume_share']) / (self.aggregate_stats[ts]['near_call_volume_share'] - self.aggregate_stats[ts]['far_call_volume_share']), 2)

            """
            print("----------oi----------")
            print(self.aggregate_stats[ts]['near_call_oi_share'], self.aggregate_stats[ts]['near_put_oi_share'])
            print(self.aggregate_stats[ts]['far_call_oi_share'], self.aggregate_stats[ts]['far_put_oi_share'])
            """
            n_period_stats = self.get_n_period_stats(ts)
            self.aggregate_stats[ts]['regime'] = n_period_stats['regime']
            self.aggregate_stats[ts]['market_entrant'] = n_period_stats['market_entrant']
            self.aggregate_stats[ts]['call_entrant'] = n_period_stats['call_entrant']
            self.aggregate_stats[ts]['put_entrant'] = n_period_stats['put_entrant']
            self.aggregate_stats[ts]['transition'] = n_period_stats['transition']
            self.aggregate_stats[ts]['roll_near_vol_pcr'] = n_period_stats['roll_near_vol_pcr']
            self.aggregate_stats[ts]['roll_far_vol_pcr'] = n_period_stats['roll_far_vol_pcr']
            self.aggregate_stats[ts]['roll_vol_spread_pcr'] = n_period_stats['roll_vol_spread_pcr']
            ledger_stats = self.get_ledger_stats(ts)
            self.aggregate_stats[ts]['ledger'] = ledger_stats
            """
            self.aggregate_stats[ts]['ledger']['total_pnl'] = ledger_stats['total_pnl']
            self.aggregate_stats[ts]['ledger']['call_pnl'] = ledger_stats['call_pnl']
            self.aggregate_stats[ts]['ledger']['put_pnl'] = ledger_stats['put_pnl']
            self.aggregate_stats[ts]['ledger']['max_total_investment'] = ledger_stats['max_total_investment']
            self.aggregate_stats[ts]['ledger']['max_call_investment'] = ledger_stats['max_call_investment']
            self.aggregate_stats[ts]['ledger']['max_put_investment'] = ledger_stats['max_put_investment']
            self.aggregate_stats[ts]['ledger']['total_profit'] = ledger_stats['total_profit']
            """

            ## Addition
            ## calculate n period open interest change
            self.calc_cross_instrument_stats(ts)
            self.roundify(ts)

    def roundify(self, ts):
        for key, val in self.aggregate_stats[ts].items():
            try:
                self.aggregate_stats[ts][key] = np.round(val, 3)
            except:
                pass

    def get_n_period_stats(self, ts, n_period=3):
        all_ts = list(self.aggregate_stats.keys())
        filtered_ts = [x for x in all_ts if x<= ts]
        filtered_ts.sort()
        n_period_ts = filtered_ts[-n_period:]
        n_period_aggr_stats = [self.aggregate_stats[ts] for ts in n_period_ts]
        n_period_call_oi_change = sum([period_aggr_stats['call_addition'] for period_aggr_stats in n_period_aggr_stats])
        n_period_put_oi_change = sum([period_aggr_stats['put_addition'] for period_aggr_stats in n_period_aggr_stats])
        n_period_total_oi_change = sum([period_aggr_stats['total_addition'] for period_aggr_stats in n_period_aggr_stats])

        build_up_theshold = 0.1/100

        call_build_up_dir = int(abs(n_period_call_oi_change) > build_up_theshold) * np.sign(n_period_call_oi_change)
        put_build_up_dir = int(abs(n_period_put_oi_change) > build_up_theshold) * np.sign(n_period_put_oi_change)
        if call_build_up_dir > 0 and put_build_up_dir > 0:
            regime = "both_build_up"
        elif call_build_up_dir > 0 and put_build_up_dir == 0:
            regime = "call_buildup"
        elif call_build_up_dir == 0 and put_build_up_dir > 0:
            regime = "put_buildup"
        elif call_build_up_dir == 0 and put_build_up_dir == 0:
            regime = "neutral"
        elif call_build_up_dir == 0 and put_build_up_dir < 0:
            regime = "put_covering"
        elif call_build_up_dir < 0 and put_build_up_dir == 0:
            regime = "call_covering"
        elif call_build_up_dir < 0 and put_build_up_dir < 0:
            regime = "both_covering"
        elif (call_build_up_dir < 0) and put_build_up_dir > 0:
            regime = "call_to_put_trans"
        elif (call_build_up_dir > 0) and put_build_up_dir < 0:
            regime = "put_to_call_trans"
        #print(call_build_up_dir, put_build_up_dir)
        stats= {}
        stats['regime'] = regime
        stats['market_entrant'] = n_period_total_oi_change
        stats['call_entrant'] = n_period_call_oi_change
        stats['put_entrant'] = n_period_put_oi_change
        stats['transition'] = (n_period_put_oi_change - n_period_call_oi_change) if  n_period_put_oi_change > n_period_total_oi_change else 0
        stats['roll_near_vol_pcr'] = np.round(np.mean([period_aggr_stats['near_vol_pcr'] for period_aggr_stats in n_period_aggr_stats]), 2)
        stats['roll_far_vol_pcr'] = np.round(np.mean([period_aggr_stats['far_vol_pcr'] for period_aggr_stats in n_period_aggr_stats]), 2)
        stats['roll_vol_spread_pcr'] = np.round(np.mean([period_aggr_stats['vol_spread_pcr'] for period_aggr_stats in n_period_aggr_stats]), 2)
        return stats

    def get_ledger_stats(self, ts):

        transposed_data = self.option_capsule.transposed_data
        ts_data = transposed_data[ts]
        call_pnl = sum([cell.ledger['total_pnl'] for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
        put_pnl = sum([cell.ledger['total_pnl'] for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
        total_pnl = call_pnl + put_pnl
        call_cum_investment = sum([cell.ledger['cum_investment'] for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
        put_cum_investment = sum([cell.ledger['cum_investment'] for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
        total_cum_investment = call_cum_investment + put_cum_investment

        stats= {}
        stats['total_pnl'] = total_pnl
        stats['call_pnl'] = call_pnl
        stats['put_pnl'] = put_pnl
        stats['total_cum_investment'] = total_cum_investment
        stats['call_cum_investment'] = call_cum_investment
        stats['put_cum_investment'] = put_cum_investment

        ts_history = [x for x in list(self.aggregate_stats.keys()) if x < ts]
        if ts_history:
            previous_ts = max(ts_history)
            previous_ledger = self.aggregate_stats[previous_ts]['ledger']
            stats['max_total_investment'] = max(total_cum_investment, previous_ledger['max_total_investment'])
            stats['max_call_investment'] = max(call_cum_investment, previous_ledger['max_call_investment'])
            stats['max_put_investment'] = max(put_cum_investment, previous_ledger['max_put_investment'])
        else:
            stats['max_total_investment'] = total_cum_investment
            stats['max_call_investment'] = call_cum_investment
            stats['max_put_investment'] = put_cum_investment

        stats['total_profit'] = np.round(total_pnl/stats['max_total_investment'],2)
        stats['call_profit'] = np.round(call_pnl / stats['max_call_investment'], 2)
        stats['put_profit'] = np.round(put_pnl / stats['max_put_investment'], 2)
        ######## Daily PNL ###########
        day_call_pnl = sum([cell.day_ledger['total_pnl'] for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
        day_put_pnl = sum([cell.day_ledger['total_pnl'] for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])

        day_total_pnl = day_call_pnl + day_put_pnl
        day_call_cum_investment = sum([cell.day_ledger['cum_investment'] for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
        day_put_cum_investment = sum([cell.day_ledger['cum_investment'] for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
        day_total_cum_investment = day_call_cum_investment + day_put_cum_investment

        if ts_history and TradeDateTime(max(ts_history)).date_string == TradeDateTime(ts).date_string:
            previous_ts = max(ts_history)
            previous_ledger = self.aggregate_stats[previous_ts]['ledger']
            stats['day_max_total_investment'] = max(day_total_cum_investment, previous_ledger['day_max_total_investment'])
            stats['day_max_call_investment'] = max(day_call_cum_investment, previous_ledger['day_max_call_investment'])
            stats['day_max_put_investment'] = max(day_put_cum_investment, previous_ledger['day_max_put_investment'])
        else:
            stats['day_max_total_investment'] = day_total_cum_investment
            stats['day_max_call_investment'] = day_call_cum_investment
            stats['day_max_put_investment'] = day_put_cum_investment

        stats['day_total_profit'] = np.round(day_total_pnl/stats['day_max_total_investment'],2)
        stats['day_call_profit'] = np.round(day_call_pnl / stats['day_max_call_investment'], 2)
        stats['day_put_profit'] = np.round(day_put_pnl / stats['day_max_put_investment'], 2)

        """
        print("put_pnl=====", put_pnl)
        print("max_put_investment=====", stats['max_put_investment'])
        print("put_profit=====", stats['put_profit'])
        print("call_pnl=====", call_pnl)
        print("max_call_investment=====", stats['max_call_investment'])
        print("call_profit=====", stats['call_profit'])
        """
        return stats



    def calc_cross_instrument_stats(self, timestamp):
        transposed_data = self.option_capsule.transposed_data
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
                'oi_drop': np.round(cell.ion.oi / cell.analytics['max_oi'] - 1, 2) if cell.analytics['max_oi'] else 0,
                'oi_share': cell.analytics.get('oi_share', None), #np.round(float(cell.ion.oi/ts_oi), 4),
                'oi_share_chg': cell.analytics.get('oi_share', 0) - cell.elder_sibling.analytics.get('oi_share', 0) if cell.elder_sibling else 0,
                'oi_build_up_factor': np.round((cell.ion.oi - cell.ion.past_closing_oi)/start_total_oi, 4),
                'vol_share': cell.analytics.get('vol_share', None),
                'vol_share_change': cell.analytics['vol_share_change'],
                'vol_share_flow': np.round(sum(vol_share_change_series[-3::]), 4),
                # 'vol_scale': np.round(float(cell.ion.volume / median_volume), 2),
                #'price_delta': np.round(cell.analytics.get('price_delta', 0), 2),
                'vwap_delta': np.round(cell.analytics['vwap_delta'], 2),
                'price_delta': np.round(cell.analytics['price_delta'], 2),
            }

        self.option_capsule.analytics[timestamp] = change_dct

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
        return list(self.option_capsule.transposed_data.keys())

    def get_instrument_ion_field_series(self, instrument='spot', field = None):
        #print(instrument)
        series = []
        if instrument == 'spot':
            instrument_capsule = self.spot_capsule.trading_data.get(instrument, None)
        else:
            instrument_capsule = self.option_capsule.trading_data.get(instrument, None)

        if instrument_capsule is not None:
            series = [cell.ion.get_field(field) for cell in list(instrument_capsule.trading_data.values())]

        return series

    def get_instrument_stats_series(self, instrument, field):
        instrument_capsule = self.option_capsule.trading_data.get(instrument, None)
        series = []
        if instrument_capsule is not None:
            series = [cell.analytics[field] for cell in list(instrument_capsule.trading_data.values())]

        return series

    def get_all_option_instruments(self):
        instruments = [{'instrument': inst, 'strike': int(inst[:-3]), 'kind': inst[-2::]} for inst in self.option_capsule.trading_data.keys()]
        return instruments

    def get_spot_ltp(self, ts):
        try:
            spot_ltp = self.spot_capsule.trading_data['spot'].trading_data[ts].ion.close
        except:
            spot_close_series = self.get_instrument_ion_field_series('spot', 'close')
            spot_ltp = spot_close_series[-1]
        return spot_ltp

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
        return self.option_capsule.analytics[timestamp]

    def get_aggregate_stats(self, timestamp):
        return self.aggregate_stats[timestamp]

