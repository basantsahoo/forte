#from strategies_bkp.sma_cross_over_buy import SMACrossBuy
#from strategies_bkp.range_break import RangeBreakDownStrategy
#from backtest import strategy_back_tester
from backtest_2024.analysis import classifier_train
import pandas as pd
import numpy as np
from settings import reports_dir
import matplotlib.pyplot as plt



def load_back_test_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = pd.read_csv(reports_dir + 'Patt_Cand_NIFTY_2022-04-29_2021-09-22.csv') # index_col=0
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
    print("=================================================Basic Statictics=================================================")
    total_days = len(df['day'].unique())
    print("Total no of days pattern matched ====", total_days)
    print("Total no of  strategy matched ====", len(df['strategy'].unique()))
    unique_strategies = df['strategy'].unique()
    core_strategies = list(set([strategy.split("_")[0] for strategy in unique_strategies]))
    print("Total no of  core strategy matched ====", len(core_strategies))
    print("Trades per day", len(df['entry_time'].unique()) / len(df['day'].unique()))
    strategy_df = df.groupby(['strategy']).agg({'realized_pnl': ['count', 'mean', 'min', 'max', 'std']}).reset_index()
    strategy_df.columns = ['strategy', 'count', 'mean', 'min', 'max', 'std']
    strategy_df = strategy_df.sort_values(by=['mean', 'count'], ascending=[False, False], na_position='first')
    filtered_df = strategy_df[(strategy_df['count'] >= total_days * 0.2)].reset_index()
    return df[df['strategy'].isin(filtered_df['strategy'].to_list())]
    #print(filtered_df.to_string())

def get_cleaned_results():
    df = load_back_test_results()
    print('total no of records =', df.shape[0])
    print('records count by trigger')
    print(df.groupby(['trigger']).agg({'realized_pnl': ['count']}))
    drop_cols = [ 'exit_time', 'exit_price', 'seq', 'target', 'stop_loss', 'quantity', 'neck_point', 'exit_type','closed', 'pattern_time',	'pattern_price', 'duration', 'entry_time_read']
    df.drop(drop_cols, axis=1, inplace=True)
    df['realized_pnl'] = df['realized_pnl'] + df['un_realized_pnl']
    del df['un_realized_pnl']
    print('Basic analysis of P & L by signal ====================================')
    common_cols = ['day', 'symbol', 'strategy', 'signal_id', 'entry_time']
    df_1_cols = ['realized_pnl']
    df_1 = df[common_cols + df_1_cols]
    df_1 = df_1.groupby(common_cols).agg({'realized_pnl': ['sum']}).reset_index()
    df_1.columns = common_cols + df_1_cols
    print('total strategy signals ', df_1.shape[0])
    exlcude_columns = ['trigger']
    df_2_cols = [x for x in df.columns if x not in common_cols and x not in df_1_cols and x not in exlcude_columns]
    df_2 = df[common_cols + df_2_cols]
    df_2.drop_duplicates(inplace=True)
    final_df = pd.merge(df_1, df_2, how='left', left_on=common_cols, right_on=common_cols)
    print('final df shape is ', final_df.shape)
    return final_df

def do_analysis(df, strategies):
    df['infl_dir'] = df['infl_n'] - df['infl_0']
    df['infl_dir'] = df['infl_dir'].apply(lambda x: int(x > 0))
    # 'resistance_ind',	'support_ind'

    exclude_vars = ['day', 'symbol', 'signal_id', 'trigger', 'entry_time', 'infl_0', 'infl_n', 'entry_price', ]
    print('going to describe')
    #descriptive_analysis.perform_analysis_strategies(df.copy(), 'realized_pnl', exclude_vars)


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
        try:
            print('classification for ================== ', strategy)
            # if strategy == 'CDLXSIDEGAP3METHODS_5_BUY_30':
            df_tmp = df[df['strategy'] == strategy] #[imp_vars_4 + ['realized_pnl']]
            #print(df_tmp.columns.to_list())
            classifier_train.train(df_tmp, 'realized_pnl', exclude_vars)
            data_set = df[df['strategy'] == strategy][imp_vars + ['realized_pnl']].copy()
            del data_set['week_day']
            correlations = data_set.corr(method='pearson')
            #correlations.to_csv('corr.csv')
        except:
            pass
        # print(correlations)




def run():
    df = get_cleaned_results()
    filtered_strategies = basic_statistics(df)
    do_analysis(filtered_strategies, 'aa')
