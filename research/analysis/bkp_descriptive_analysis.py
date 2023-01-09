import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
from settings import reports_dir
from sklearn.linear_model import LinearRegression


def box_plot(report, df, metric, title=None):
    # Plot day average  and perform anova of k-means
    ax = df.boxplot(metric, figsize=(12, 8))
    #columns_my_order = df[group]
    #ax.set_xticklabels(columns_my_order)
    if title is None:
        title = "box plot of " + metric
    plt.title(title, fontsize=20)
    report.savefig()
    plt.close()



def box_plot_by_group(report, df, metric, group, title=None):
    # Plot day average  and perform anova of k-means
    ax = df.boxplot(metric, by=group, figsize=(12, 8))
    #columns_my_order = df[group]
    #ax.set_xticklabels(columns_my_order)
    if title is None:
        title = metric + ' over ' + group
    plt.title(title, fontsize=20)
    report.savefig()
    plt.close()


def plot_table(report, df):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('tight')
    ax.axis('off')
    the_table = ax.table(cellText=df.values, colLabels=df.columns, loc='center')
    report.savefig()
    plt.close()

def add_text_page(report, txt):
    firstPage = plt.figure(figsize=(11.69, 8.27))
    firstPage.clf()
    firstPage.text(0.5, 0.5, txt, transform=firstPage.transFigure, size=24, ha="center")
    report.savefig()
    plt.close()

def group_wise_summary(report, df_i,target, grp):
    day_wise_df = df_i.groupby([grp]).agg({target: ['count', 'mean', 'min', 'max']})
    # day_wise_df = df_i.groupby(['strategy', 'support_ind',]).agg({target: ['count', 'mean', 'min', 'max']})
    day_wise_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max']
    day_wise_df = day_wise_df.reset_index().round(2)
    aggregate_df = df_i.groupby(['strategy']).agg({target: ['count', 'mean', 'min', 'max']})

    aggregate_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max']
    aggregate_df = aggregate_df.reset_index().round(2)
    #print('aggregate_df+++++++++++++++++')
    aggr_values = list(aggregate_df.iloc[0])
    aggr_values[0] = 'Total'
    day_wise_df.loc[len(day_wise_df.index)] = aggr_values
    plot_table(report, day_wise_df)


def add_strategy_details(report, df_i):
    strategy = df_i['strategy'].to_list()[0]
    winning_trades = df_i[df_i[target] > 0]
    losing_trades = df_i[df_i[target] < 0]
    winning_count = df_i[df_i[target] > 0][target].count()
    winning_avg = round(df_i[df_i[target] > 0][target].mean(), 2)
    losing_count = df_i[df_i[target] < 0][target].count()
    losing_avg = round(df_i[df_i[target] < 0][target].mean(), 2)
    winning_pct = round(winning_trades.shape[0] / (winning_trades.shape[0] + losing_trades.shape[0]) * 100, 1)
    print('winning trade count', df_i[df_i[target] > 0][target].count())
    print('winning trade avg', round(df_i[df_i[target] > 0][target].mean(), 2))
    print('losing trade count', df_i[df_i['realized_pnl'] < 0][target].count())
    print('losing trade avg', round(df_i[df_i['realized_pnl'] < 0]['target'].mean(), 2))
    print('percentage winning trade', str(winning_pct) + "%")

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

    report.savefig()
    plt.close()


def plot_histogram(report, df_input, metric, filter={}, title=None):

    if title is None:
        title = 'Histogram of ' + metric

    df = df_input
    try:
        for key, value in filter.items():
            df = df[df[key] == value]
            desc = value if isinstance(value, str) else str(value)
            title = 'Histogram of ' + metric + " for " + desc + " "
        df[metric].hist(weights=np.ones_like(df[df.columns[0]]) * 100. / len(df), grid=False,figsize=(12,8))
        plt.title(title, fontsize=20)
        report.savefig()
        plt.close()
    except:
        pass


def plot_scatter(report, df_input, x, y, s, filter={}, title=None):
    if title is None:
        title = 'Scatter plot of ' + x + " vs " + y
    df = df_input
    for key, value in filter.items():
        df = df[df[key] == value]
        desc = value if isinstance(value, str) else str(value)
        title = 'Scatter plot of ' + x + " vs " + y + " for " + desc
    df.plot.scatter(x=x, y=y, s=s)
    try:
        linear_regressor = LinearRegression()
        linear_regressor.fit(df[x].values.reshape(-1, 1), df[y].values.reshape(-1, 1))
        y_pred = linear_regressor.predict(df[x].values.reshape(-1, 1))
        plt.plot(df[x], y_pred, color='red')
    except:
        pass
    plt.title(title, fontsize=10)
    report.savefig()
    plt.close()


def Plot3D_O(report, df, x,y,z):
    threedee = plt.figure().gca(projection='3d')
    threedee.scatter(df[x], df[y], df[z])
    threedee.set_xlabel(x)
    threedee.set_ylabel(y)
    threedee.set_zlabel(z)
    report.savefig()
    plt.close()

def Plot3D(report, df, x,y,z):
    threedee = plt.figure()
    X, Y = np.meshgrid(df[x], df[y])
    ax = plt.axes(projection='3d')
    #ax.contour3D(X,Y, df[z], cmap='binary')
    #ax.plot_surface(X, Y, df[z], rstride=1, cstride=1, cmap='viridis', edgecolor='none')
    #ax.plot_trisurf(df[x], df[y],  df[z], linewidth=0, antialiased=False)
    ax.scatter( df[y], df[z],df[x], c='r', marker='o')
    ax.view_init(20, 60)

    ax.set_xlabel(y)
    ax.set_ylabel(z)
    ax.set_zlabel(x)

    report.savefig()
    plt.close()




def perform_analysis_strategies(data_set, target, exclude_variables=[]):
    print('perform_analysis_strategies descriptive++++++++')
    data_set['tpo'].fillna(0, inplace=True)
    #data_set = data_set[data_set[target]>0]
    #data_set = data_set[data_set['pattern_quad'] > -1000]

    cols =  [x for x in data_set.columns if x not in exclude_variables]
    data_set = data_set[cols]
    description = data_set.describe()
    #print(description)
    correlations = data_set.corr(method='pearson')
    #print(correlations)
    """
    plt.figure(figsize=(7, 5))
    plt.hist(data_set.realized_pnl)
    plt.show()
    """

    #print(df_i.columns.tolist())
    with PdfPages(reports_dir +'descrpitive_analysis.pdf') as report:
        data_set['root_strategy'] = data_set['strategy'].apply(lambda x: x.split("_")[0])
        root_strategies = list(set(data_set['root_strategy'].to_list()))
        root_strategies.sort()
        for root_strategy in root_strategies:
            txt = 'Analysis of root strategy ' + root_strategy
            add_text_page(report, txt)
            strategies = list(set(data_set[data_set['root_strategy'] == root_strategy]['strategy'].to_list()))
            strategies.sort()
            for strategy in strategies:
                print('analysing strategy++++++++++++++++++++++++++++++++++++++++++++', strategy)
                txt = 'Analysis of  strategy ' + strategy
                add_text_page(report, txt)
                df_i = data_set[data_set['strategy'] == strategy]
                group_wise_summary(report, df_i, target, 'week_day')
                group_wise_summary(report, df_i, target, 'open_type')
                group_wise_summary(report, df_i, target, 'tpo')
                add_strategy_details(report,df_i)

                box_plot(report, df_i, 'realized_pnl')
                plot_histogram(report, df_i, 'realized_pnl')
                box_plot_by_group(report, df_i, 'realized_pnl', 'week_day')
                box_plot_by_group(report, df_i, 'realized_pnl', 'open_type')
                box_plot_by_group(report, df_i, 'realized_pnl', 'tpo')
                """
                plot_histogram(report, df_i, 'realized_pnl', filter={'week_day': 'Monday'})
                plot_histogram(report, df_i, 'realized_pnl', filter={'week_day': 'Tuesday'})
                plot_histogram(report, df_i, 'realized_pnl', filter={'week_day': 'Wednesday'})
                plot_histogram(report, df_i, 'realized_pnl', filter={'week_day': 'Thursday'})
                plot_histogram(report, df_i, 'realized_pnl', filter={'week_day': 'Friday'})
                box_plot(report, df_i, 'dist_frm_level')
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1, filter={'week_day': 'Monday'})
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1, filter={'week_day': 'Tuesday'})
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1, filter={'week_day': 'Wednesday'})
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1, filter={'week_day': 'Thursday'})
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1, filter={'week_day': 'Friday'})
                """
                """
                plot_scatter(report, df_i, 'static_ratio', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'd_en_pyr', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'candles_in_range', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'dist_frm_level', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'support_ind', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'y_low', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'y_va_h_p', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'y_va_l_p', 'realized_pnl', 1)
                plot_scatter(report, df_i, 'y_poc_price', 'realized_pnl', 1)
                """
                x = ['static_ratio', 'd_en_pyr', 'candles_in_range', 'dist_frm_level',
               'support_ind', 'y_low', 'y_va_h_p', 'y_va_l_p', 'y_poc_price',
               'w_S1', 'w_S2', 'pattern_location',
                'lw_total_energy_ht', 'auc_del', 'mu_n']
                col_sub = ['quad', 'lin', 'quad_r2', 'lin_r2', 'market_auc', 'trend_auc', 'auc_del', 'mu_0', 'mu_n', 'exp_b', 'exp_c', 'pattern_quad', 'pattern_lin', 'pattern_quad_r2', 'pattern_lin_r2', 'pattern_market_auc', 'pattern_trend_auc', 'pattern_auc_del', 'first_hour_trend', 'whole_day_trend', 'five_min_trend', 'fifteen_min_trend', 'five_min_ex_first_hr_trend', 'fifteen_min_ex_first_hr_trend', 'hurst_exp_15', 'hurst_exp_5', 'ret_trend', 'candles_in_range']
                """
                for col in x:
                    df_t = df_i.dropna(subset=[col])
                    plot_scatter(report, df_t, col, 'realized_pnl', 1)
                """
                #print(day_wise_df[day_wise_df['support_ind']==0].to_string())

def perform_analysis(data_set, target, exclude_variables=[]):
    print('perform_analysis descriptive++++++++')
    data_set = data_set.dropna(subset=['tpo'])
    #data_set = data_set[data_set[target]>0]

    data_set = data_set[data_set['pattern_quad'] > -1000]
    cols =  [x for x in data_set.columns if x not in exclude_variables]
    data_set = data_set[cols]
    strategies = data_set['strategy'].unique()
    print(strategies)
    root_strategies = set([x.split("_")[0] for x in strategies])
    print('total patterns matched___', len(list(root_strategies)))
    print(list(root_strategies))
    for strategy in strategies:
        print(strategy, "============================")
        data_set_temp = data_set[data_set['strategy'] == strategy]
        data_set_temp_gb = data_set_temp.describe()
        print(data_set_temp_gb.T)
    #description = data_set.describe()
    #print(description)
