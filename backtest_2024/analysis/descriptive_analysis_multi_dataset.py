import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from servers.server_settings import reports_dir
from backtest_2024.analysis.binning import get_bins, bin_dict


def plot_table(report, df, title=""):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('tight')
    ax.axis('off')
    the_table = ax.table(cellText=df.values, colLabels=df.columns, loc='center')
    ax.title.set_text(title)
    report.savefig()
    plt.close()

def plot_table_large(report, df, title=""):
    fig, ax = plt.subplots(figsize=(12, 8))
    #fig.clf()
    #fig.text(0.4, 0.9, 'test +++++', transform=fig.transFigure, size=24, ha="center")
    ax.axis('tight')
    ax.axis('off')
    the_table = ax.table(cellText=df.values, colLabels=df.columns, loc='center')
    ax.title.set_text(title)
    report.savefig()
    plt.close()

def add_text_page(report, txt):
    firstPage = plt.figure(figsize=(11.69, 8.27))
    firstPage.clf()
    firstPage.text(0.5, 0.5, txt, transform=firstPage.transFigure, size=24, ha="center")
    report.savefig()
    plt.close()

def cross_group_summary(report, df_i,target, grp_list, filter={}):
    for key, value in filter.items():
        df_i = df_i[df_i[key] == value]

    day_wise_df = df_i.groupby(grp_list).agg({target: ['count', 'mean', 'min', 'max']})
    # day_wise_df = df_i.groupby(['strategy', 'support_ind',]).agg({target: ['count', 'mean', 'min', 'max']})
    day_wise_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max']
    day_wise_df = day_wise_df.reset_index().round(2)
    day_wise_df.to_csv('reports/cross_group_summary.csv')
    plot_table_large(report, day_wise_df)


def group_wise_summary(report, df_i,target, grp, filter={}):
    for key, value in filter.items():
        df_i = df_i[df_i[key] == value]

    day_wise_df = df_i.groupby([grp]).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
    # day_wise_df = df_i.groupby(['strategy', 'support_ind',]).agg({target: ['count', 'mean', 'min', 'max']})
    day_wise_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max', '+ve']
    day_wise_df = day_wise_df.reset_index().round(3)
    aggregate_df = df_i.groupby(['strategy']).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})

    aggregate_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max', '+ve']
    aggregate_df = aggregate_df.reset_index().round(3)
    #print('aggregate_df+++++++++++++++++')
    #print(aggregate_df)
    aggr_values = list(aggregate_df.iloc[0])
    aggr_values[0] = 'Total'
    day_wise_df.loc[len(day_wise_df.index)] = aggr_values
    day_wise_df['acc'] = day_wise_df['+ve']/day_wise_df['count']
    day_wise_df['acc'] = day_wise_df['acc'].round(2)
    plot_table(report, day_wise_df)


def bin_wise_summary(report, df_i, target, grp, filter={}, title=""):
    for key, value in filter.items():
        df_i = df_i[df_i[key] == value]

    bins = bin_dict.get(grp, [])
    if bins:
        day_wise_df = df_i.groupby(pd.cut(df_i[grp], bins, duplicates="drop")).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
    else:
        bins = get_bins(df_i, grp)
        day_wise_df = df_i.groupby(pd.cut(df_i[grp], bins, duplicates="drop")).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
        #day_wise_df = df_i.groupby(pd.qcut(df_i[grp], 20, duplicates="drop")).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
    #day_wise_df = df_i.groupby(pd.qcut(df_i[grp], 20, duplicates="drop")).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
    # day_wise_df = df_i.groupby(['strategy', 'support_ind',]).agg({target: ['count', 'mean', 'min', 'max']})
    day_wise_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max', '+ve']
    day_wise_df = day_wise_df.reset_index().round(3)
    aggregate_df = df_i.groupby(['strategy']).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})

    aggregate_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max', '+ve']
    aggregate_df = aggregate_df.reset_index().round(3)
    print('aggregate_df+++++++++++++++++')
    print(aggregate_df)
    aggr_values = list(aggregate_df.iloc[0])
    aggr_values[0] = 'Total'
    day_wise_df.loc[len(day_wise_df.index)] = aggr_values
    day_wise_df['acc'] = day_wise_df['+ve']/day_wise_df['count']
    day_wise_df['acc'] = day_wise_df['acc'].round(2)
    plot_table_large(report, day_wise_df, title)


def add_strategy_details(report, df_i, target, filter={}):
    total_days = len(df_i['day'].unique())
    for key, value in filter.items():
        df_i = df_i[df_i[key] == value]

    strategy = df_i['strategy'].to_list()[0]
    no_of_days = len(df_i['day'].unique())
    winning_trades = df_i[df_i[target] > 0]
    losing_trades = df_i[df_i[target] < 0]
    winning_count = df_i[df_i[target] > 0][target].count()
    winning_avg = round(df_i[df_i[target] > 0][target].mean(), 2)
    losing_count = df_i[df_i[target] < 0][target].count()
    losing_avg = round(df_i[df_i[target] < 0][target].mean(), 2)
    winning_pct = round(winning_trades.shape[0] / (winning_trades.shape[0] + losing_trades.shape[0]) * 100, 1)
    days_for_scen = round(no_of_days / total_days * 100, 2)
    print('filter', filter)
    print('winning trade count', df_i[df_i[target] > 0][target].count())
    print('winning trade avg', round(df_i[df_i[target] > 0][target].mean(), 2))
    print('losing trade count', df_i[df_i[target] < 0][target].count())
    print('losing trade avg', round(df_i[df_i[target] < 0][target].mean(), 2))
    print('percentage winning trade', str(winning_pct) + "%")
    print('No days for scenario', str(no_of_days) )
    print('percentage days for scenario', str(days_for_scen) + "%")

    txt_d = 'Details of strategy ' + strategy
    firstPage = plt.figure(figsize=(11.69, 8.27))
    firstPage.clf()
    firstPage.text(0.4, 0.9, txt_d, transform=firstPage.transFigure, size=24, ha="center")
    firstPage.text(0.4, 0.8, 'winning trade count = ' + str(winning_count), transform=firstPage.transFigure, size=15,
                   ha="center")
    firstPage.text(0.4, 0.7, 'winning trade avg = ' + str(winning_avg), transform=firstPage.transFigure, size=15,
                   ha="center")
    firstPage.text(0.4, 0.6, 'losing trade count = ' + str(losing_count), transform=firstPage.transFigure, size=15,
                   ha="center")
    firstPage.text(0.4, 0.5, 'losing trade avg = ' + str(losing_avg), transform=firstPage.transFigure, size=15,
                   ha="center")
    firstPage.text(0.4, 0.5, 'losing trade avg = ' + str(losing_avg), transform=firstPage.transFigure, size=15,
                   ha="center")
    firstPage.text(0.4, 0.4, 'percentage winning trade = ' + str(winning_pct) + "%", transform=firstPage.transFigure, size=15,
                   ha="center")

    firstPage.text(0.4, 0.3, 'No days for scenario = ' + str(no_of_days) , transform=firstPage.transFigure,
                   size=15,
                   ha="center")

    firstPage.text(0.4, 0.2, 'percentage days for scenario = ' + str(days_for_scen) + "%", transform=firstPage.transFigure,
                   size=15,
                   ha="center")
    report.savefig()
    plt.close()


def perform_analysis_strategies_multi_df(time_data_set, inflex_data_set, target, exclude_variables=[], inflex_buffers=[]):
    print('perform_analysis_strategies_multi_df descriptive++++++++')
    time_data_set['tpo'].fillna(0, inplace=True)
    inflex_data_set['tpo'].fillna(0, inplace=True)

    cols =  [x for x in time_data_set.columns if x not in exclude_variables]
    time_data_set = time_data_set[cols]
    inflex_data_set = inflex_data_set[cols]
    description = time_data_set.describe()


    #print(df_i.columns.tolist())
    with PdfPages(reports_dir +'descrpitive_analysis_multi_df.pdf') as report:
        time_data_set['root_strategy'] = time_data_set['strategy'].apply(lambda x: x.split("_")[0])
        root_strategies = list(set(time_data_set['root_strategy'].to_list()))
        root_strategies.sort()
        for root_strategy in root_strategies:
            txt = 'Analysis of root strategy ' + root_strategy
            add_text_page(report, txt)
            strategies = list(set(time_data_set[time_data_set['root_strategy'] == root_strategy]['strategy'].to_list()))
            strategies.sort()
            for strategy in strategies:
                print('analysing strategy++++++++++++++++++++++++++++++++++++++++++++', strategy)
                txt = 'Analysis of  strategy ' + strategy
                add_text_page(report, txt)
                df_time = time_data_set[time_data_set['strategy'] == strategy]
                df_inflex = inflex_data_set[inflex_data_set['strategy'] == strategy]
                dict_df_inflex = {}
                for inflex_buffer in inflex_buffers:
                    df = df_inflex.copy()
                    df['realized_pnl'] = df['realized_pnl'].apply(lambda x: x - inflex_buffer)
                    dict_df_inflex[inflex_buffer] = df

                filter = {}
                #variables = ['day_put_profit', 'day_call_profit', 'day_total_profit', 'vol_rat', 'pcr_minus_1', 'put_call_vol_scale_diff', 'call_entrant', 'put_entrant', 'transition', 'near_put_oi_share', 'far_put_oi_share', 'near_call_oi_share', 'far_call_oi_share', 'put_vol_spread', 'call_vol_spread', 'near_call_volume_share_per_oi', 'near_put_volume_share_per_oi', 'far_call_volume_share_per_oi', 'far_put_volume_share_per_oi' ]
                variables = [
                    'near_put_oi_share', 'far_put_oi_share', 'near_call_oi_share', 'far_call_oi_share',
                    'put_vol_spread', 'call_vol_spread', 'near_call_volume_share_per_oi',
                    'near_put_volume_share_per_oi', 'far_call_volume_share_per_oi', 'far_put_volume_share_per_oi',
                    'pcr_minus_1',
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
                    'r_total_vol_pcr'
                    ]

                for variable in variables:
                    bin_wise_summary(report, df_time, target, variable, filter=filter, title="time based")
                    for buffer, buffer_df in dict_df_inflex.items():
                        bin_wise_summary(report, buffer_df, target, variable, filter=filter, title="inflex based buffer " + str(buffer))

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