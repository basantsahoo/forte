#from backtest import strategy_back_tester
from backtest_2024.analysis import descriptive_analysis, classifier_train
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
def load_back_test_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = pd.read_csv(reports_dir + 'option_market_impact_spot_at_low.csv')
    return df


def create_drawdowns(equity_curve):
    """
    Calculate the largest peak-to-trough drawdown of the PnL curve
    as well as the duration of the drawdown. Requires that the
    pnl_returns is a pandas Series.

    Parameters:
    pnl - A pandas Series representing period percentage returns.

    Returns:
    drawdown, duration - Highest peak-to-trough drawdown and duration.
    """

    # Calculate the cumulative returns curve
    # and set up the High Water Mark
    # Then create the drawdown and duration series
    hwm = [0]
    eq_idx = equity_curve.index
    drawdown = pd.Series(index = eq_idx)
    duration = pd.Series(index = eq_idx)

    # Loop over the index range
    for t in range(1, len(eq_idx)):
        cur_hwm = max(hwm[t-1], equity_curve[t])
        hwm.append(cur_hwm)
        drawdown[t]= hwm[t] - equity_curve[t]
        duration[t]= 0 if drawdown[t] == 0 else duration[t-1] + 1
    return drawdown.max(), duration.max()


def plot_curve(df):
    periods = 252  # days
    sharpe_ratio = np.sqrt(periods) * (np.mean(df['return'])) / np.std(df['return'])
    print('sharpe_ratio ++++', sharpe_ratio)
    drawdown = create_drawdowns(df['equity_curve'])

    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(df.index, df['close'])
    plt.ylabel('close price')
    plt.xlabel("day")
    plt.xticks(rotation=90)
    ax2 = ax.twinx()
    # make a plot with different y-axis using second axis object
    ax2.plot(df.index, df['equity_curve'], color="red", marker="o", markersize=2)
    ax2.set_ylabel("equity", color="red", fontsize=14)

    plt.title("Equity curve")
    plt.text(0.6, 1.1, 'sharpe ratio = ' + str(sharpe_ratio), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'Max drawdown = ' + str(drawdown[0]), transform=ax.transAxes)
    plt.text(0.01, 1.1, 'Max drawdown period = ' + str(drawdown[1]), transform=ax.transAxes)
    plt.show()


def portfolio_performance(df):
    print('portfolio_performance=================================================')
    df = df[['day', 'entry_price', 'realized_pnl']].copy()
    df_1 = df.groupby(['day']).agg({'realized_pnl': ['sum'], 'entry_price':['mean']}).reset_index()
    df_1.columns = ['day', 'realized_pnl', 'close']
    df = df_1
    df['return'] = df['realized_pnl'] / df['close']
    df['cum_return'] = df['return'].cumsum()
    df['equity_curve'] = (1.0 + df['cum_return'])
    df.set_index('day', inplace=True)
    #print(df)
    periods = 252 #days
    sharpe_ratio = np.sqrt(periods) * (np.mean(df['return'])) / np.std(df['return'])
    print('sharpe_ratio ===========================================================', sharpe_ratio)
    plot_curve(df)


def basic_statistics(df):
    print("Total no of days pattern matched ====", len(df['day'].unique()))
    print("Total no of  pattern matched ====", len(df['entry_time'].unique()))
    print("Trades per day", len(df['entry_time'].unique())/len(df['day'].unique()))
    print("Avg Return", np.mean(df['return_pct'].to_list()))
    print("Total Return", np.sum(df['return_pct'].to_list()))
    print("Accuracy", len(df[df['return_pct'] > 0])/len(df['return_pct']))

def get_cleaned_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = load_back_test_results()
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
            'pattern_location'
    ]
    min_buffer = 20
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
    descriptive_analysis.perform_analysis_strategies(df, 'return_pct', exclude_vars_in_analysis)

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

def scen_2():

    #save_back_test_results()

    df = get_cleaned_results()
    #df =  df[(df['pcr_minus_1'] <= -0.25) | (df['pcr_minus_1'] >= 1.25)]
    df = df[(df['pcr_minus_1'] > -0.25) & (df['pcr_minus_1'] < 1.25)]
    #df = df[df['regime'].isin(['put_to_call_trans', 'call_buildup', 'put_covering'])]
    #df = df[(df['call_entrant'] > 0)]
    #df = df[(df['put_pos_price_pct'] >= 0.505)]
    df = df[(df['far_put_volume_share_per_oi'] >= 0.9)]
    df = df[(df['put_call_vol_scale_diff'] >= 0.7)]
    df = df[(df['put_volume_scale'] >= 2)]
    df = df[(df['vol_rat'] > 1.5)]
    basic_statistics(df)
    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))

    #portfolio_performance(df)
    #analysis(df)

def scen_1():

    #save_back_test_results()

    df = get_cleaned_results()
    df =  df[(df['pcr_minus_1'] <= -0.25) | (df['pcr_minus_1'] >= 1.25)]
    df = df[df['regime'].isin([ 'call_buildup', 'put_covering'])] #Factor 2 works in presence of factor 1
    df = df[(df['call_entrant'] > 0.0)] #0.009 for call scenario check
    df = df[(df['put_pos_price_pct'] >= 0.505)]
    df = df[(df['far_put_volume_share_per_oi'] >= 1.1)] #Factor 1 works in all scenario
    df = df[(df['vol_rat'] > 1)]
    #df = df[(df['put_call_vol_scale_diff'] >= 0)]
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

"""
def create_hyperparams_grid(X,y):
    graph_x = []
    graph_y = []
    graph_z = []
    for alpha_value in np.arange(-5.0,2.0,0.7):
        alpha_value = pow(10,alpha_value)
        graph_x_row = []
        graph_y_row = []
        graph_z_row = []
        for gamma_value in np.arange(0.0,20,2):
            hyperparams = (alpha_value,gamma_value)
            rmse = KRR_function(hyperparams,X,y)
            graph_x_row.append(alpha_value)
            graph_y_row.append(gamma_value)
            graph_z_row.append(rmse)
        graph_x.append(graph_x_row)
        graph_y.append(graph_y_row)
        graph_z.append(graph_z_row)
        print('')
    graph_x=np.array(graph_x)
    graph_y=np.array(graph_y)
    graph_z=np.array(graph_z)
    min_z = np.min(graph_z)
    pos_min_z = np.argwhere(graph_z == np.min(graph_z))[0]
    print('Minimum RMSE: %.4f' %(min_z))
    print('Optimum alpha: %f' %(graph_x[pos_min_z[0],pos_min_z[1]]))
    print('Optimum gamma: %f' %(graph_y[pos_min_z[0],pos_min_z[1]]))
    return graph_x,graph_y,graph_z
"""

def run():
    df = get_cleaned_results()
    df.to_csv(reports_dir + 'option_market_impact_spot_at_low_analysis.csv')
    #descriptive_analysis.perform_analysis_strategies(df, 'realized_pnl', [])
    """
    param_search_result = descriptive_analysis.param_search(df, 'realized_pnl', 3, [])
    df_param_search = pd.DataFrame(param_search_result)
    #df_param_search.to_csv(reports_dir + 'option_market_impact_spot_param_search_4.csv')
    df_param_search.to_csv(reports_dir + 'option_market_impact_spot_at_low_param_search_3.csv')
    """
    #df = df[(df['roll_near_vol_pcr'] > 1.5)]
    #df = df[(df['roll_far_vol_pcr'] < 0.5)]
    #df = df[(df['pcr_minus_1'] > -0.25) & (df['pcr_minus_1'] < 1.25)]
    #df = df[(df['vol_rat'] > 1.8)]
    #df = df[(df['day_put_profit'] > 0.8)]
    basic_statistics(df)

    #df = df[(df['far_put_volume_share_per_oi'] >= 1.1)]

    global strat_days
    strat_days = strat_days.union(set(df['day'].to_list()))
    basic_statistics(df)


    scen_1()
    scen_2()
    scen_3()
    scen_4()
    scen_5()
    scen_6()
    scen_7()
    scen_8()
    print(strat_days)




"""
Notes : With the above analysis for trade every minute, 
1. both_covering and put_covering regime showed highest loss. 
This means when there is put covering loss is maximum

2. call_to_put_trans and put_to_call_trans shows best regimes 

"""