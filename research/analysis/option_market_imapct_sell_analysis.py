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
def load_time_results(regime):
    df = pd.read_csv(reports_dir + 'Inflex_analysis/low_inflex/' + regime + '/option_market_impact_spot_sell.csv')
    return df

def load_inflex_results(regime):
    df = pd.read_csv(reports_dir + 'Inflex_analysis/low_inflex/' + regime + '/option_market_impact_spot_at_low.csv')
    return df



def basic_statistics(df):
    print("Total no of days pattern matched ====", len(df['day'].unique()))
    print("Total no of  pattern matched ====", len(df['entry_time'].unique()))
    print("Trades per day", len(df['entry_time'].unique())/len(df['day'].unique()))
    print("Avg Return", np.mean(df['return_pct'].to_list()))
    print("Total Return", np.sum(df['return_pct'].to_list()))
    print("Avg P&L Value", np.mean(df['realized_pnl'].to_list()))
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


strat_days = set()


def param_search():
    time_df = load_time_results('range_bound_market')
    param_search_result = parameter_grid_search.param_search(time_df, 'realized_pnl', 3, [])
    df_param_search = pd.DataFrame(param_search_result)
    #df_param_search.to_csv(reports_dir + 'option_market_impact_spot_param_search_4.csv')
    df_param_search.to_csv(reports_dir + 'option_market_impact_spot_at_low_param_search_3.csv')


def run():
    inflex_buffers = [13, 20, 30]
    time_df = load_time_results('range_bound_market')
    time_df = get_cleaned_results(time_df)
    inflex_df = load_inflex_results('range_bound_market')
    inflex_df = get_cleaned_results(inflex_df)
    descriptive_analysis_multi_dataset.perform_analysis_strategies_multi_df(time_df, inflex_df, 'realized_pnl', [], inflex_buffers=inflex_buffers)

    """
    near_put_oi_share < 0.043  (Shows variation in different markets)
    far_put_oi_share < 0.306   (This works but target must be adjusted for different markets)
    near_call_oi_share > 0.098 (Shows variation in different markets)
    far_call_oi_share > 0.445  (This works but target must be adjusted for different markets) 
    far_put_volume_share_per_oi > 0.846
    pcr_minus_1 < -0.37
    calc near pcr
    pattern_location < 12
    call_drop >  -0.12  (Shows variation in different markets)
    put_drop < -0.15
    r_near_put_volume_per_oi  > 0.13
    r_far_put_volume_per_oi > 0.04
    r_near_call_volume_per_oi > 0.1
    r_far_call_volume_per_oi > 0.047
    r_total_call_volume_per_oi > 0.05
    r_total_put_volume_per_oi > 0.05
    r_call_vol_spread > 0.06
    r_put_vol_spread > 0.07
    near_vol_pcr < 0.52 or > 2.6
    far_vol_pcr < 0.63 (Shows variation in different markets)    
    """



def scen_02():
    inflex_buffer = 12
    #save_back_test_results()
    regimes = ['bear_market', 'bull_market', 'range_bound_market']
    for regime in regimes:
        print("=================== ", regime, " ======================")
        time_df = load_time_results(regime)
        time_df = get_cleaned_results(time_df)
        inflex_df = load_inflex_results(regime)
        inflex_df = get_cleaned_results(inflex_df)
        inflex_df['realized_pnl'] = inflex_df['realized_pnl'].apply(lambda x: x - inflex_buffer)
        inflex_df['return_pct'] = inflex_df['realized_pnl'] / inflex_df['entry_price']

        time_df = time_df[(time_df['r_near_put_volume_per_oi'] >= 0.13) & (time_df['r_near_put_volume_per_oi'] < 100)]
        time_df = time_df[(time_df['r_far_put_volume_per_oi'] >= 0.04) & (time_df['r_far_put_volume_per_oi'] < 100)]
        time_df = time_df[(time_df['r_near_call_volume_per_oi'] >= 0.1) & (time_df['r_far_put_volume_per_oi'] < 100)]
        time_df = time_df[(time_df['r_far_call_volume_per_oi'] >= 0.047) & (time_df['r_far_call_volume_per_oi'] < 100)]
        time_df = time_df[(time_df['r_put_vol_spread'] >= 0.07) & (time_df['r_put_vol_spread'] < 100)]
        time_df = time_df[(time_df['r_call_vol_spread'] >= 0.06) & (time_df['r_call_vol_spread'] < 100)]
        time_df = time_df[(time_df['near_vol_pcr'] >= 2.5) & (time_df['near_vol_pcr'] < 100)] # Key filter
        time_df = time_df[(time_df['pattern_location'] <= 12) & (time_df['pattern_location'] > 0)]

        inflex_df = inflex_df[(inflex_df['r_near_put_volume_per_oi'] >= 0.13) & (inflex_df['r_near_put_volume_per_oi'] < 100)]
        inflex_df = inflex_df[(inflex_df['r_far_put_volume_per_oi'] >= 0.04) & (inflex_df['r_far_put_volume_per_oi'] < 100)]
        inflex_df = inflex_df[(inflex_df['r_near_call_volume_per_oi'] >= 0.1) & (inflex_df['r_far_put_volume_per_oi'] < 100)]
        inflex_df = inflex_df[(inflex_df['r_far_call_volume_per_oi'] >= 0.047) & (inflex_df['r_far_call_volume_per_oi'] < 100)]
        inflex_df = inflex_df[(inflex_df['r_call_vol_spread'] >= 0.06) & (inflex_df['r_call_vol_spread'] < 100)]
        inflex_df = inflex_df[(inflex_df['r_put_vol_spread'] >= 0.07) & (inflex_df['r_put_vol_spread'] < 100)]
        inflex_df = inflex_df[(inflex_df['near_vol_pcr'] >= 2.5) & (inflex_df['near_vol_pcr'] < 100)] # Key filter
        inflex_df = inflex_df[(inflex_df['pattern_location'] <= 12) & (inflex_df['pattern_location'] > 0)]

        print("******* Time DF *****")
        basic_statistics(time_df)
        print("******* Inflex DF *****")
        basic_statistics(inflex_df)
        global strat_days
        strat_days = strat_days.union(set(inflex_df['day'].to_list()))

def scen_01():
    inflex_buffer = 12
    #save_back_test_results()
    regimes = ['bear_market', 'bull_market', 'range_bound_market']
    for regime in regimes:
        print("=================== ", regime, " ======================")
        time_df = load_time_results(regime)
        time_df = get_cleaned_results(time_df)
        inflex_df = load_inflex_results(regime)
        inflex_df = get_cleaned_results(inflex_df)
        inflex_df['realized_pnl'] = inflex_df['realized_pnl'].apply(lambda x: x - inflex_buffer)
        inflex_df['return_pct'] = inflex_df['realized_pnl'] / inflex_df['entry_price']

        time_df = time_df[(time_df['r_total_vol_pcr'] >= 1.5) & (time_df['r_total_vol_pcr'] < 100)] # Key filter
        time_df = time_df[(time_df['pattern_location'] <= 5) & (time_df['pattern_location'] > 0)]

        inflex_df = inflex_df[(inflex_df['r_total_vol_pcr'] >= 1.5) & (inflex_df['r_total_vol_pcr'] < 100)] # Key filter
        inflex_df = inflex_df[(inflex_df['pattern_location'] <= 5) & (inflex_df['pattern_location'] > 0)]

        print("******* Time DF *****")
        basic_statistics(time_df)
        print("******* Inflex DF *****")
        basic_statistics(inflex_df)
        global strat_days
        strat_days = strat_days.union(set(inflex_df['day'].to_list()))


def scenarios():
    print("===========")
    scen_01()

    print(strat_days)



"""
Notes : With the above analysis for trade every minute, 
1. both_covering and put_covering regime showed highest loss. 
This means when there is put covering loss is maximum

2. call_to_put_trans and put_to_call_trans shows best regimes 

"""