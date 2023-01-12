from research.strategies.aggregators import CandleAggregator
from research.analysis import classifier_train
from research.analysis import regression_train
from research.analysis import descriptive_analysis
import pandas as pd
import numpy as np
from backtest.settings import reports_dir
import matplotlib.pyplot as plt


def load_back_test_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    #df = pd.read_csv(reports_dir + 'test1.csv')
    df = pd.read_csv(reports_dir + 'bkp_cheap_option.csv')
    df = df.sort_values(['entry_time', 'signal_id', 'trigger'], ascending=[True,True, True]).reset_index(drop=True)
    #print(df.head().T)

    #df = pd.read_csv(reports_dir + 'ddddd.csv')
    # 'Cand_NIFTY_2022-12-28_2022-08-03 copy.csv'
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
    plt.plot(df.index, df['spot'])
    plt.ylabel('spot price')
    plt.xlabel("day")
    plt.xticks(rotation=90)
    ax2 = ax.twinx()
    # make a plot with different y-axis using second axis object
    ax2.plot(df.index, df['equity_curve'], color="red", marker="o", markersize=2)
    ax2.set_ylabel("equity", color="red", fontsize=14)

    plt.title("Equity curve")
    plt.text(0.6, 1.1, 'sharpe ratio = ' + str(round(sharpe_ratio,2)), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'Max drawdown = ' + str(round(drawdown[0]*100, 2)) + "%", transform=ax.transAxes)
    plt.text(0.01, 1.1, 'Max drawdown period = ' + str(drawdown[1]), transform=ax.transAxes)
    plt.show()

    df['daily_return'] = df['spot'].pct_change()
    correl = df[['daily_return', 'return']].corr(method='pearson')
    print('correllation with index============', correl)


def portfolio_performance(df, filter={}):
    for key, value in filter.items():
        df = df[df[key] == value]
    print('portfolio_performance=================================================')
    df = df[['day', 'spot', 'entry_price', 'realized_pnl']].copy()
    df_1 = df.groupby(['day']).agg({'realized_pnl': ['sum'], 'spot':['mean'], 'entry_price':['sum']}).reset_index()
    df_1.columns = ['day', 'realized_pnl', 'spot', 'premium']
    df = df_1
    df['return'] = df['realized_pnl'] / df['premium']
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
    print("Premium earned", df['realized_pnl'].sum())

def get_cleaned_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = load_back_test_results()
    df['realized_pnl'] = df['realized_pnl'] + df['un_realized_pnl']
    df['target_pct'] = df['target']/df['entry_price'] -1
    df['pnl_pct'] = df['realized_pnl'] / df['entry_price']
    df['stop_loss_pct'] = 1 - df['stop_loss'] / df['entry_price']

    drop_cols = [ 'exit_time', 'exit_price','un_realized_pnl', 'seq', 'target', 'stop_loss', 'quantity', 'neck_point', 'exit_type', 'closed', 'pattern_time',	'pattern_price', 'duration', 'entry_time_read']
    for col in drop_cols:
        try:
            df.drop(col, axis=1, inplace=True)
        except:
            pass
    print('Basic analysis of P & L by trigger ====================================')
    #print(df.groupby(['strategy', 'trigger']).agg({'realized_pnl': ['count', 'mean', 'min', 'max']}))

    #df['trigger'] = df['trigger'].apply(lambda x: 1 if x == 2 else x)
    common_cols = ['day', 'symbol', 'strategy', 'signal_id', 'trigger', 'entry_time']
    df_1_cols = ['realized_pnl']
    df_1 = df[common_cols + df_1_cols]
    df_1 = df_1.groupby(common_cols).agg({'realized_pnl': ['sum']}).reset_index()
    df_1.columns = common_cols + df_1_cols
    #print(df_1)
    df_2_cols = [x for x in df.columns if x not in common_cols and x not in df_1_cols]
    df_2 = df[common_cols + df_2_cols]

    df_2.drop_duplicates(inplace=True)
    #print(df_1.shape)
    final_df = pd.merge(df_1, df_2, how='left', left_on=common_cols, right_on=common_cols)
    final_df = final_df.sort_values(['entry_time', 'signal_id', 'trigger'], ascending=[True, True, True]).reset_index(drop=True)
    #print(final_df)
    #print(final_df.columns.to_list())
    #print(final_df.shape)
    #print(final_df.tail().T.to_string())

    #final_df = final_df[(final_df['static_ratio'] > 0.165) & (final_df['mu_n'] > 0.295)]

    return final_df

def analysis(df):
    #df['infl_dir'] = df['infl_n'] - df['infl_0']
    #df['infl_dir'] = df['infl_dir'].apply(lambda x: int(x > 0))
    # 'resistance_ind',	'support_ind'

    da_exclude_vars = ['symbol', 'signal_id', 'trigger', 'entry_time', 'infl_0', 'infl_n', 'entry_price', ]
    print('going to describe')
    train_size = int(df.shape[0] * 0.66)
    df_train = df[0:train_size]
    #print(df_train)
    descriptive_analysis.perform_analysis_strategies(df_train, 'pnl_pct', da_exclude_vars)
    non_features = ['day','pnl_pct', 'symbol', 'signal_id', 'strategy','entry_price', 'entry_time', 'infl_0', 'infl_n', 'entry_price', 'trigger_time', 'trigger', 'side', 'instrument', 'strike']
    imp_features1 = ['week_day', 'money_ness', 'tpo','open_type', 'strength', 'd2_cd_new_business_pressure', 'd2_cd_support_pressure', 'lc_dist_frm_level', 'total_energy', 'five_min_trend', 'dynamic_ratio' , 'total_energy_pyr',	'kind',	'd_en_ht',	'total_energy_ht']
    imp_features = ['week_day', 'candles_in_range',	'd_t_2_high',	'd_t_2_low',	'd_t_2_poc_price',	'd_t_2_va_h_p',	'd_t_2_va_l_p',	'd_y_high',	'd_y_low',	'd_y_poc_price',	'd_y_va_h_p',	'd_y_va_l_p',	'd2_ad_high',	'd2_ad_low',	'd2_ad_new_business_pressure',	'd2_ad_poc_price',	'd2_ad_resistance_pressure',	'd2_ad_retest_fract',	'd2_ad_support_pressure',	'd2_ad_type',	'd2_ad_va_h_p',	'd2_ad_va_l_p',	'd2_cd_close_rat',	'd2_cd_new_business_pressure',	'd2_cd_resistance_pressure',	'd2_cd_retest_fract',	'd2_cd_support_pressure',	'd2_cd_type',	'd2_gap',	'lc_dist_frm_level',	'lc_resistance_ind',	'lc_support_ind',	'lc_t_2_high',	'lc_t_2_low',	'lc_t_2_poc_price',	'lc_t_2_va_h_p',	'lc_t_2_va_l_p',	'lc_w_high',	'lc_w_low',	'lc_w_Pivot',	'lc_w_R1',	'lc_w_R2',	'lc_w_R3',	'lc_w_S1',	'lc_w_S2',	'lc_w_S3',	'lc_y_high',	'lc_y_low',	'lc_y_poc_price',	'lc_y_va_h_p',	'lc_y_va_l_p',	'open_type',	'pat_t_2_high',	'pat_t_2_low',	'pat_t_2_poc_price',	'pat_t_2_va_h_p',	'pat_t_2_va_l_p',	'pat_w_high',	'pat_w_low',	'pat_w_Pivot',	'pat_w_R1',	'pat_w_R2',	'pat_w_R3',	'pat_w_S1',	'pat_w_S2',	'pat_w_S3',	'pat_y_high',	'pat_y_low',	'pat_y_poc_price',	'pat_y_va_h_p',	'pat_y_va_l_p',	'strength']
    imp_features_2 = ['week_day', 'open_type', 'fifteen_min_trend',	'exp_c',	'five_min_trend',	'whole_day_trend',	'trend_auc',	'mu_0',	'exp_b',	'market_auc',	'lc_dist_frm_level',	'lin',	'mu_n',	'auc_del',	'quad',	'strength',	'quad_r2',	'lin_r2']
    imp_features_3 = ['week_day', 'open_type', 'exp_b', 'five_min_trend', 'lc_dist_frm_level', 'd2_ad_resistance_pressure', 'd2_ad_support_pressure', 'd2_cd_new_business_pressure']
    strategies = ['OPTION_CHEAP_BUY'] #df['strategy'].unique()
    root_strategies = set([x.split("_")[0] for x in strategies])
    print('total patterns matched___', len(list(root_strategies)))

    for strategy in strategies:

        print('classification for ================== ', strategy)
        """
        df_tmp = df[df['strategy'] == strategy]
        df_tmp.replace([np.inf, -np.inf], np.nan, inplace=True)
        df_tmp.fillna(0, inplace=True)
        print(df_tmp.columns[df_tmp.isna().any()].tolist())

        #df_tmp = df_tmp[imp_features1 + ['realized_pnl']]
        #print(df_tmp.columns.to_list())
        classifier_train.train(df_tmp, 'realized_pnl', non_features)
        """


    """
    tpo : 8, 9, 10
    ABOVE_VA, BELOW_VA
    
    scen 1 : Monday, ABOVE_VA , (tpo 10 , call, srrength 50% looks better)
    scen 2 : Tuesday, BELOW_VA,INSIDE_VA , (tpo 9/10 , call,ITM_1 to 4, strength 40-50% looks better, strength 60% best no loss)
    scen 3 : Wednesday, ABOVE_VA,BELOW_VA,GAP_DOWN (tpo 1,2 & 8,9,10,11 , call/Put,ITM_1 to 3, & OTM 1,2 strength above 30% looks better)
    scen 4 : Thursday not good day
    Scen 5 : Friday, ABOVE_VA, tpo 1, PE, moneyness - doesn't look good strength also doesn't differentiate 
    
    wednesday looks best so far
    
    CE, BELOW_VA looks better
    PE, Wednesday, Friday, ABOVE_VA, tpo - 7 to 11 OTM-3 to ITM 3 looks fine strength 20-40 looks better >50 doesnt trade
    
    Open type
    =========
    Above VA (best) strength 20-30 % any moneyness , days other than Thursday, favours puts buys, tpo 8/9/10
    GAP UP DAYS are not good for buying 
    INSIDE VA tpo 10,11 Tuesday < 50% 
    INSIDE VA THURSDAY good for selling
    INSIDE VA > 50% good for selling 
    BELOW VA Wednesday best for buying , tpo 1, 3-6  CE, PE both , All moneyness strength 20% - 50% but % days very less
    GAP DOWN, Wednesday and Friday, tpo  3 -9 , CE , ITM 1- 3
    
    TPO
    ======
    1. Thursday good for selling (lot of trades)
    1. BELOW_VA good for buying,  20-50% good for selling analyse this again
    2. Very good for selling 
    3. Monday, Tuesday, Wednesday good for buying any open other than inside va, any moneyness, strength 30-40%
    4. Almost similar to 3 slight diff and less accurate 
    5. ignore
    6. more than 40% good for sell
    7. decent but very less return
    8. Monday and Gapup 
    9. other than Friday
    10. other than Friday ABOVE_VA, INSIDE_VA
    11. Other than Friday, ABOVE_VA, Inside VA OTMS
    
    Moneyness (This definition is not correct as they are determined by variable spot) we need to keep the fixed spot
    =========
    ITM_1 : Wednesday tpo 8-10
    ITM_2 : Wednesday tpo 2-5, strength 20-30
    
    Strength 
    ========
    20% : ABOVE_VA, BELOW VA, 6-10
    30% : Tuesday, Wednesday ABOVE_VA, BELOW_VA, 3-6
    40% : Tuesday, Wednesday BELOW_VA, 3-6
    50% : Thurday good for selling,  Monday Tuesday, Wednesday good for buying , BELOW_VA, 
    60% : ABOVE_VA, 
     
    """
    """
    Ananlysis 2
    overall
    -------
    Monday, Tuesday, Wednesday better that Thursday Friday
    BELOW_VA better than others 
    
    1,2 best for selling and 6/7 best for buying
    OTM_5 and ITM 2,3,4
    strngth 80,90 
    
    Week day 
    Monday : BELOW_VA, INSIDE_VA, tpo 7 -10 CE > PE OTM_5 and ITM 2,3,4 strength 40-60 
    Tueday : Tpo - 4 -9 ITM 2, OTM 5, strength 40
    Wednesday : Best day ,ABOVE_VA and BELOW_VA ,tpo 1-3 and 7-9 PE > CE  , > 30%
    Thursday: good for selling , ITM 2-3-4 OTM_5 and >80% looks fine for buying
    Friday : selling prefered specifically for PE, Buying - ABOVE_VA  and GAP_DOWN CE > PE, moneyness no clarity 
    
    """



def run():

    #save_back_test_results()

    df = get_cleaned_results()
    #basic_statistics(df)
    portfolio_performance(df)
    #portfolio_performance(df, filter={'open_type': 'ABOVE_VA', 'week_day': 'Monday'})
    analysis(df)

