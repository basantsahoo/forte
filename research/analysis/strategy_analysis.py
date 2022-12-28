from backtest import strategy_back_tester
from analysis import classifier_train
from analysis import regression_train
from analysis import descriptive_analysis
import pandas as pd
from settings import reports_dir


def save_back_test_results():
    # results = strategy_back_tester.test(strategy_class=SMACrossBuy, symbols=['NIFTY'],days=['2022-05-25'])
    results = strategy_back_tester.test(SMACrossBuy, ['NIFTY'], days=['2022-06-03'], for_past_days=300)
    #pd.DataFrame(results).to_csv(reports_dir + 'SMACrossBuy_nifty_results.csv')

def load_back_test_results():
    #df = pd.read_csv(reports_dir + 'RangeBreakDownStrategy_for_refression.csv')
    df = pd.read_csv(reports_dir + 'PatternAggregator_3.csv')
    return df

def run():

    #save_back_test_results()

    df = load_back_test_results()
    df['infl_dir'] = df['infl_n'] - df['infl_0']
    df['infl_dir'] = df['infl_dir'].apply(lambda x : int(x > 0))
    # 'resistance_ind',	'support_ind'

    exclude_vars = ['day', 'symbol', 'trigger', 'infl_0', 'infl_n', 'Unnamed: 0', 'un_realized_pnl', 'entry_time','exit_time']
    descriptive_analysis.perform_analysis_strategies(df, 'realized_pnl', exclude_vars)

    exclude_vars = ['day', 'symbol', 'strategy', 'trigger', 'infl_0', 'infl_n', 'Unnamed: 0', 'un_realized_pnl','entry_time', 'exit_time', 'pattern_time']
    strategies = df['strategy'].unique()
    root_strategies = set([x.split("_")[0] for x in strategies])
    print('total patterns matched___', len(list(root_strategies)))


    for strategy in strategies:
        print(strategy)
        #if strategy == 'CDLXSIDEGAP3METHODS_5_BUY_30':
        df_tmp = df[df['strategy'] == strategy]
        classifier_train.train(df_tmp, 'realized_pnl', exclude_vars)
        

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
    #CDL3OUTSIDE_5_BUY_15 - 0.67
    #CDL3OUTSIDE_5_BUY_20 - 0.71
    #CDL3OUTSIDE_5_BUY_30 - 0.77
    #CDL3OUTSIDE_5_SELL_20 - 0.73
    #CDL3OUTSIDE_15_SELL_30 - 0.64
    #CDLXSIDEGAP3METHODS_5_BUY_15 - 0.72
    #CDLXSIDEGAP3METHODS_5_BUY_30 - 0.85


    #tier -2
    #CDLENGULFING_15_BUY_15 - 0.52
    #CDLENGULFING_5_SELL_20 - 0.78
    #CDLENGULFING_5_SELL_30 - 0.80
    #CDL3OUTSIDE_5_SELL_30  - 0.73
    #CDL3OUTSIDE_15_SELL_15 - 0.42
    #CDL3OUTSIDE_15_BUY_10  - 0.42
    #classifier_train.train(df, 'realized_pnl', exclude_vars)
