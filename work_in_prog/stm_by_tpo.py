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
from transition.intra_day_transition import DayFullStateGenerator
from transition.mc_pre_process import MCPreprocessor
from transition.markov_chain import MarkovChain, MarkovChainTPO
from transition.first_level_mc import MarkovChainFirstLevel
from transition.second_level_mc import MarkovChainSecondLevel
from transition.point_to_point_mc import MarkovChainPointToPoint
from transition.empirical import EmpiricalDistribution

symbol = 'NIFTY'

def generate_hist_transition():
    all_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
    days = all_days[100:250]
    result_cat = {}
    for day in days:
        in_day = day if type(day) == str else day.strftime('%Y-%m-%d')
        feature_generator = DayFullStateGenerator(symbol,in_day)
        print(day)
        print('=========================================================================================')
        start_time = datetime.now()
        price_list = get_daily_tick_data(symbol, day)
        end_time = datetime.now()
        print('DB total', (end_time - start_time).total_seconds())

        price_list['symbol'] = helper_utils.root_symbol(symbol)
        price_list = price_list.to_dict('records')
        start_time = datetime.now()
        for j in range(len(price_list)):
            candle = price_list[j]
            curr_price = candle['close']
            if not j:
                #feature_generator.set_up_states()
                feature_generator.set_open_type(candle)
                feature_generator.update_state(curr_price)
            else:
                feature_generator.update_state(curr_price)
        features = feature_generator.get_features()
        result_cat[in_day] = features
        end_time = datetime.now()
        print('Generator total total', (end_time - start_time).total_seconds())

    with open(reports_dir + 'full_state_'+symbol+'.json', "w") as write_file:
        json.dump(result_cat, write_file, indent=4)

def get_model_data():
    f = open(reports_dir + 'full_state_'+symbol+'.json')
    data = json.load(f)
    return data



def get_prob(data, transition_field):
    """
    mc = MarkovChainFirstLevel()
    mc.from_data(data, transition_field)
    #print(dict(mc.model))
    df = pd.DataFrame(mc.observed_p_matrix, index=mc.states, columns=mc.states, dtype=float)
    df.to_csv(reports_dir + 'first_level_prob.csv')
    graph = mc.graph_make(
        format="png",
        graph_attr=[("rankdir", "LR")],
        node_attr=[("fontname", "Roboto bold"), ("fontsize", "20")],
        edge_attr=[("fontname", "Iosevka"), ("fontsize", "12")]
    )
    #graph.write_png(reports_dir + 'full_state_graph.png')
    graph.render(reports_dir + 'first_level_graph')
    """
    mc = MarkovChainPointToPoint()
    mc.from_data(data, transition_field)
    #print(dict(mc.model['D10']))
    df = pd.DataFrame(mc.observed_matrix, index=mc.states, columns=mc.states, dtype=float)
    df = df.loc[(df != 0).any(axis=1)]
    df = df.loc[:, (df != 0).any(axis=0)]

    #df = df[df.values.sum(axis=0) != 0]
    #df = df[df.values.sum(axis=1) != 0]
    df.to_csv(reports_dir + 'second_level_observed_' + transition_field + '.csv')
    df = pd.DataFrame(mc.total_matrix, index=mc.states, columns=mc.states, dtype=float)
    df = df.loc[(df != 0).any(axis=1)]
    df = df.loc[:, (df != 0).any(axis=0)]

    #df = df[df.values.sum(axis=0) != 0]
    #df = df[df.values.sum(axis=1) != 0]
    df.to_csv(reports_dir + 'second_level_total_' + transition_field + '.csv')
    df = pd.DataFrame(mc.observed_p_matrix, index=mc.states, columns=mc.states, dtype=float)
    df = df.loc[(df != 0).any(axis=1)]
    df = df.loc[:, (df != 0).any(axis=0)]

    #df = df[df.values.sum(axis=0) != 0]
    #df = df[df.values.sum(axis=1) != 0]
    df.to_csv(reports_dir + 'second_level_prob_' + transition_field + '.csv')

    """ - if graph printing is required
    graph = mc.graph_make(
        format="png",
        graph_attr=[("rankdir", "LR")],
        node_attr=[("fontname", "Roboto bold"), ("fontsize", "20")],
        edge_attr=[("fontname", "Iosevka"), ("fontsize", "12")]
    )
    #graph.write_png(reports_dir + 'full_state_graph.png')
    graph.render(reports_dir + 'second_level_graph_' + transition_field)
    """

#generate_hist_transition()
data = get_model_data()
pre_processed_data = MCPreprocessor().get_processed_data(data, symbol="NIFTY", start_tpo=1, end_tpo=None, use_range=[0,-1])

transition_field = 'observed_transitions'  # 'refined_transitions'
get_prob(pre_processed_data, transition_field)
ep = EmpiricalDistribution(pre_processed_data, transition_field)
"""
curr_events=[{'type': 'open_type', 'value':'GAP_UP'}]
pr = ep.get_distribution(curr_events=curr_events, forecast_states=['D9'])
print(pr)
if pr:
    for (k,v) in pr.items():
        p_un_cond = v['u_positive_outcomes']/v['count_uni_set']
        p_cond = v['count_sample_space'] and  v['c_positive_outcomes'] / v['count_sample_space'] or 0
        print('probability for '+ k +" given " + "|".join([event['value'] for event in curr_events]) + "====")
        print('unconditional =', p_un_cond)
        print('conditional =', p_cond)
"""
curr_events=[{'type': 'state', 'value':'D15'}]
pr = ep.get_distribution(curr_events=curr_events, forecast_states=['D18', 'D22'])
print(pr)
if pr:
    for (k,v) in pr.items():
        p_un_cond = v['u_positive_outcomes']/v['count_uni_set']
        p_cond = v['count_sample_space'] and  v['c_positive_outcomes'] / v['count_sample_space'] or 0
        print('probability for '+ k +" given " + "|".join([event['value'] for event in curr_events]) + "====")
        print('unconditional =', p_un_cond)
        print('conditional =', p_cond)








