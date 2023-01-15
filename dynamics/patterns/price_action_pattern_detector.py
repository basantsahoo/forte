import numpy as np
from statistics import mean
from dynamics.patterns.technical_patterns import pattern_config
from dynamics.constants import PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP
dt_between_highs_diff = 0.0006
dt_height_th = 0.3
pat_conf = {'len': 4, 'end_infl' : 'SPH'}



class PriceActionPatternDetector:
    def __init__(self, insight_book, period):
        self.insight_book = insight_book
        self.last_match = None
        self.period = period
        self.enabled_patterns = [INDICATOR_DOUBLE_TOP]
        self.infirm_patterns = []
        self.pat_conf = pattern_config[INDICATOR_DOUBLE_TOP]

    def get_suitable_prior_infl(self, df2, base_index, search_infl, base_price, threshold):
        df_infl_ = df2[(df2['SPExt'] == search_infl) & (df2.index < base_index)][['SPExt', 'Close']]
        itr = list(df_infl_.index)
        itr.reverse()
        _idx_to_check = []
        for i in itr:
            if df_infl_.Close[i] / base_price > (1 + threshold):
                break
            elif df_infl_.Close[i] / base_price > (1 - threshold):
                _idx_to_check.append(i)
        _idx_to_check.reverse() # look from first match
        return _idx_to_check

    def get_infl_count_between_infl(self, df2, start_index, end_index, threshold, cat="HIGHER", infl=[]):
        if cat == "HIGHER":
            tmp_df_infl = df2[(df2.index > start_index) & (df2.index < end_index) & (df2.SPExt.isin(infl)) & (df2.Close > threshold)]
        else:
            tmp_df_infl = df2[(df2.index > start_index) & (df2.index < end_index) & (df2.SPExt.isin(infl)) & (df2.Close < threshold)]
        count = tmp_df_infl.shape[0]
        return count

    def get_minima_between_infl(self, df2, start_index, end_index):
        minima = None
        minima_idx = None
        tmp_df_infl = df2[(df2.index > start_index) & (df2.index <= end_index)]
        if tmp_df_infl.shape[0] > 0:
            minima = min(tmp_df_infl.Close)
            # Third point found
            minima_idx = tmp_df_infl[tmp_df_infl['Close'] == minima].index[0]  # point 3
        return [minima_idx, minima]

    def get_minima_infl_between_infl(self, df2, start_index, end_index):
        minima = None
        minima_idx = None
        tmp_df_infl = df2[(df2.index > start_index) & (df2.index < end_index) & (df2.SPExt != '')]
        if tmp_df_infl.shape[0] > 0:
            minima = min(tmp_df_infl.Close)
            # Third point found
            minima_idx = tmp_df_infl[tmp_df_infl['Close'] == minima].index[0]  # point 3
        return [minima_idx, minima]

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
    most recent inflex
    """
    def search_most_recent_inflx(self, df2, infl=None):
        pos = ()
        if infl is None:
            all_sp_infl = np.array(df2.index[df2.SPExt != ''])
        else:
            all_sp_infl = np.array(df2.index[df2.SPExt == infl])
        if len(all_sp_infl) > 0:
            recent_infl_idx = all_sp_infl[-1]
            recent_infl_price = df2.Close[recent_infl_idx]
            pos = (recent_infl_idx, recent_infl_price)
        return pos

    def check_dt_pattern(self, df2):

        ret_val = {}
        # row position where inflex occured
        #sp_infl = np.where([df2.SPExt != ''])[1]
        all_sp_infl = np.array(df2.index[df2.SPExt != ''])
        meets_min_criteria = len(all_sp_infl) > self.pat_conf['len'] #and df2.SPExt[sp_infl[-1]] == self.pat_conf['end_infl']
        if meets_min_criteria: #minimum 4 inflex required excluding last one (To do when sharp fall after last inflex and last inflext takes long time)

            last_infl = df2.SPExt[all_sp_infl[-1]]
            # point 4
            (pattern_end_infl_idx, pattern_end_infl_price) = self.search_most_recent_inflx(df2, 'SPH')
            # point 5
            [recent_infl_idx, recent_infl_price] = self.get_minima_between_infl(df2, pattern_end_infl_idx, list(df2.index)[-1])
            # possible point 2
            sph_idx_to_check = self.get_suitable_prior_infl(df2,pattern_end_infl_idx,'SPH', pattern_end_infl_price, self.pat_conf['similar_highs_th'])
            # try to form pattern with all possible prev highs
            pattern_found = False
            #print('check_dt_pattern', np.array(df2.index)[-1],pattern_end_infl_idx, pattern_end_infl_price, sph_idx_to_check)
            for second_point_idx in sph_idx_to_check:

                # Third point found
                [minima_idx, minima] = self.get_minima_infl_between_infl(df2, second_point_idx, pattern_end_infl_idx)
                if minima_idx is None:
                    continue
                #There shouldn't be any high between two highs of DT
                second_point_price = df2.Close[second_point_idx]
                high_count = self.get_infl_count_between_infl(df2, second_point_idx, pattern_end_infl_idx, max(second_point_price, pattern_end_infl_price), 'HIGHER', ['SPH'])
                if high_count > 0:
                    # #31-May 30 May 07 Jun-- recheck individually
                    continue
                # Look for first point
                trend_begin_point = self.get_trend_begin_point(df2, second_point_idx)
                if trend_begin_point[0] is not None:
                    height = pattern_end_infl_price - minima
                    first_point_idx = trend_begin_point[0]
                    first_point_price = trend_begin_point[1]
                    if (minima - trend_begin_point[1]) >= self.pat_conf['min_height_th'] * height:
                        #print('last infl', last_infl)
                        # print([df2.Time[first_point_idx], df2.Time[second_point_idx], df2.Time[minima_idx], df2.Time[pattern_end_infl_idx]])
                        # print('minima after patter 4th', recent_infl_price)
                        # print('minima before pattern 4th', minima)
                        # print('last price', df2.Close.tolist()[-1])
                        if recent_infl_price < minima: #Double top confirmed
                            pattern_found = True
                            #print(first_point_idx)
                            ret_val = {'time_list':[df2.Time[first_point_idx], df2.Time[second_point_idx], df2.Time[minima_idx], df2.Time[pattern_end_infl_idx], df2.Time[recent_infl_idx]],
                                       'price_list':[first_point_price, df2.Close[second_point_idx], minima,  pattern_end_infl_price]}
                            # print('success first time', ret_val)
                            break
                            # print('total highs found', len(sph_idx_to_check))
                            # print('first_point_price ', first_point_price)
                            # print('recent_price ', recent_infl_price)
                        # There is already a low formed in between so we need to keep looking

                        elif recent_infl_price >= minima and recent_infl_price < pattern_end_infl_price and last_infl != self.pat_conf['end_infl']:
                            # print('pattern exists?+++++++++++++++++++++++++++++++++++++++++++++', self.infirm_pattern_exists(df2.Time[pattern_end_infl_idx]))
                            if not self.infirm_pattern_exists(df2.Time[pattern_end_infl_idx]):
                                self.infirm_patterns.append({'pattern':INDICATOR_DOUBLE_TOP, 'time_list':[df2.Time[first_point_idx], df2.Time[second_point_idx], df2.Time[minima_idx], df2.Time[pattern_end_infl_idx]]})
                                # print(self.infirm_patterns)

            if pattern_found:
                # print('occured at length', df2.shape[0])
                pass
        """    
        if df2.shape[0] > 10:
            ret_val = {'time_list': [1652932200, 1652932560, 1652932920, 1652933160, 1652933520], 'price_list': [15917.6, 15959.95, 15929.35, 15951.55]}
        """
        return ret_val
            # find price near to last_price


    def check_pattern(self, df2, pattern):
        if pattern == INDICATOR_DOUBLE_TOP:
            return self.check_dt_pattern(df2)
        else:
            return []

    def pattern_broken(self, df, pattern_data):
        broken = False
        if pattern_data['pattern'] == INDICATOR_DOUBLE_TOP:
            last_infl_time = pattern_data['time_list'][3]
            # pattern broken when price moves above previous high
            broken = max(df[df['Time']>last_infl_time]['Close'].to_list()) > df[df['Time'] == last_infl_time]['Close'].tolist()[0]
        # print('is broken+++++', broken)
        return broken

    def pattern_confirmed(self, df, pattern_data):
        #print('checking confirmation', pattern_data)
        ret_val = []
        if pattern_data['pattern'] == INDICATOR_DOUBLE_TOP:
            minima_time = pattern_data['time_list'][2]
            last_infl_time = pattern_data['time_list'][3]
            # print(df[df['Time'] > minima_time])
            # print('lowest price inside confirm', min(df[df['Time'] > last_infl_time]['Close'].to_list())) # lowest price
            # print('last price inside confirm', df['Close'].to_list()[-1])  # lowest price
            # print(df[df['Time'] == minima_time]['Close'].tolist()[0]) #minima
            # pattern confirmed when price below minima
            confirmed = min(df[df['Time'] > last_infl_time]['Close'].to_list()) < df[df['Time'] == minima_time]['Close'].tolist()[0]

            # print('confirmed', confirmed)
            if confirmed:
                recent_infl_time = list(df.Time)[-1]
                time_list = pattern_data['time_list'].copy()
                price_list = df[df.Time.isin(time_list)]['Close'].to_list()
                time_list.append(recent_infl_time)
                ret_val = {'time_list': time_list, 'price_list': price_list}


        return ret_val

    def infirm_pattern_exists(self, query_time):
        exists = False
        for infirm_pattern in self.infirm_patterns:
            if infirm_pattern['time_list'][-1] == query_time:
                exists = True
                break
        return exists



    def reevaluate_pending_patterns(self):
        pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
        for infirm_pattern in self.infirm_patterns.copy():
            if self.pattern_broken(pattern_df, infirm_pattern):
                self.infirm_patterns.remove(infirm_pattern)
            else:
                matched_pattern = self.pattern_confirmed(pattern_df, infirm_pattern)
                if len(matched_pattern) > 0:
                    # print('success on reevaluation', matched_pattern)
                    pat = {'category': PRICE_ACTION_INTRA_DAY, 'indicator': infirm_pattern['pattern'], 'signal': 1, 'strength': 0,
                           'signal_time': matched_pattern['time_list'][-1] if 'time_list' in matched_pattern else self.insight_book.spot_processor.last_tick['timestamp'],
                           'notice_time': self.insight_book.spot_processor.last_tick['timestamp'],
                           'info': matched_pattern}
                    self.insight_book.pattern_signal(pat)
                    #self.insight_book.pattern_signal(infirm_pattern['pattern'], matched_pattern)
                    self.infirm_patterns.remove(infirm_pattern)
                    # print('pending patterns after removal', self.infirm_patterns)

    def evaluate(self):
        self.reevaluate_pending_patterns()
        pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
        #print(pattern_df)
        if pattern_df is not None:# and pattern_df.shape[0] > 260: -- for testing only
            for pattern in self.enabled_patterns:
                matched_pattern = self.check_pattern(pattern_df, pattern)
                if matched_pattern:
                    #print(matched_pattern)
                    #print(list(pattern_df.Time))
                    pat = {'category': PRICE_ACTION_INTRA_DAY, 'indicator': pattern, 'signal': 1, 'strength': 0,
                           'signal_time': matched_pattern['time_list'][-1] if 'time_list' in matched_pattern else self.insight_book.spot_processor.last_tick['timestamp'],
                           'notice_time': self.insight_book.spot_processor.last_tick['timestamp'],
                           'info': matched_pattern}
                    self.insight_book.pattern_signal(pat)


