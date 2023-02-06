from backtest.settings import reports_dir
import numpy as np
from db.market_data import (
    get_daily_tick_data,
    convert_to_n_period_candles,
    )

from dynamics.profile.utils import get_next_lowest_index, get_next_highest_index
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

def load_back_test_results():
    df = pd.read_csv(reports_dir + 'ema_act_2_tick_watcher_redesign.csv', converters={'pattern_time': pd.eval})
    return df

def plot_intraday_chart(report, ticker, day, period, entry_points, exit_points, entry_prices, exit_prices):
    today_df = get_daily_tick_data(ticker, day)
    today_df['timestamp'] = pd.to_datetime(today_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    today_df = today_df.set_index('timestamp')
    today_df = convert_to_n_period_candles(today_df, period)

    today_df = today_df.reset_index()
    today_df_cp = today_df.copy()
    today_df_cp['timestamp'] = today_df_cp['timestamp'].apply(lambda x: x.timestamp()) #.astype('int64')
    #print(today_df_cp['timestamp'].to_list())
    #print(entry_points)
    entry_indices = [np.array(today_df.index[today_df_cp['timestamp'] == (entry_time - 4* 60)])[0] for entry_time in entry_points]
    print(entry_indices)
    entry_indices = [get_next_lowest_index(today_df_cp['timestamp'].to_list(), entry_time) for entry_time in
                 entry_points]
    print(entry_indices)
    exit_indices = [get_next_lowest_index(today_df_cp['timestamp'].to_list(), exit_time) for exit_time in
                 exit_points if not np.isnan(exit_time)]

    today_df["timestamp"] = today_df["timestamp"].apply(lambda x: x.strftime('%H:%M'))

    #print(today_df.timestamp)
    #today_df = today_df.set_index('timestamp')
    #final_df = today_df
    #prices = final_df.loc[:, ['timestamp', 'open', 'high', 'low', 'close']]
    prices = today_df
    up = prices[prices.close >= prices.open]
    down = prices[prices.close < prices.open]

    width = .4
    width2 = .05

    # define colors to use
    col1 = 'green'
    col2 = 'red'

    # plot up prices
    plt.figure()
    plt.bar(up.index, up.close - up.open, width, bottom=up.open, color=col1)
    plt.bar(up.index, up.high - up.close, width2, bottom=up.close, color=col1)
    plt.bar(up.index, up.low - up.open, width2, bottom=up.open, color=col1)

    # plot down prices
    plt.bar(down.index, down.close - down.open, width, bottom=down.open, color=col2)
    plt.bar(down.index, down.high - down.open, width2, bottom=down.open, color=col2)
    plt.bar(down.index, down.low - down.close, width2, bottom=down.close, color=col2)

    prices['EMA5'] = prices['close'].ewm(span=5, adjust=False).mean()
    plt.plot(prices.index, prices['EMA5'], color='green', label='EMA5')

    for idx in range(len(entry_indices)):
        entry_idx = entry_indices[idx]
        entry_price = entry_prices[idx]
        plt.plot(entry_idx, entry_price, marker="<", markersize=7, markeredgecolor="black", markerfacecolor="black")

    for idx in range(len(exit_indices)):
        exit_idx = exit_indices[idx]
        exit_price = exit_prices[idx]
        plt.plot(exit_idx, exit_price, marker=">", markersize=7, markeredgecolor="blue", markerfacecolor="blue")
    tick_pos = list(range(0,len(prices.timestamp),3))
    tick_labels = [prices.timestamp[x] for x in tick_pos]
    plt.xticks(ticks = tick_pos, labels = tick_labels)
    # rotate x-axis tick labels
    plt.xticks(rotation=90, ha='right')
    plt.title(day)
    if day is not None:
        plt.text(0.9, 1.05, day, transform=plt.gcf().transFigure)
    report.savefig()
    plt.close()

    # display candlestick chart
    #plt.show()


def run():
    df = load_back_test_results()
    days = df['day'].unique()
    ticker = df['symbol'].tolist()[0]
    with PdfPages(reports_dir + 'visualize_ema_chart_' + ticker + '.pdf') as report:
        for day in days:
            try:
                t_day = df[df['day']==day]
                entry_points = list(set(t_day['entry_time'].tolist()))
                exit_points = list(set(t_day['exit_time'].tolist()))
                entry_prices = [t_day[t_day['entry_time'] == entry_point]['entry_price'].to_list()[0] for entry_point in entry_points]
                #print(entry_prices)
                exit_prices = [t_day[t_day['exit_time'] == exit_point]['exit_price'].to_list()[0] for exit_point in exit_points]
                #print(exit_prices)
                #print('trying', day)
                plot_intraday_chart(report, ticker, day, '5Min', entry_points, exit_points, entry_prices, exit_prices)
            except Exception as e:
                print(e)
            pass
