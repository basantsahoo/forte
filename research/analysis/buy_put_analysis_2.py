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
    df = pd.read_csv(reports_dir + 'buy_put_option_on_volume.csv')
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
    drop_cols = ['Unnamed: 0', 'symbol', 'trade_id', 'leg', 'side', 'exit_time', 'exit_price',
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
            'dir_pos_price_pct',
            'dir_inv_neg_price_pct',
            'pattern_location'
    ]

    df = df[select_cols]
    df['realized_pnl'] = df['realized_pnl'] + df['un_realized_pnl']

    df['return_pct'] = df['realized_pnl']/df['entry_price']
    del df['un_realized_pnl']
    del df['realized_pnl']
    df = df[df['tpo'] < 13]
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

def run():

    #save_back_test_results()

    df = get_cleaned_results()
    df.to_csv(reports_dir + 'buy_put_option_on_volume_analysis.csv')
    basic_statistics(df)
    #portfolio_performance(df)
    analysis(df)

"""
Notes : With the above analysis for trade every minute, 
1. both_covering and put_covering regime showed highest loss. 
This means when there is put covering loss is maximum

2. call_to_put_trans and put_to_call_trans shows best regimes 

"""