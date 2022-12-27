from db.market_data import (get_all_days, get_daily_tick_data, prev_day_data, get_prev_week_candle, get_nth_day_profile_data, get_hist_ndays_profile_data)
import time
from datetime import datetime
import pandas as pd
import profile.utils as profile_utils
import helper.utils as helper_utils
import itertools
from itertools import chain, product
import calendar
import bnlearn as bn
from settings import reports_dir
from pgmpy.factors.discrete import TabularCPD
import numpy as np
import json

symbol = 'NIFTY'
open_type_codes = ['GAP_UP', 'GAP_DOWN', 'ABOVE_VA', 'BELOW_VA', 'INSIDE_VA']

def determine_day_open(open_candle, yday_profile):
    open_low = open_candle['open']
    open_high = open_candle['open']
    open_type = None
    if open_low >= yday_profile['high']:
        open_type = 'GAP_UP'
    elif open_high <= yday_profile['low']:
        open_type = 'GAP_DOWN'
    elif open_low >= yday_profile['va_h_p']:
        open_type = 'ABOVE_VA'
    elif open_high <= yday_profile['va_l_p']:
        open_type = 'BELOW_VA'
    else:
        open_type = 'INSIDE_VA'
    return open_type

def check_candle_patterns(df):
    op = df['open']
    hi = df['high']
    lo = df['low']
    cl = df['close']
    for pattern in pattern_names:
        # below is same as;
        # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
        df[pattern] = getattr(talib, pattern)(op, hi, lo, cl)
    return df


import talib
pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']
cdl_features_bull = [x + "_UP" for x in pattern_names]
cdl_features_bear = [x + "_DN" for x in pattern_names]
cdl_features = cdl_features_bull + cdl_features_bear


class DayFeaturesGenerator:
    def __init__(self, symbol, day):
        self.symbol = symbol
        self.trade_day = day
        self.price_bands = {}
        self.state_transition = []
        self.curr_state = ''
        self.state_queue = []
        self.max_size = 5
        self.open_type = "UKN"
        self.features_cat = {'candle':'CDL_UNK'}
        self.yday_profile = get_nth_day_profile_data(symbol, self.trade_day, 1).to_dict('records')[0]
        self.features_cat['week_day'] = calendar.day_name[self.yday_profile['date'].weekday()]
        hist_data = get_hist_ndays_profile_data(symbol, self.trade_day, 15)
        df = check_candle_patterns(hist_data)
        for pattern in pattern_names:
            if df[pattern].to_list()[-1] > 0:
                self.features_cat['candle'] = pattern + "_UP"
            if df[pattern].to_list()[-1] < 0:
                self.features_cat['candle'] = pattern + "_DN"

    def set_open_type(self,open_candle):
        self.features_cat['open_type'] = determine_day_open(open_candle, self.yday_profile)

    def set_up_states(self):
        poc = self.yday_profile['poc_price']
        vah = self.yday_profile['va_h_p']
        val = self.yday_profile['va_l_p']
        low = self.yday_profile['low']
        high = self.yday_profile['close']
        rng = range(-20, 22, 2)
        slabs = [round(poc * (1 + x / 1000)) for x in rng]
        poc_idx = profile_utils.get_next_lowest_index(slabs, poc)

        for i in range(len(slabs) - 1):
            if i <= poc_idx:
                self.price_bands[(slabs[i] + 0.01, slabs[i + 1])] = 'D' + str(poc_idx - i)
            else:
                self.price_bands[(slabs[i] + 0.01, slabs[i + 1])] = 'U' + str(i - poc_idx)

    def get_slab_for_price(self, curr_price):
        price_level = "S_UKN"
        for (band, level) in self.price_bands.items():
            if curr_price >= band[0] and curr_price <= band[1]:
                price_level = level
                # print(curr_price, price_level, band)
                break
        return price_level

    def update_state(self, curr_price):
        curr_band = self.get_slab_for_price(curr_price)
        self.state_queue.append(curr_band)
        if len(self.state_queue) > self.max_size:
            self.state_queue.pop(0)
        if self.curr_state not in self.state_queue:
            self.curr_state = self.state_queue[-1]
            self.state_transition.append(self.curr_state)

    def get_transition_2(self):
        transition = {}
        transition_list = []
        print(self.state_transition)
        for state in self.state_transition:
            if state in transition:
                transition[state] += 1
            else:
                transition[state] = 1
            transition_list.append(state + "_" + str(transition[state]))
        return transition_list

    def get_transition(self):
        return self.state_transition

    def get_features(self):
        transition_list = self.get_transition()
        print(transition_list)
        for transition in transition_list:
            self.features_cat['transition'] = transition_list
        return self.features_cat

def back_test(symbol, days):
    result_cat = {}
    start_time = datetime.now()
    for day in days:
        in_day = day if type(day) == str else day.strftime('%Y-%m-%d')
        feature_generator = DayFeaturesGenerator(symbol,in_day)
        print(day)
        print('=========================================================================================')
        price_list = get_daily_tick_data(symbol, day)
        price_list['symbol'] = helper_utils.root_symbol(symbol)
        price_list = price_list.to_dict('records')
        for j in range(len(price_list)):
            candle = price_list[j]
            curr_price = candle['close']
            if not j:
                feature_generator.set_up_states()
                feature_generator.set_open_type(candle)
            else:
                feature_generator.update_state(curr_price)
        features = feature_generator.get_features()
        result_cat[in_day] = features
    with open(reports_dir + 'stm_df.json', "w") as write_file:
        json.dump(result_cat, write_file, indent=4)
    """
    result_df = pd.DataFrame(result_cat)
    result_df.to_csv(reports_dir + 'stm_df.csv')
    """
def learn_structure():
    bn_df = pd.read_csv(reports_dir + 'bn_df.csv')
    bn_df.fillna(0, inplace=True)
    del bn_df['Unnamed: 0']
    #print(bn_df.columns.to_list())
    cols_set_1 = ['candle', 'week_day', 'open_type']
    cols_set_2 = [x for x in bn_df.columns.to_list() if x not in cols_set_1]
    cols_set_2.sort()
    edges = list(itertools.product(cols_set_1, cols_set_2))
    edges2 = [(x,y) for x in cols_set_2 for y in cols_set_2 if x != y]
    final_edge2 = []
    for edg_pair in edges2:
        print(edg_pair)

        occs = [edg.split("_")[-1] for edg in edg_pair]
        lebels = [edg.split("_")[0] for edg in edg_pair]
        lebels = [x if x != 'S' else 'L1' for x in lebels]
        print(lebels)
        levels = [int(label[1:]) for label in lebels]
        if levels[0] == levels[1]-1 and occs[0] < occs[1]:
            final_edge2.append(edg_pair)
    print(final_edge2)
    dfhot, dfnum = bn.df2onehot(bn_df)
    print(dfhot.columns)
    """
    DAG = bn.make_DAG(edges+edges2)
    DAG = bn.parameter_learning.fit(DAG, bn_df)
    bn.plot(DAG)
    """
    model = bn.structure_learning.fit(bn_df, fixed_edges=edges+final_edge2)
    #print(model)
    G = bn.plot(model, interactive=False)
    # Compute edge strength with the chi_square test statistic
    model = bn.independence_test(model, bn_df, test='chi_square', prune=True)
    # Plot
    bn.save(model, reports_dir + 'nifty_bn')
    bn.plot(model, interactive=False, pos=G['pos'])
    adjmat = model['adjmat']
    vector = bn.adjmat2vec(adjmat)
    print(vector)
    adjmat.to_csv(reports_dir + 'adm.csv')
    #bn.print_CPD(model)

def cpd_to_df(DAG, variable):
    DAG_2 = DAG.get('model', None) # This shows the DAG structure
    tab = DAG_2.get_cpds(variable)
    #print(tab.get_values())
    #print(tab.variables)
    #print(tab.cardinality)
    evidence = tab.variables[1:]
    evidence_card = tab.cardinality[1:]
    col_indexes = np.array(list(product(*[range(i) for i in evidence_card])))
    headers_list = []
    for i in range(len(evidence_card)):
        column_header = [str(evidence[i])] + [
            "{var}({state})".format(
                var=evidence[i], state=tab.state_names[evidence[i]][d]
            )
            for d in col_indexes.T[i]
        ]
        headers_list.append(column_header)

    #print(headers_list)
    variable_array = [
        ["{var}({state})".format(var=tab.variable, state=tab.state_names[tab.variable][i]) for i in range(tab.variable_card)]
    ]
    #print(tab)

    labeled_rows = np.hstack((np.array(variable_array).T, tab.get_values())).tolist()
    #print(labeled_rows)
    final_list = headers_list + labeled_rows
    df = pd.DataFrame(final_list)
    df = df.transpose()
    df.columns = df.iloc[0]
    df = df[1:]
    return df

def build_model():
    bn_df = pd.read_csv(reports_dir + 'bn_df.csv')
    bn_df.fillna(0, inplace=True)
    del bn_df['Unnamed: 0']
    dfhot, dfnum = bn.df2onehot(bn_df)
    structure = bn.load(reports_dir + 'nifty_bn')
    #print(structure['independence_test'].to_string())

    adjmat = structure['adjmat']
    vector = bn.adjmat2vec(adjmat)
    #print(vector.to_string())
    ml = bn.to_bayesiannetwork(structure)
    DAG = bn.make_DAG(structure)
    DAG = bn.parameter_learning.fit(DAG, bn_df, verbose=0)
    df = cpd_to_df(DAG,'U2_1')
    print(df.columns[4])
    df[df.columns[4]] = df[df.columns[4]].astype(float)
    df_tmp = df[df[df.columns[4]] > 0.6]
    print(df_tmp.to_string())
    #bn.print_CPD(DAG)
    #bn.plot(DAG)


    for cpd in DAG_2.get_cpds('U8_4'):
        print("CPD 2 of {variable}:".format(variable=cpd.variable))
        print(cpd)
        pass

    #q1 = bn.inference.fit(DAG, variables=['candle'])
    #print(q1.df)


def calc_prob(features):
    f = open(reports_dir + 'stm_df.json')
    data = json.load(f)
    print(data)


def predict(symbol, days):
    result_cat = {}
    for day in days:
        in_day = day if type(day) == str else day.strftime('%Y-%m-%d')
        feature_generator = DayFeaturesGenerator(symbol,in_day)
        price_list = get_daily_tick_data(symbol, day)
        price_list['symbol'] = helper_utils.root_symbol(symbol)
        price_list = price_list.to_dict('records')
        for j in range(len(price_list)):
            candle = price_list[j]
            curr_price = candle['close']
            if not j:
                feature_generator.set_up_states()
                feature_generator.set_open_type(candle)
            else:
                feature_generator.update_state(curr_price)
        features = feature_generator.get_features()
        result_cat[in_day] = features
    with open(reports_dir + 'stm_df.json', "w") as write_file:
        json.dump(result_cat, write_file, indent=4)



all_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
days = all_days[100:250]
back_test(symbol, days)

#learn_structure()
#build_model()








