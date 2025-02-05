#from backtest import strategy_back_tester
from research.analysis import classifier_train
from research.analysis import regression_train
from research.analysis import descriptive_analysis
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
    df = pd.read_csv(reports_dir + 'Frid_Frid_Frid_NIFTY_2022-12-23_2022-04-07.csv')
    #'Cand_NIFTY_2022-12-28_2022-08-03 copy.csv'
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
    print(df)
    periods = 252 #days
    sharpe_ratio = np.sqrt(periods) * (np.mean(df['return'])) / np.std(df['return'])
    print('sharpe_ratio ===========================================================', sharpe_ratio)
    plot_curve(df)


def basic_statistics(df):
    print("Total no of days pattern matched ====", len(df['day'].unique()))
    print("Total no of  pattern matched ====", len(df['entry_time'].unique()))
    print("Trades per day", len(df['entry_time'].unique())/len(df['day'].unique()))

def get_cleaned_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = load_back_test_results()
    drop_cols = ['Unnamed: 0', 'exit_time', 'exit_price', 'seq', 'target', 'stop_loss', 'quantity', 'neck_point', 'exit_type','closed', 'pattern_time',	'pattern_price', 'duration', 'entry_time_read']
    for col in drop_cols:
        try:
            df.drop(col, axis=1, inplace=True)
        except:
            pass
    df['realized_pnl'] = df['realized_pnl'] + df['un_realized_pnl']
    del df['un_realized_pnl']
    print('Basic analysis of P & L by trigger ====================================')
    print(df.groupby(['strategy', 'trigger']).agg({'realized_pnl': ['count', 'mean', 'min', 'max']}))

    df['trigger'] = df['trigger'].apply(lambda x: 1 if x == 2 else x)
    common_cols = ['day', 'symbol', 'strategy', 'signal_id', 'trigger', 'entry_time']
    df_1_cols = ['realized_pnl']
    df_1 = df[common_cols + df_1_cols]
    df_1 = df_1.groupby(common_cols).agg({'realized_pnl': ['sum']}).reset_index()
    df_1.columns = common_cols + df_1_cols
    #print(df_1)
    df_2_cols = [x for x in df.columns if x not in common_cols and x not in df_1_cols]
    df_2 = df[common_cols + df_2_cols]

    df_2.drop_duplicates(inplace=True)

    print(df_2.shape)
    print(df_1.shape)
    final_df = pd.merge(df_1, df_2, how='left', left_on=common_cols, right_on=common_cols)
    print(final_df.shape)
    #print(final_df.tail().T.to_string())

    #final_df = final_df[(final_df['static_ratio'] > 0.165) & (final_df['mu_n'] > 0.295)]

    return final_df

def analysis(df):
    df['infl_dir'] = df['infl_n'] - df['infl_0']
    df['infl_dir'] = df['infl_dir'].apply(lambda x: int(x > 0))
    # 'resistance_ind',	'support_ind'

    exclude_vars = ['day', 'symbol', 'signal_id', 'trigger', 'entry_time', 'infl_0', 'infl_n', 'entry_price', ]
    print('going to describe')
    descriptive_analysis.perform_analysis_strategies(df, 'realized_pnl', exclude_vars)

    exclude_vars = ['day', 'symbol', 'signal_id', 'strategy', 'entry_time', 'infl_0', 'infl_n', 'entry_price', 'trigger_time']
    imp_vars = ['dist_frm_level', 'mu_0', 'pattern_height', 'lw_total_energy_pyr', 'lw_d_en_ht', 'lw_d_en_pyr',
                'five_min_trend', 'tpo', 'static_ratio', 'dynamic_ratio', 's_en_pyr', 'd_en_ht', 'open_type',
                'd_en_pyr', 's_en_ht', 'pattern_location', 'lw_total_energy_ht', 'candles_in_range',
                'five_min_ex_first_hr_trend', 'lw_s_en_pyr', 'support_ind', 'total_energy_pyr', 'resistance_ind',
                'first_hour_trend', 'total_energy', 'w_S1', 'fifteen_min_trend', 'lw_static_ratio', 'lw_s_en_ht',
                'total_energy_ht', 'whole_day_trend', 'infl_dir', 'exp_c', 'ret_trend', 'hurst_exp_15', 'quad',
                'lw_dynamic_ratio', 'hurst_exp_5', 'pattern_lin', 'fifteen_min_ex_first_hr_trend', 'market_auc',
                'pattern_lin_r2', 'pattern_trend_auc', 'mu_n', 'week_day']
    # imp_vars_2 = ['dist_frm_level',	'mu_0',	'pattern_height',	'lw_total_energy_ht',	'five_min_trend',	'tpo',	'static_ratio',	'dynamic_ratio',	'pattern_location',	'candles_in_range',	'support_ind',	'total_energy_ht',	'resistance_ind',	'first_hour_trend',	'w_S1',	'infl_dir',	'exp_c',	'y_high',	'y_low',	'y_va_h_p',	'y_va_l_p',	'y_poc_price',	'w_high',	'w_low',	'w_Pivot',	'w_R1',	'w_S1',	'w_R2',	'w_S2',	'w_R3',	'w_S3', 'week_day', 'open_type']
    imp_vars_2 = ['dist_frm_level', 'mu_0', 'pattern_height', 'lw_total_energy_ht', 'tpo', 'five_min_trend',
                  'pattern_location', 'candles_in_range', 'support_ind', 'total_energy_ht', 'resistance_ind',
                  'first_hour_trend', 'w_S1', 'infl_dir', 'exp_c', 'y_high',
                  'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price', 'w_high', 'w_low', 'w_Pivot', 'week_day', 'open_type']

    # Analyse weekly levels separately
    wk = ['w_high', 'w_low', 'w_Pivot', 'w_R1', 'w_S1', 'w_R2', 'w_S2', 'w_R3', 'w_S3', ]
    r = ['static_ratio', 'dynamic_ratio', 'pattern_location', 'candles_in_range', 'support_ind',
         'total_energy_ht', 'resistance_ind', 'first_hour_trend', 'w_S1', 'infl_dir', 'exp_c', 'y_high',
         'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price', 'w_high', 'w_low', 'w_Pivot', 'w_R1', 'w_S1', 'w_R2',
         'w_S2', 'w_R3', 'w_S3', 'week_day', 'open_type']
    imp_vars_3 = ['mu_0', 'w_S1', 'y_high', 'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price', 'w_high', 'w_Pivot',
                  'week_day']
    imp_vars_3 = ['mu_0', 'w_S1', 'y_high', 'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price', 'w_high', 'w_Pivot',
                  'week_day', 'open_type']
    imp_vars_4 = ['static_ratio', 'd_en_pyr', 'candles_in_range', 'dist_frm_level',
                  'support_ind', 'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price',
                  'w_S1', 'w_S2', 'pattern_location',
                  'lw_total_energy_ht', 'auc_del', 'mu_n', 'open_type', 'week_day']
    strategies = df['strategy'].unique()
    root_strategies = set([x.split("_")[0] for x in strategies])
    print('total patterns matched___', len(list(root_strategies)))

    for strategy in strategies:
        print('classification for ================== ', strategy)
        # if strategy == 'CDLXSIDEGAP3METHODS_5_BUY_30':
        df_tmp = df[df['strategy'] == strategy] #[imp_vars_4 + ['realized_pnl']]
        print(df_tmp.columns.to_list())
        classifier_train.train(df_tmp, 'realized_pnl', exclude_vars)
        data_set = df[df['strategy'] == strategy][imp_vars + ['realized_pnl']].copy()
        del data_set['week_day']
        correlations = data_set.corr(method='pearson')
        correlations.to_csv('corr.csv')
        # print(correlations)

    # five_min_trend > -0.075 and pattern_auc_del <= 0.001 and market_auc <= 0.455 and ret_trend > 0.905 and hurst_exp_15 > -1.08
    """
    -- perform descriptive -- requires strategy variable to be included
    df = load_back_test_results()
    df['infl_dir'] = df['infl_n'] - df['infl_0']
    df['infl_dir'] = df['infl_dir'].apply(lambda x : int(x > 0))
    # 'resistance_ind',	'support_ind'
    exclude_vars = ['day',	'symbol', 	'trigger',	'infl_0',	'infl_n','Unnamed: 0','un_realized_pnl', 'entry_time', 'exit_time']
    descriptive_analysis.perform_analysis_strategies(df, 'realized_pnl', exclude_vars)
    """
    """
    -- perform classification
    df = load_back_test_results()
    df['infl_dir'] = df['infl_n'] - df['infl_0']
    df['infl_dir'] = df['infl_dir'].apply(lambda x : int(x > 0))
    # 'resistance_ind',	'support_ind'
    exclude_vars = ['day',	'symbol', 	'strategy', 'trigger',	'infl_0',	'infl_n','Unnamed: 0','un_realized_pnl', 'entry_time', 'exit_time']
    strategies = df['strategy'].unique()
    for strategy in strategies:
        print(strategy)
        #if strategy == 'CDLXSIDEGAP3METHODS_5_BUY_30':
        df_tmp = df[df['strategy'] == strategy]
        classifier_train.train(df_tmp, 'realized_pnl', exclude_vars)

    """
    """

    for strategy in strategies:
        print(strategy, "++++++++++++++++++++++++++++++++")
        df_tmp = df[df['strategy'] == strategy]
        regression_train.train(df_tmp, 'realized_pnl', exclude_vars)
    """

    # tier -1
    # CDL3OUTSIDE_5_BUY_15 - 0.67
    # CDL3OUTSIDE_5_BUY_20 - 0.71
    # CDL3OUTSIDE_5_BUY_30 - 0.77
    # CDL3OUTSIDE_5_SELL_20 - 0.73
    # CDL3OUTSIDE_15_SELL_30 - 0.64
    # CDLXSIDEGAP3METHODS_5_BUY_15 - 0.72
    # CDLXSIDEGAP3METHODS_5_BUY_30 - 0.85

    # tier -2
    # CDLENGULFING_15_BUY_15 - 0.52
    # CDLENGULFING_5_SELL_20 - 0.78
    # CDLENGULFING_5_SELL_30 - 0.80
    # CDL3OUTSIDE_5_SELL_30  - 0.73
    # CDL3OUTSIDE_15_SELL_15 - 0.42
    # CDL3OUTSIDE_15_BUY_10  - 0.42
    # classifier_train.train(df, 'realized_pnl', exclude_vars)


def run():

    #save_back_test_results()

    df = get_cleaned_results()
    basic_statistics(df)
    #portfolio_performance(df)
    analysis(df)

