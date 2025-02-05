import pandas as pd
from backtest.settings import reports_dir
from dynamics.trend.tick_price_smoothing import PriceInflexDetectorForTrend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from db.market_data import get_daily_tick_data, get_all_days
from dynamics.trend.technical_patterns import pattern_engine
from matplotlib.backends.backend_pdf import PdfPages
import helper.utils as helper_utils
import numpy as np


def load_back_test_results():
    df = pd.read_csv(reports_dir + 'ema_act_2_tick_watcher_redesign.csv', converters={'pattern_time': pd.eval})
    return df


def plot_sp_ext(report, dfsub,Symbol,day=None):
    total_infl = len(dfsub.index[dfsub['SPExt']!=''])
    post_ib_df = dfsub.iloc[60:, :]
    post_ib_infl = post_ib_df[post_ib_df['SPExt']!=''].shape[0]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index,dfsub['Close'],dfsub.index[dfsub['SPExt']!=''],dfsub.Close[dfsub['SPExt']!=''])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("Second pass inflex")
    plt.text(0.01, 1.1, 'total infl = ' + str(total_infl), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'post first hr infl = ' + str(post_ib_infl), transform=ax.transAxes)
    if day is not None:
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()
    #plt.show()



def plot_patterns_ext(report, dfsub,Symbol,day=None,all_trades=[]):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index, dfsub['Close'])
    for pattern_trade in all_trades:
        pat_points = pattern_trade['pattern_time']
        #print(pat_points)
        pattern_infl_idx = np.array(dfsub.index[dfsub['Time'].isin(pat_points)])
        #print('iii', pattern_infl_idx)
        pattern_infl_close = np.array(dfsub.Close)[pattern_infl_idx]
        plt.plot(pattern_infl_idx, pattern_infl_close)
        for trade in pattern_trade['trades']:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            if not np.isnan(exit_time):
                entry_idx = np.array(dfsub.index[dfsub['Time']==entry_time])[0]
                exit_idx = np.array(dfsub.index[dfsub['Time']==exit_time])[0]
                plt.plot(entry_idx, entry_price, marker="<", markersize=3, markeredgecolor="green", markerfacecolor="green")
                plt.plot(exit_idx, exit_price, marker=">", markersize=3, markeredgecolor="red", markerfacecolor="green")
            else:
                entry_idx = np.array(dfsub.index[dfsub['Time']==entry_time])[0]
                plt.plot(entry_idx, entry_price, marker="<", markersize=3, markeredgecolor="yellow", markerfacecolor="green")

    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("Pattern inflex")
    if day is not None:
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()
    #plt.show()

def run():
    df = load_back_test_results()
    #df = df[df['realized_pnl'] < 0]
    days = df['day'].unique()
    symbol = df['symbol'].tolist()[0]

    with PdfPages(reports_dir + 'visualize_pattern_chart_' + symbol + '.pdf') as report:
        for day in days:
            try:
                price_list = get_daily_tick_data(symbol, day)
                price_list['symbol'] = symbol
                price_list = price_list.to_dict('records')
                # https://medium.com/automation-generation/algorithmically-detecting-and-trading-technical-chart-patterns-with-python-c577b3a396ed
                pattern_detector = PriceInflexDetectorForTrend(symbol, fpth=0.001, spth=0.001)
                try:
                    for i in range(len(price_list)):
                        price = price_list[i]
                        pattern_detector.on_price_update([price['timestamp'], price['close']])
                except Exception as e:
                    print(e)
                # pattern_detector.create_sp_extremes()
                dfsub = pattern_detector.dfstock_3
                # print(dfsub.head().T)
                # dfsub = dfsub.reset_index()
                entry_points = list(set(df[df['day']==day]['entry_time'].tolist()))
                #print(entry_points)
                #print(df[(df['day'] == day) & (df['entry_time'] == entry_points[0])])
                pattern_times = [df[(df['day'] == day) & (df['entry_time'] == x)]['pattern_time'].to_list()[0] for x in entry_points]
                all_trades = []
                for pattern_time in pattern_times:
                    tmp = df[(df['day'] == day) & (df.pattern_time.map(set(pattern_time).issubset))][['entry_time', 'exit_time', 'entry_price', 'exit_price']]
                    tmp_trades = {'pattern_time': pattern_time, 'trades':[]}
                    for index, row in tmp.iterrows():
                        tmp_trades['trades'].append({'entry_time':row['entry_time'], 'exit_time':row['exit_time'], 'entry_price':row['entry_price'], 'exit_price':row['exit_price']})
                    all_trades.append(tmp_trades)
                #print(all_trades)
                plot_patterns_ext(report, dfsub, symbol, day, all_trades)
                plot_sp_ext(report, dfsub, symbol, day)
            except Exception as e:
                print(e)
                pass
