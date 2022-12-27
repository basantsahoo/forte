import pandas as pd
import numpy as np
from trend.technical_patterns import pattern_engine
from rx.subject import Subject
from datetime import datetime
#from numba import jit
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import auc,r2_score
from scipy import stats
import math
from helper.utils import pattern_param_match
from patterns.technical_patterns import inflex_config

"""
1. A low is considered as low if it is proceeded by a high
2. A low is considered as low if its followed by high or it's last inflex
3. Among all lows between 2 highs lowest low is considered 
4. Reversal 
5. First pass Low -
    a. It must be a low inflex 
    a. If it's first low inflex then it's considered as FPL 
    b. Or it's formed after a threshold downward movement from previous FPH 
6. FPLCount/FPHCount - Cumulative Count of FPL/FPH
"""
class PriceInflexDetector:
    def __init__(self, symbol,  fpth = None, spth = None, tpth =None,  callback=None, fourth_pass=False):
        self.symbol = symbol
        self.fpth = fpth if fpth is None else inflex_config[symbol]['fpth']
        self.spth = spth if fpth is None else inflex_config[symbol]['spth']
        self.tpth = tpth if fpth is None else inflex_config[symbol]['tpth']
        self.fourth_pass = fourth_pass
        self.pBefore = 1
        self.minimum_data_points = self.pBefore * 2 + 1
        self.dfstock_2 = pd.DataFrame(
            columns=['Time', 'Close'])
        self.dfstock_3 = None
        self.callback = callback
        self.counter = 0
        self.trend_params = {}
        self.processed_first_point = False


    def create_inflex(self):
        i = self.dfstock_2.shape[0] - self.pBefore - 1
        df = self.dfstock_2
        if ((df['Close'][i] - df['Close'][i - self.pBefore]) > 0 and (
                df['Close'][i] - df['Close'][i + self.pBefore]) >= 0):
            df.loc[df.index[i], 'Inflex'] = 'LH'
        elif ((df['Close'][i] - df['Close'][i - self.pBefore]) < 0 and (
                df['Close'][i] - df['Close'][i + self.pBefore]) <= 0):
            df.loc[df.index[i], 'Inflex'] = 'LL'
        else:
            df.loc[df.index[i], 'Inflex'] = ''

        if not self.processed_first_point:
            infl_list = df[(df['Inflex']!='') & (df['Inflex'].notnull())]['Inflex'].tolist()
            if len(infl_list) > 0:
                first_inflex = infl_list[0]
                #print(first_inflex)
                if first_inflex == 'LL':
                    df.loc[df.index[0], 'Inflex'] = 'LH'
                elif first_inflex == 'LH':
                    df.loc[df.index[0], 'Inflex'] = 'LL'
                for i in range(0,self.dfstock_2.shape[0] - self.pBefore):
                    self.create_fp_inflex(i)
                self.processed_first_point = True

            #self.processed_first_point = True

    def create_fp_inflex(self, idx=None):
        i = self.dfstock_2.shape[0] - self.pBefore - 1 if idx is None else idx
        df = self.dfstock_2
        data = {}
        data['FPInflex'] = ''
        if i == 0:
            data['FPInflex'] = 'FPL' if df['Inflex'][i] == 'LL' else 'FPH' if df['Inflex'][i] == 'LH' else ''
            data['FPLCount'] = 1 if data['FPInflex'] == 'FPL' else 0
            data['FPHCount'] = 1 if data['FPInflex'] == 'FPH' else 0
            data['FPL In Range'] = 1 if data['FPInflex'] == 'FPL' else 0
            data['FPH In Range'] = 1 if data['FPInflex'] == 'FPH' else 0

            if data['FPInflex'] == 'FPL':
                data['Lowest FPL'] = df['Close'][i]
            if data['FPInflex'] == 'FPH':
                data['Highest FPH'] = df['Close'][i]

        else:
            if ((df['Inflex'][i] == 'LL') and ((df['FPLCount'][i - 1] == 0) or (
                    (df['FPHCount'][i - 1] > 0) and (df['Close'][i] < (1 - self.fpth) * df['Highest FPH'][i - 1])))):
                data['FPInflex'] = 'FPL'
            elif ((df['Inflex'][i] == 'LH') and ((df['FPHCount'][i - 1] == 0) or (
                    (df['FPLCount'][i - 1] > 0) and (df['Close'][i] > (1 + self.fpth) * df['Lowest FPL'][i - 1])))):
                data['FPInflex'] = 'FPH'

            data['FPLCount'] = (df['FPLCount'][i - 1] + 1) if data['FPInflex'] == 'FPL' else df['FPLCount'][i - 1]
            data['FPHCount'] = (df['FPHCount'][i - 1] + 1) if data['FPInflex'] == 'FPH' else df['FPHCount'][i - 1]
            data['FPL In Range'] = (df['FPL In Range'][i - 1] + 1) if data['FPInflex'] == 'FPL' else 0 if data['FPInflex'] == 'FPH' else df['FPL In Range'][i - 1]
            data['FPH In Range'] = (df['FPH In Range'][i - 1] + 1) if data['FPInflex'] == 'FPH' else 0 if data['FPInflex'] == 'FPL' else df['FPH In Range'][i - 1]

            if data['FPInflex'] == 'FPL':
                if df['FPLCount'][i - 1] == 0:
                    data['Lowest FPL'] = df['Close'][i]
                elif df['FPH In Range'][i - 1] > 0:
                    data['Lowest FPL'] = df['Close'][i]
                else:
                    data['Lowest FPL'] = min(df['Close'][i], df['Lowest FPL'][i - 1])
            else:
                data['Lowest FPL'] = df['Lowest FPL'][i - 1]

            if data['FPInflex'] == 'FPH':
                if df['FPHCount'][i - 1] == 0:
                    data['Highest FPH'] = df['Close'][i]
                elif df['FPL In Range'][i - 1] > 0:
                    data['Highest FPH'] = df['Close'][i]
                else:
                    data['Highest FPH'] = max(df['Close'][i], df['Highest FPH'][i - 1])
            else:
                data['Highest FPH'] = df['Highest FPH'][i - 1]
        df.loc[df.index[i], data.keys()] = data.values()


    def filter_extremes(self, index, arr):
        sp_ext = arr[0]
        close = arr[1]
        res = []
        for i in range(len(sp_ext) - 1):
            if (sp_ext[i] == sp_ext[i + 1]) and (close[i] == close[i + 1]):
                res.append(index[i])
        return res

    #@jit(nopython=True)
    def calculate_extremes(self, arr, high_label=1, low_label=-1):
        lowest_fpl = arr[0]
        fp_inflex = arr[1]
        highest_fph = arr[2]
        close = arr[3]
        fpl_count = arr[4]
        fph_count = arr[5]
        #itr = range(len(lowest_fpl) - self.pBefore - 1, self.pBefore - 1, -1)
        itr = range(len(lowest_fpl) - self.pBefore - 1,  - 1, -1)

        res = np.zeros((3, len(lowest_fpl)))
        totalfpi = max(fpl_count) + max(fph_count)
        #print(totalfpi)
        for i in itr:
            res[0][i] = lowest_fpl[i - 1] if fp_inflex[i] == high_label else res[0][i + 1]
            res[1][i] = highest_fph[i - 1] if fp_inflex[i] == low_label else res[1][i + 1]
            """
            if i == 53:
                print(i, close[i], res[0][i], res[1][i])
                print(res[0][i] == close[i])
                print(res[1][i] == close[i])
            """
            if res[0][i] == close[i]:
                res[2][i] = -1
            elif res[1][i] == close[i]:
                res[2][i] = 1

            derived_inflex_indices = [idx for idx, val in enumerate(res[2]) if val != 0]
            last_inflex_idx = max(derived_inflex_indices) if len(derived_inflex_indices) > 0 else -1
            if last_inflex_idx > -1 :
                last_inflex = res[2][last_inflex_idx]
                remaining_period_price = list(close[last_inflex_idx + 1:max(itr)+1])
                remaining_period_price_dup = remaining_period_price.copy()
                remaining_inflex = list(fp_inflex[last_inflex_idx + 1:max(itr)+1])

                if len(remaining_period_price) > 0:
                    if last_inflex == 1: #Last inflex is a high
                        remaining_inflex_prices = [remaining_period_price[idx] for idx, val in enumerate(remaining_inflex) if val == low_label]
                        if len(remaining_inflex_prices) > 0:
                            local_infl_index = remaining_period_price.index(min(remaining_inflex_prices))
                            #if fp_inflex[last_inflex_idx+local_infl_index+1] != '': #An inflex must be formed
                            res[2][last_inflex_idx+local_infl_index+1] = -1

                    elif last_inflex == -1:  # Last inflex is a low
                        remaining_inflex_prices = [remaining_period_price[idx] for idx, val in enumerate(remaining_inflex) if val == high_label]
                        if len(remaining_inflex_prices) > 0:
                            local_infl_index = remaining_period_price.index(max(remaining_inflex_prices))
                            #if fp_inflex[last_inflex_idx+local_infl_index+1] != '': #An inflex must be formed
                            res[2][last_inflex_idx+local_infl_index+1] = 1


        return res

    def create_sp_extremes(self):
        df = self.dfstock_2.copy()

        start_time = datetime.now()
        required_array = df[['Lowest FPL', 'FPInflex',  'Highest FPH',  'Close', 'FPLCount', 'FPHCount']].values.T
        required_array[1] = np.array([1 if x == 'FPH' else -1 if x == 'FPL' else 0 for x in required_array[1]])
        res = self.calculate_extremes(required_array)
        """
        if (res.shape[1]>53):
            print(res[:,53])
        """
        df['Local Min'] = res[0]
        df['Local Max'] = res[1]
        df['SPExt'] = res[2]
        df['SPExt'] = df['SPExt'].apply(lambda x: 'SPH' if x > 0 else 'SPL' if x < 0 else '')
        end_time = datetime.now()
        # print('all extrems', (end_time - start_time).total_seconds())

        temp = df[df['SPExt'] != '']
        #print(temp)
        start_time = datetime.now()
        res2 = self.filter_extremes(temp.index, temp[['SPExt', 'Close']].values.T)
        #print(res2)
        #df.loc[res2, 'SPExt'] = ''  # test this one
        self.dfstock_3 = df
        end_time = datetime.now()

        # print('loop 2', (end_time - start_time).total_seconds())

    def create_tp_inflex(self, idx=None):
        arr = self.dfstock_3[['Close', 'SPExt']].values.T
        close = arr[0]
        sp_ext = arr[1]
        itr = range(0, len(close) - self.pBefore if idx is None else idx)

        res = np.zeros((7, len(close)))
        for i in itr:
            if i == 0:
                # TPInflex, TPLCount, TPHCount, TPL In Range, TPH In Range, Lowest TPL, Highest TPH
                res[0][i] = -1 if sp_ext[i] == 'SPL' else 1 if sp_ext[i] == 'SPH' else 0
                res[1][i] = 1 if res[0][i] == -1 else 0
                res[2][i] = 1 if res[0][i] == 1 else 0
                res[3][i] = 1 if res[0][i] == -1 else 0
                res[4][i] = 1 if res[0][i] == 1 else 0
                res[5][i] = close[i] if res[0][i] == -1 else 0
                res[6][i] = close[i] if res[0][i] == 1 else 0
            else:
                if ((sp_ext[i] == 'SPL') and ((res[1][i - 1] == 0) or ((res[2][i - 1] > 0) and (close[i] < (1 - self.tpth) * res[6][i - 1])))):
                    res[0][i] = -1
                elif ((sp_ext[i] == 'SPH') and ((res[2][i - 1] == 0) or ((res[1][i - 1] > 0) and (close[i] > (1 + self.tpth) * res[5][i - 1])))):
                    res[0][i] = 1

                res[1][i] = (res[1][i - 1] + 1) if res[0][i] == -1 else res[1][i - 1]
                res[2][i] = (res[2][i - 1] + 1) if res[0][i] == 1 else res[2][i - 1]
                res[3][i] = (res[3][i - 1] + 1) if res[0][i] == -1 else 0 if res[0][i] == 1 else res[3][i - 1]
                res[4][i] = (res[4][i - 1] + 1) if res[0][i] == 1 else 0 if res[0][i] == -1 else res[4][i - 1]

                if res[0][i] == -1:
                    if res[1][i - 1] == 0:
                        res[5][i] = close[i]
                    elif res[4][i - 1] > 0:
                        res[5][i] = close[i]
                    else:
                        res[5][i] = min(close[i], res[5][i - 1])
                else:
                    res[5][i] = res[5][i - 1]

                if res[0][i] == 1:
                    if res[2][i - 1] == 0:
                        res[6][i] = close[i]
                    elif res[3][i - 1] > 0:
                        res[6][i] = close[i]
                    else:
                        res[6][i] = max(close[i], res[6][i - 1])
                else:
                    res[6][i] = res[6][i - 1]
        # TPInflex, TPLCount, TPHCount, TPL In Range, TPH In Range, Lowest TPL, Highest TPH
        self.dfstock_3['TPInflex'] = res[0]
        self.dfstock_3['TPLCount'] = res[1]
        self.dfstock_3['TPHCount'] = res[2]
        self.dfstock_3['TPL In Range'] = res[3]
        self.dfstock_3['TPH In Range'] = res[4]
        self.dfstock_3['Lowest TPL'] = res[5]
        self.dfstock_3['Highest TPH'] = res[6]
        self.dfstock_3['TPInflex'] = self.dfstock_3['TPInflex'].apply(lambda x: 'TPH' if x > 0 else 'TPL' if x < 0 else '')


    def create_fourth_pass_extremes(self):
        df = self.dfstock_3.copy()

        start_time = datetime.now()
        required_array = df[['Lowest TPL', 'TPInflex',  'Highest TPH',  'Close', 'TPLCount', 'TPHCount']].values.T
        required_array[1] = np.array([1 if x == 'TPH' else -1 if x == 'TPL' else 0 for x in required_array[1]])

        res = self.calculate_extremes(required_array)
        """
        if (res.shape[1]>53):
            print(res[:,53])
        """
        df['Local Fourth Min'] = res[0]
        df['Local Fourth Max'] = res[1]
        df['FourthExt'] = res[2]
        df['FourthExt'] = df['FourthExt'].apply(lambda x: 'FRPH' if x > 0 else 'FRPL' if x < 0 else '')
        end_time = datetime.now()
        # print('all extrems', (end_time - start_time).total_seconds())

        temp = df[df['FourthExt'] != '']
        #print(temp)
        start_time = datetime.now()
        res2 = self.filter_extremes(temp.index, temp[['FourthExt', 'Close']].values.T)
        #print(res2)
        #df.loc[res2, 'SPExt'] = ''  # test this one
        self.dfstock_3 = df
        end_time = datetime.now()


    def on_price_update(self, price_point):
        start_time = datetime.now()
        self.dfstock_2 = self.dfstock_2.append([{'Time': price_point[0], 'Close': price_point[1]}], ignore_index=True)
        end_time = datetime.now()
        # print('append', (end_time - start_time).total_seconds())

        if self.dfstock_2.shape[0] == 1:
            #print('all initialization here')
            self.dfstock_2['Inflex'] = ''
            self.dfstock_2['FPInflex'] = ''
            self.dfstock_2['FPLCount'] = 0
            self.dfstock_2['FPHCount'] = 0
            self.dfstock_2['FPL In Range'] = 0
            self.dfstock_2['FPH In Range'] = 0
            self.dfstock_2['Lowest FPL'] = 0
            self.dfstock_2['Highest FPH'] = 0


        if self.dfstock_2.shape[0] >= self.minimum_data_points:
            start_time = datetime.now()
            self.create_inflex()
            end_time = datetime.now()
            # print('create_inflex', (end_time - start_time).total_seconds())

            start_time = datetime.now()
            self.create_fp_inflex()
            end_time = datetime.now()
            # print('create_fp_inflex', (end_time - start_time).total_seconds())

            start_time = datetime.now()
            self.create_sp_extremes()
            end_time = datetime.now()
            # print('create_sp_extremes', (end_time - start_time).total_seconds())


class PriceInflexDetectorForTrend(PriceInflexDetector):
    def getSPTrend(self, pat_points=2):
        sp_infl = np.where([self.dfstock_3.SPExt != ''])[1]
        if len(sp_infl) >= pat_points:
            pattern_sp_infl_idx = sp_infl[range(-pat_points, -0)]
            pattern_sp_infl_lvl = self.dfstock_3.Close[pattern_sp_infl_idx].to_list()
            #print(pattern_sp_infl_idx)

            if pattern_sp_infl_lvl[1] > pattern_sp_infl_lvl[0] and self.callback is not None:
                self.callback(self.dfstock_3.Time[pattern_sp_infl_idx[1]])

    def get_trend_params(self):
        if self.dfstock_3.shape[0] >= 60:
            sp_infl = np.where([self.dfstock_3.SPExt != ''])[1]
            pattern_sp_infl_lvl = self.dfstock_3.Close[sp_infl].to_list()
            pattern_sp_infl_lvl = [x/self.dfstock_3.Close[0] for x in pattern_sp_infl_lvl] #standardise by deviding close of first candle
            sp_infl = [x/60/24 for x in sp_infl] #convert minutes to days for scalling down
            #print(sp_infl, pattern_sp_infl_lvl)
            reg = np.polyfit(sp_infl, pattern_sp_infl_lvl, 2)
            trendpoly = np.poly1d(reg)
            #print(reg)
            quadratic_comp =  np.poly1d([reg[0], 0, reg[2]])
            linear_comp = np.poly1d([0, reg[1], reg[2]])
            """
            slope, intercept, q_r_value, p_value, std_err = stats.linregress(pattern_sp_infl_lvl, quadratic_comp(sp_infl))
            print(slope, intercept, q_r_value, p_value, std_err)
            slope, intercept, l_r_value, p_value, std_err = stats.linregress(pattern_sp_infl_lvl, linear_comp(sp_infl))
            print(slope, intercept, l_r_value, p_value, std_err)
            """
            """
            plt.plot(sp_infl, pattern_sp_infl_lvl)
            plt.plot(sp_infl, trendpoly(sp_infl))
            plt.plot(sp_infl, linear_comp(sp_infl))
            plt.plot(sp_infl, quadratic_comp(sp_infl))
            plt.show()
            """
            q_r_value = r2_score(pattern_sp_infl_lvl,quadratic_comp(sp_infl))
            l_r_value = r2_score(pattern_sp_infl_lvl, linear_comp(sp_infl))
            market_auc = auc(sp_infl, trendpoly(sp_infl))/(sp_infl[-1]-sp_infl[0])
            trend_auc =  0.5 * (pattern_sp_infl_lvl[-1] + pattern_sp_infl_lvl[0])
            result = {'pattern_quad' : round(reg[0],4), 'pattern_lin':round(reg[1],4), 'pattern_quad_r2':round(q_r_value,2) , 'pattern_lin_r2':round(l_r_value,2) , 'pattern_market_auc': round(market_auc,4), 'pattern_trend_auc': round(trend_auc,4), 'pattern_auc_del': round(market_auc-trend_auc,4), 'infl_0': round(pattern_sp_infl_lvl[0]*self.dfstock_3.Close[0],4), 'infl_n': round(pattern_sp_infl_lvl[-1]*self.dfstock_3.Close[0],4)}
            return result
        else:
            return {}



    def on_price_update(self, price_point):
        self.dfstock_2 = self.dfstock_2.append([{'Time': price_point[0], 'Close': price_point[1]}], ignore_index=True)
        if self.dfstock_2.shape[0] == 1:
            #print('all initialization here')
            self.dfstock_2['Inflex'] = ''
            self.dfstock_2['FPInflex'] = ''
            self.dfstock_2['FPLCount'] = 0
            self.dfstock_2['FPHCount'] = 0
            self.dfstock_2['FPL In Range'] = 0
            self.dfstock_2['FPH In Range'] = 0
            self.dfstock_2['Lowest FPL'] = 0
            self.dfstock_2['Highest FPH'] = 0

        if self.dfstock_2.shape[0] >= self.minimum_data_points:
            self.create_inflex()
            self.create_fp_inflex()
            self.create_sp_extremes()
            if self.fourth_pass:
                self.create_tp_inflex()
                self.create_fourth_pass_extremes()
            """
            if self.dfstock_2.shape[0] % 15 == 0:
                print(self.dfstock_3[self.dfstock_3['SPExt']!=''].T)
                self.dfstock_3.to_csv('test_df.csv')
            #self.getSPTrend()
            """
    def update_trend(self):
        if self.dfstock_2.shape[0] >= self.minimum_data_points:
            self.trend_params = self.get_trend_params()
