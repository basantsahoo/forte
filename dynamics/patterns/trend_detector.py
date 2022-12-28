import numpy as np
from statistics import mean
import math
from helper.utils import get_overlap
from dynamics.patterns.price_action_pattern_detector import PriceActionPatternDetector
from dynamics.patterns.technical_patterns import pattern_config, inflex_config

class TrendDetector(PriceActionPatternDetector):
    def __init__(self, insight_book, period):
        PriceActionPatternDetector.__init__(self,insight_book, period)
        self.insight_book = insight_book
        self.last_match = None
        self.period = period
        self.enabled_patterns = ['TREND']


    def check_pattern(self, df2, pattern):
        if pattern == "TREND":
            return self.check_trend(df2)
        else:
            return []

    def get_trend_begin_point(self, df2, idx):
        trend_begin_point = [None, None]
        prev_infl_df = df2[(df2.index < idx) & (df2.SPExt != '')]
        itr2 = list(prev_infl_df.index)
        itr2.reverse()  # search from last point
        idx_to_check = []
        ref_point = df2.Close[idx]
        for i in itr2:
            # print('iteration', i)
            # break if there is a point above ref point
            if (prev_infl_df.Close[i] - ref_point) >= 0:
                break
            else:
                idx_to_check.append(i)  # possible point 2
                if prev_infl_df.SPExt[i] == df2.SPExt[idx]:
                    ref_point = prev_infl_df.Close[i]
        if len(idx_to_check) > 0:
            trend_begin_price = min(prev_infl_df.Close[idx_to_check])
            trend_df = prev_infl_df[prev_infl_df.index.isin(idx_to_check)]
            trend_begin_idx = trend_df[trend_df['Close'] == trend_begin_price].index[-1]
            trend_begin_point = [trend_begin_idx, trend_begin_price]
        return trend_begin_point

    """
    1. 
    
    """
    def get_infl_count_between_infl(self, df2, start_index, end_index, column, threshold, infl=[], cat="HIGHER"):
        if cat == "HIGHER":
            tmp_df_infl = df2[(df2.index > start_index) & (df2.index < end_index) & (df2[column].isin(infl)) & (df2.Close > threshold)]
        else:
            tmp_df_infl = df2[(df2.index > start_index) & (df2.index < end_index) & (df2[column].isin(infl)) & (df2.Close < threshold)]
        count = tmp_df_infl.shape[0]
        return count

    def check_trend(self, df2, infl_label='SPExt'): #infl_label='FourthExt'
        #print('check_trend=======================================================')
        #print(df2)
        ret_val = {'trend': {}, 'last_wave': {}, 'all_waves' : []}
        all_sp_infl = np.array(df2.index[df2[infl_label] != ''])
        if len(all_sp_infl) > 1:
            #print(all_sp_infl)
            inflex_times = df2.iloc[all_sp_infl, :]['Time'].tolist()
            inflex_prices = df2.iloc[all_sp_infl,:]['Close'].tolist()
            inflex_types = df2.iloc[all_sp_infl, :][infl_label].tolist()
            if len(inflex_prices) > 0:
                momentum_block = (inflex_config['NIFTY']['fpth'] * inflex_prices[0]) // 5 * 5
            else:
                momentum_block = 20
            #print(momentum_block)
            #print(inflex_price)
            #print(inflex_type)
            #deltas = [(round(x - inflex_prices[i - 1], 0), round(x*1.00/inflex_prices[i - 1]-1,4)) if i else (0,1) for i, x in enumerate(inflex_prices)][1:]
            #print(df2)
            #print(inflex_prices)
            deltas = [x - inflex_prices[i - 1] if i > 0 else 0 for i, x in enumerate(inflex_prices)]
            ratios = [round(abs(x/deltas[i - 1]), 3) if (i > 1 and deltas[i - 1] > 0) else 0 for i, x in enumerate(deltas)]
            start_prices = [inflex_prices[i - 1] if i else inflex_prices[i] for i, x in enumerate(inflex_prices)]
            #comb = list(zip(all_sp_infl, inflex_types, inflex_prices, deltas, ratios))
            comb = [
                {'index': idx, 'wave_end_time':wave_end_time, 'type': inf_type, 'start': start_price, 'end': inf_price, 'dist': delta, 'ratio': ratio}
                for idx, wave_end_time,  inf_type,start_price, inf_price, delta, ratio in zip(all_sp_infl, inflex_times, inflex_types, start_prices, inflex_prices, deltas, ratios)
            ]
            for itm in comb:
                itm['direction'] = np.sign(itm['dist'])

            for i in range(0, len(comb)):
                if i == 0:
                    comb[i]['velocity'] = abs(comb[i]['dist']/momentum_block)
                    comb[i]['strength'] = 0
                    comb[i]['retrace_prev'] = 0
                    comb[i]['advance_fresh'] = 0
                    comb[i]['wave'] = 1
                    comb[i]['thrust'] = 0
                    comb[i]['portfolio'] = 0
                    comb[i]['prev_range'] = [df2.Close[df2.index == comb[i]['index']].to_list()[0],df2.Close[df2.index == comb[i]['index']].to_list()[0]]
                else:
                    prev_price_range = [min(df2.Close[df2.index <= comb[i - 1]['index']].to_list()),max(df2.Close[df2.index <= comb[i - 1]['index']].to_list())] #if i > 1 else [min(df2.Close[df2.index <= comb[i - 1]['index']].to_list()),max(df2.Close[df2.index <= comb[i - 1]['index']].to_list())]
                    #print(prev_price_range)
                    comb[i]['velocity'] =  abs(comb[i]['dist']/momentum_block)
                    comb[i]['strength'] = self.get_infl_count_between_infl(df2, comb[i-1]['index'], comb[i]['index'], "SPExt", 0, ["SPH", "SPL"])
                    if abs(comb[i]['dist']) > abs(comb[i-1]['dist']):
                        comb[i]['retrace_prev'] = abs(comb[i-1]['dist']) / momentum_block
                        comb[i]['advance_fresh'] = abs(abs(comb[i]['dist']) - abs(comb[i-1]['dist'])) / momentum_block
                        comb[i]['wave'] = 1
                        comb[i]['thrust'] = 0


                        if (comb[i]['direction'] > 0) and (comb[i]['end'] > prev_price_range[1]):
                            comb[i]['thrust'] = abs(comb[i]['end'] - prev_price_range[1]) / momentum_block
                        elif (comb[i]['direction'] < 0) and (comb[i]['end'] < prev_price_range[0]):
                            comb[i]['thrust'] = abs(comb[i]['end'] - prev_price_range[0]) / momentum_block

                    else:
                        comb[i]['advance_fresh'] = 0
                        comb[i]['wave'] = 2
                        comb[i]['thrust'] = 0
                    comb[i]['prev_range'] = prev_price_range
                    comb[i]['portfolio'] = comb[i]['direction'] * abs(comb[i]['dist']) * (abs(comb[i]['dist']) + 1) / 2


            #thrust_sum = [itm['direction'] * itm['thrust'] for itm in comb if itm['wave'] == 1]
            #print(sum(thrust_sum))
            for i in range(0, len(comb)):
                # find all waves which are in same direction
                dir_waves = 0 if i <= 1 else 1
                end_price = comb[i]['end']
                start_price = comb[i]['start'] #comb[i]['price'] + comb[i]['dist']
                # Filter only the waves in same direction
                filtered_waves = []
                for j in range(0, i):
                    if comb[j]['direction'] == comb[i]['direction']:
                        filtered_waves.append(comb[j])
                # calculate overlap
                wave_overlap = []
                #print('filtereing waves for +++++++++++++' , i)
                #print([start_price,end_price])
                #print(filtered_waves)
                for wave in filtered_waves:
                    wave_start = wave['start']
                    wave_end = wave['end']
                    overlap = get_overlap([start_price,end_price],  [wave_start, wave_end])
                    #print([start_price,end_price],  [wave_start, wave_end], overlap)
                    wave_overlap.append(overlap)
                wave_overlap.sort()
                wave_ol_dct = []
                # Split overlap into segments - This doesn't reflect correctly
                for k in range(len(wave_overlap)):
                    over_lap_count = len(wave_overlap) - k
                    over_lap_to_consider = max(over_lap_count - 1, 0)
                    #over_lap_to_consider = max(over_lap_count, 0)
                    if k == 0:
                        wave_ol_dct.append((wave_overlap[k], over_lap_to_consider))
                    else:
                        wave_ol_dct.append((wave_overlap[k] - wave_overlap[k-1], over_lap_to_consider))
                comb[i]['total_energy'] = abs(comb[i]['direction'] * abs(comb[i]['dist']) * (abs(comb[i]['dist']) + 1) / 2)
                fct = 0.1
                if i < 1:
                    comb[i]['static_energy'] = 0
                else:
                    static_energy = 0
                    #print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                    for ol_idx in range(len(wave_ol_dct)):
                        (ol, count) = wave_ol_dct[ol_idx]
                        prev_mark = 0 if ol_idx == 0 else sum([item[0] for item in wave_ol_dct[0:ol_idx]])
                        low_price_port = abs(comb[i]['dist'])-prev_mark
                        high_price_port = low_price_port - ol
                        total_port = (low_price_port + high_price_port) * ol/2
                        diffusion = abs(total_port * (1 - math.exp(-1*count)))
                        static_energy += diffusion
                        """
                        if(comb[i]['index']) == 147:
                            print('wave_ol_dct', wave_ol_dct)
                            print('prev_mark', prev_mark)
                            print('low_price_port', low_price_port)
                            print('high_price_port', high_price_port)
                            print('total_port', total_port)
                            print('diffusion', diffusion)
                            print('static_energy', static_energy)
                            #print('comb[i]', comb[i])
                        """
                    comb[i]['static_energy'] = static_energy

                comb[i]['dynamic_energy'] = comb[i]['total_energy'] - comb[i]['static_energy']
                comb[i]['ol'] = wave_ol_dct
                comb[i]['total_energy_pyr'] = comb[i]['total_energy'] / (0.5 * momentum_block * (momentum_block + 1))
                comb[i]['total_energy_ht'] = math.sqrt(abs(comb[i]['total_energy']) * 2) / momentum_block
                comb[i]['static_ratio'] = round(comb[i]['static_energy'] / (comb[i]['total_energy'] + 0.001), 2)
                comb[i]['dynamic_ratio'] = round(comb[i]['dynamic_energy'] / (comb[i]['total_energy'] + 0.001),2)
                comb[i]['d_en_ht'] = np.sign(comb[i]['dynamic_energy'])*math.sqrt(abs(comb[i]['dynamic_energy']) * 2) / momentum_block
                comb[i]['s_en_ht'] = np.sign(comb[i]['static_energy']) * math.sqrt(abs(comb[i]['static_energy']) * 2) / momentum_block
                comb[i]['d_en_pyr'] = comb[i]['dynamic_energy'] / (0.5 * momentum_block * (momentum_block+1))
                comb[i]['s_en_pyr'] = comb[i]['static_energy'] / (0.5 * momentum_block * (momentum_block + 1))

            tot = [x['total_energy'] for x in comb]
            stc = [x['static_energy'] for x in comb]
            dnc = [x['dynamic_energy'] * x['direction']for x in comb]
            #print('total static :', sum(stc))
            #print('total energy :', sum(tot))
            #print('static ratio :', round(sum(stc) / (sum(tot) + 0.001), 2) * 100)
            #print('dynamic ratio :', round(sum(dnc)/(sum(tot)+0.001), 2)*100)
            ret_val['all_waves'] = comb
            ret_val['trend']['total_energy']=sum(tot)
            ret_val['trend']['total_energy_pyr'] = sum(tot)/ (0.5 * momentum_block * (momentum_block+1))
            ret_val['trend']['total_energy_ht'] = math.sqrt(abs(sum(tot)) * 2) / momentum_block
            ret_val['trend']['static_ratio'] = round(sum(stc) / (sum(tot) + 0.001), 2)
            ret_val['trend']['dynamic_ratio'] = round(sum(dnc) / (sum(tot) + 0.001), 2)
            ret_val['trend']['d_en_ht'] = np.sign(sum(dnc)) * math.sqrt(abs(sum(dnc))*2) / momentum_block
            ret_val['trend']['s_en_ht'] = np.sign(sum(stc)) * math.sqrt(abs(sum(stc)) * 2) / momentum_block
            ret_val['trend']['d_en_pyr'] = sum(dnc) / (0.5 * momentum_block * (momentum_block+1))
            ret_val['trend']['s_en_pyr'] = sum(stc) / (0.5 * momentum_block * (momentum_block + 1))
            if len(comb) >= 4:
                last_wave = comb[-4]
                ret_val['last_wave']['lw_total_energy'] = last_wave['total_energy']
                ret_val['last_wave']['lw_total_energy_pyr'] = last_wave['total_energy'] / (0.5 * momentum_block * (momentum_block + 1))
                ret_val['last_wave']['lw_total_energy_ht'] = math.sqrt(abs(last_wave['total_energy']) * 2) / momentum_block
                ret_val['last_wave']['lw_static_ratio'] = round(last_wave['static_energy'] / (last_wave['total_energy'] + 0.001), 2)
                ret_val['last_wave']['lw_dynamic_ratio'] = round(last_wave['dynamic_energy'] / (last_wave['total_energy'] + 0.001),2)
                ret_val['last_wave']['lw_d_en_ht'] = np.sign(last_wave['dynamic_energy'])*math.sqrt(abs(last_wave['dynamic_energy']) * 2) / momentum_block
                ret_val['last_wave']['lw_s_en_ht'] = np.sign(last_wave['static_energy']) * math.sqrt(abs(last_wave['static_energy']) * 2) / momentum_block
                ret_val['last_wave']['lw_d_en_pyr'] = last_wave['dynamic_energy'] / (0.5 * momentum_block * (momentum_block+1))
                ret_val['last_wave']['lw_s_en_pyr'] = last_wave['static_energy'] / (0.5 * momentum_block * (momentum_block + 1))
            # Distance , Velocity , Impact, Energy Transfer, Oscilation, Static Energy, Kinetic Enenrgy, DIFFUSION, MAGNETIC FORCE

        return ret_val
            # find price near to last_price