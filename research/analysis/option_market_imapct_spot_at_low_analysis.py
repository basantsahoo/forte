#from backtest import strategy_back_tester
from research.analysis import classifier_train
from research.analysis import regression_train
from research.analysis import descriptive_analysis_multi_dataset
from research.analysis import parameter_grid_search
import pandas as pd
import numpy as np
from servers.server_settings import reports_dir
import matplotlib.pyplot as plt

"""
def save_back_test_results():
    # results = strategy_back_tester.test(strategy_class=SMACrossBuy, symbols=['NIFTY'],days=['2022-05-25'])
    results = strategy_back_tester.test(SMACrossBuy, ['NIFTY'], days=['2022-06-03'], for_past_days=300)
    #pd.DataFrame(results).to_csv(reports_dir + 'SMACrossBuy_nifty_results.csv')
"""
def load_time_results():
    df = pd.read_csv(reports_dir + 'Inflex_analysis/low_inflex/bear_market/' + 'option_market_impact_spot_sell.csv')
    return df

def load_inflex_results():
    df = pd.read_csv(reports_dir + 'Inflex_analysis/low_inflex/bear_market/' + 'option_market_impact_spot_at_low.csv')
    return df



def basic_statistics(df):
    print("Total no of days pattern matched ====", len(df['day'].unique()))
    print("Total no of  pattern matched ====", len(df['entry_time'].unique()))
    print("Trades per day", len(df['entry_time'].unique())/len(df['day'].unique()))
    print("Avg Return", np.mean(df['return_pct'].to_list()))
    print("Total Return", np.sum(df['return_pct'].to_list()))
    print("Accuracy", len(df[df['return_pct'] > 0])/len(df['return_pct']))

def get_cleaned_results(df):
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    drop_cols = ['Unnamed: 0', 'symbol', 'trade_id', 'leg', 'side', 'exit_time',
                 'seq', 'instrument', 'cover', 'market_view', 'spot_target', 'spot_stop_loss',
                 'spot_stop_loss_rolling', 'instr_target', 'instr_stop_loss', 'duration', 'quantity'
                 'spot_entry_price', 'spot_exit_price', 'trigger_time', 'open_type', 'spot',
                 '', '', '',  '', '', '', '', '', '', '',
                 'stop_loss', 'quantity', 'neck_point', 'exit_type','closed', 'pattern_time',	'pattern_price', 'duration', 'entry_time_read']

    for col in drop_cols:
        try:
            df.drop(col, axis=1, inplace=True)
        except:
            pass
    select_cols = [
                'day',
            'strategy',
            'entry_time',
            'entry_price',
            'exit_price',
            'realized_pnl',
            'un_realized_pnl',
            'week_day',
            'tpo',
            'call_volume_scale',
            'put_volume_scale',
            'sum_call_volume',
            'sum_put_volume',
            'call_volume_scale_day',
            'put_volume_scale_day',
            'pcr_minus_1',
            'regime',
            'market_entrant',
            'call_entrant',
            'put_entrant',
            'transition',
            'roll_near_vol_pcr',
            'roll_far_vol_pcr',
            'roll_vol_spread_pcr',
            'put_pos_price_pct',
            'call_pos_price_pct',
            'call_vol_spread',
            'put_vol_spread',
            'total_vol_spread',
            'total_profit',
            'call_profit',
            'put_profit',
            'day_total_profit',
            'day_call_profit',
            'day_put_profit',
            'near_put_oi_share',
            'far_put_oi_share',
            'near_call_oi_share',
            'far_call_oi_share',
            'put_oi_spread',
            'call_oi_spread',
            'near_call_volume_share_per_oi',
            'near_put_volume_share_per_oi',
            'far_call_volume_share_per_oi',
            'far_put_volume_share_per_oi',
            'pattern_location',
            'call_drop',
            'put_drop',
            'r_near_put_volume_per_oi',
            'r_far_put_volume_per_oi',
            'r_near_call_volume_per_oi',
            'r_far_call_volume_per_oi',
            'r_total_call_volume_per_oi',
            'r_total_put_volume_per_oi',
            'r_call_vol_spread',
            'r_put_vol_spread',
            'near_vol_pcr',
            'far_vol_pcr',
            'r_total_vol_pcr',

    ]
    min_buffer = 0
    df = df[select_cols]
    df['realized_pnl'] = df['realized_pnl'] + df['un_realized_pnl']
    df['realized_pnl'] = df['realized_pnl'].apply(lambda x: x - min_buffer)
    df['return_pct'] = df['realized_pnl']/df['entry_price']
    df['put_call_vol_scale_diff'] = df['put_volume_scale'] - df['call_volume_scale']
    df['put_call_vol_scale_diff_day'] = df['put_volume_scale_day'] - df['call_volume_scale_day']
    df['vol_rat'] = df['sum_put_volume']/df['sum_call_volume']
    del df['un_realized_pnl']
    #del df['realized_pnl']
    #df = df[df['tpo'] < 13]
    return df

def analysis(df):

    exclude_vars_in_analysis = ['symbol', 'signal_id', 'trigger', 'entry_time',  'entry_price', ]
    print('going to describe')
    descriptive_analysis_multi_dataset.perform_analysis_strategies_multi_df(df, df, 'return_pct', exclude_vars_in_analysis)

    exclude_vars = ['day', 'symbol', 'signal_id', 'strategy', 'entry_time', 'infl_0', 'infl_n', 'entry_price', 'trigger_time']
    corr_vars = [
        'call_volume_scale',
        'put_volume_scale',
        'sum_call_volume',
        'sum_put_volume',
        'call_volume_scale_day',
        'put_volume_scale_day',
        'pcr_minus_1',
        'market_entrant',
        'call_entrant',
        'put_entrant',
        'transition',
        'roll_near_vol_pcr',
        'roll_far_vol_pcr',
        'roll_vol_spread_pcr',
        'put_pos_price_pct',
        'call_pos_price_pct',
        'call_vol_spread',
        'put_vol_spread',
        'total_vol_spread',
        'total_profit',
        'call_profit',
        'put_profit',
        'day_total_profit',
        'day_call_profit',
        'day_put_profit',
        'near_put_oi_share',
        'far_put_oi_share',
        'near_call_oi_share',
        'far_call_oi_share',
        'put_oi_spread',
        'call_oi_spread',
        'dir_pos_price_pct',
        'dir_inv_neg_price_pct',
        'pattern_location'
                 ]
    class_vars = [ 'week_day', 'tpo', 'regime']
    strategies = df['strategy'].unique()
    root_strategies = set([x.split("_")[0] for x in strategies])
    print('total patterns matched___', len(list(root_strategies)))

    for strategy in strategies:
        print('classification for ================== ', strategy)
        # if strategy == 'CDLXSIDEGAP3METHODS_5_BUY_30':
        df_tmp = df[df['strategy'] == strategy] [class_vars + corr_vars + ['return_pct']]
        print(df_tmp.columns.to_list())
        classifier_train.train(df_tmp, 'return_pct', exclude_vars)
        data_set = df[df['strategy'] == strategy][corr_vars + ['return_pct']].copy()
        try:
            del data_set['week_day']
        except:
            pass
        correlations = data_set.corr(method='pearson')
        correlations.to_csv('corr.csv')
        # print(correlations)

strat_days = set()


def scen_1():

    #save_back_test_results()

    df = get_cleaned_results()
    df = df[(df['day_put_profit'] >= 0) & (df['day_put_profit'] < 0.2)]
    #df = df[df['regime'].isin([ 'call_buildup', 'put_covering'])]
    df = df[(df['day_call_profit'] < 0.02) & (df['day_call_profit'] >= -0.01)]
    df = df[(df['vol_rat'] >= 1.6)]
    """
    df = df[(df['put_pos_price_pct'] >= 0.505)]
    df = df[(df['far_put_volume_share_per_oi'] >= 1.1)] #Factor 1 works in all scenario
    df = df[(df['vol_rat'] > 1)]
    """
    #df = df[(df['put_call_vol_scale_diff'] >= 0)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))

    #portfolio_performance(df)
    #analysis(df)

def scen_2():

    #save_back_test_results()

    df = get_cleaned_results()
    #df =  df[(df['pcr_minus_1'] <= -0.25) | (df['pcr_minus_1'] >= 1.25)]
    #df = df[(df['realized_pnl'] > 100)]
    df = df[(df['day_put_profit'] < -0.4)]
    df = df[(df['far_put_oi_share'] > 0.25)]
    df = df[(df['pcr_minus_1'] <= -0.1)]
    df = df[(df['call_entrant'] >= 0.002)]

    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))

    #portfolio_performance(df)
    #analysis(df)


def scen_3():
    df = get_cleaned_results()
    df = df[(df['put_vol_spread'] > 1)]
    df = df[(df['far_call_oi_share'] > 0.5)]
    df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def scen_4():
    df = get_cleaned_results()
    df = df[(df['roll_near_vol_pcr'] > 2)]
    #df = df[(df['roll_far_vol_pcr'] < 0.5)]
    df = df[(df['vol_rat'] > 1.5)]
    df = df[(df['day_put_profit'] > 0.1)]
    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def scen_5():
    df = get_cleaned_results()
    df = df[(df['roll_near_vol_pcr'] > 1)]
    df = df[(df['roll_far_vol_pcr'] < 0.5)]
    df = df[(df['vol_rat'] > 1.5)]
    df = df[(df['day_put_profit'] > 0.1)]
    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def scen_6():
    df = get_cleaned_results()
    df = df[(df['roll_near_vol_pcr'] > 1.5)]
    #df = df[(df['roll_far_vol_pcr'] < 0.5)]
    df = df[(df['vol_rat'] > 1.5)]
    df = df[(df['day_put_profit'] < -0.15)]
    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def scen_7():
    df = get_cleaned_results()
    #df = df[(df['roll_near_vol_pcr'] > 1.5)]
    #df = df[(df['roll_far_vol_pcr'] < 0.5)]
    df = df[(df['vol_rat'] > 1.5)]
    df = df[(df['day_put_profit'] < -0.4)]
    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def scen_8():
    df = get_cleaned_results()
    #df = df[(df['roll_near_vol_pcr'] > 1.5)]
    #df = df[(df['roll_far_vol_pcr'] < 0.5)]
    df = df[(df['vol_rat'] > 1.8)]
    df = df[(df['day_put_profit'] < -0.5)]
    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))


def param_search():
    time_df = load_time_results()
    param_search_result = parameter_grid_search.param_search(time_df, 'realized_pnl', 3, [])
    df_param_search = pd.DataFrame(param_search_result)
    #df_param_search.to_csv(reports_dir + 'option_market_impact_spot_param_search_4.csv')
    df_param_search.to_csv(reports_dir + 'option_market_impact_spot_at_low_param_search_3.csv')


def run():
    inflex_buffers = [12, 20, 30]
    time_df = load_time_results()
    time_df = get_cleaned_results(time_df)
    inflex_df = load_inflex_results()
    inflex_df = get_cleaned_results(inflex_df)
    descriptive_analysis_multi_dataset.perform_analysis_strategies_multi_df(time_df, inflex_df, 'realized_pnl', [], inflex_buffers=inflex_buffers)

    """
    pcr_minus_1 (-0.58, -0.37], (-0.31, -0.24], (0.03, 0.07], (-0.05, -0.01]
    day_put_profit (-0.34, -0.21], (-0.51, -0.34], (-1,-2)
    day call profit (0.17, 0.24], (0.24, 0.31], (0.31, 0.39], (0.39, 0.8]  (-0.01, 0.02], (0.02, 0.04]
    put_call_vol_scale_diff (-4.2, -0.56], (0.48, 4.55]
    (-0.56, -0.36], (0.31, 0.48]
    call_entrant (0.006, 0.008], (0.008, 0.013], (0.013, 0.096]

    put_entrant (-0.114, -0.006], (0.009, 0.014], (0.014, 0.29]
    far_put_oi_share (0.031, 0.196], (0.456, 0.622]
    near_call_oi_share (0.014, 0.119], (0.119, 0.131]
    far_call_oi_share (0.444, 0.626]
    far_put_volume_share_per_oi (0.929, 1.082] (1.082, 2.42] 
    """


def scen_01():
    inflex_buffer = 12
    #save_back_test_results()
    time_df = load_time_results()
    time_df = get_cleaned_results(time_df)
    inflex_df = load_inflex_results()
    inflex_df = get_cleaned_results(inflex_df)
    inflex_df['realized_pnl'] = inflex_df['realized_pnl'].apply(lambda x: x - inflex_buffer)

    time_df = time_df[(time_df['day_put_profit'] >= 0) & (time_df['day_put_profit'] < 0.2)]
    time_df = time_df[(time_df['day_call_profit'] < 0.02) & (time_df['day_call_profit'] >= -0.01)]

    inflex_df = inflex_df[(inflex_df['day_put_profit'] >= 0) & (inflex_df['day_put_profit'] < 0.2)]
    inflex_df = inflex_df[(inflex_df['day_call_profit'] < 0.02) & (inflex_df['day_call_profit'] >= -0.01)]


    print("******* Time DF *****")
    basic_statistics(time_df)
    print("******* Inflex DF *****")
    basic_statistics(inflex_df)
    global strat_days
    strat_days = strat_days.union(set(inflex_df['day'].to_list()))

def scen_02():
    inflex_buffer = 12
    #save_back_test_results()
    time_df = load_time_results()
    time_df = get_cleaned_results(time_df)
    inflex_df = load_inflex_results()
    inflex_df = get_cleaned_results(inflex_df)
    inflex_df['realized_pnl'] = inflex_df['realized_pnl'].apply(lambda x: x - inflex_buffer)
    inflex_df['return_pct'] = inflex_df['realized_pnl'] / inflex_df['entry_price']

    time_df = time_df[(time_df['pcr_minus_1'] >= -10) & (time_df['pcr_minus_1'] < -0.37)]
    time_df = time_df[(time_df['day_put_profit'] >= -10) & (time_df['day_put_profit'] < -0.99)]
    time_df = time_df[(time_df['far_put_oi_share'] < 0.196) & (time_df['far_put_oi_share'] >= 0)]

    inflex_df = inflex_df[(inflex_df['pcr_minus_1'] >= -10) & (inflex_df['pcr_minus_1'] < -0.37)]
    inflex_df = inflex_df[(inflex_df['day_put_profit'] >= -10) & (inflex_df['day_put_profit'] < -0.99)]
    inflex_df = inflex_df[(inflex_df['far_put_oi_share'] < 0.196) & (inflex_df['far_put_oi_share'] >= 0)]

    print("******* Time DF *****")
    basic_statistics(time_df)
    print("******* Inflex DF *****")
    basic_statistics(inflex_df)
    global strat_days
    strat_days = strat_days.union(set(inflex_df['day'].to_list()))


def scen_03():
    inflex_buffer = 12
    #save_back_test_results()
    time_df = load_time_results()
    time_df = get_cleaned_results(time_df)
    inflex_df = load_inflex_results()
    inflex_df = get_cleaned_results(inflex_df)
    inflex_df['realized_pnl'] = inflex_df['realized_pnl'].apply(lambda x: x - inflex_buffer)
    inflex_df['return_pct'] = inflex_df['realized_pnl'] / inflex_df['entry_price']

    time_df = time_df[(time_df['put_volume_scale'] >= 2.3) & (time_df['put_volume_scale'] < 50)]
    time_df = time_df[(time_df['put_call_vol_scale_diff'] >= 1.2) & (time_df['put_call_vol_scale_diff'] < 2)]
    time_df = time_df[(time_df['far_put_oi_share'] < 0.27) & (time_df['far_put_oi_share'] >= 0)]

    inflex_df = inflex_df[(inflex_df['put_volume_scale'] >= 2.3) & (inflex_df['put_volume_scale'] < 50)]
    inflex_df = inflex_df[(inflex_df['put_call_vol_scale_diff'] >= 1.2) & (inflex_df['put_call_vol_scale_diff'] < 2)]
    inflex_df = inflex_df[(inflex_df['far_put_oi_share'] < 0.27) & (inflex_df['far_put_oi_share'] >= 0)]

    print("******* Time DF Low analysis *****")
    basic_statistics(time_df)
    print("******* Inflex DF Low analysis *****")
    basic_statistics(inflex_df)
    global strat_days
    strat_days = strat_days.union(set(inflex_df['day'].to_list()))

def scenarios():
    print("===========")
    scen_03()

    print(strat_days)



"""
Notes : With the above analysis for trade every minute, 
1. both_covering and put_covering regime showed highest loss. 
This means when there is put covering loss is maximum

2. call_to_put_trans and put_to_call_trans shows best regimes 

"""