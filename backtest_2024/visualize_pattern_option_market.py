import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

from settings import reports_dir
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
    df = pd.read_csv(reports_dir + 'up_break_type_3.csv', converters={'pattern_time': pd.eval})
    #df = df[df['strategy'] == 'PriceReverseBreakDownEMA'] #PriceReverseBreakDownEMA # PriceBreakEMADownward43
    return df

def plot_intraday_chart(report, ticker, day, period, entry_point_list, exit_point_list, entry_price_list, exit_price_list):
    today_df = get_daily_tick_data(ticker, day)
    today_df['timestamp'] = pd.to_datetime(today_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    today_df = today_df.set_index('timestamp')
    today_df = convert_to_n_period_candles(today_df, period)

    today_df = today_df.reset_index()
    today_df_cp = today_df.copy()
    today_df_cp['timestamp'] = today_df_cp['timestamp'].apply(lambda x: x.timestamp()) #.astype('int64')
    #print(today_df_cp['timestamp'].to_list())
    #print(entry_points)
    period_int = 1 if period == '1Min' else 5
    entry_indices_list = [[np.array(today_df.index[today_df_cp['timestamp'] == (entry_time - (period_int-1) * 60)])[0] for entry_time in entry_points] for entry_points in entry_point_list]
    print(entry_indices_list)
    entry_indices_list = [[get_next_lowest_index(today_df_cp['timestamp'].to_list(), entry_time) for entry_time in entry_points] for entry_points in entry_point_list]
    print(entry_indices_list)
    exit_indices_list = [[get_next_lowest_index(today_df_cp['timestamp'].to_list(), exit_time) for exit_time in
                 exit_points if not np.isnan(exit_time)] for exit_points in exit_point_list]

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

    prices['EMA10'] = prices['close'].ewm(span=10, adjust=False).mean()
    #plt.plot(prices.index, prices['EMA10'], color='green', label='EMA10')
    entry_colors = ['red', 'green']
    exit_colors = ['black', 'blue']
    for o_idx in range(len(entry_indices_list)):
        entry_indices = entry_indices_list[o_idx]
        entry_prices = entry_price_list[o_idx]
        for idx in range(len(entry_indices)):
            entry_idx = entry_indices[idx]
            entry_price = entry_prices[idx]
            plt.plot(entry_idx, entry_price, marker="<", markersize=3, markeredgecolor=entry_colors[o_idx], markerfacecolor=entry_colors[o_idx])

    for o_idx in range(len(exit_indices_list)):
        exit_indices = exit_indices_list[o_idx]
        exit_prices = exit_price_list[o_idx]

        for idx in range(len(exit_indices)):
            exit_idx = exit_indices[idx]
            exit_price = exit_prices[idx]
            plt.plot(exit_idx, exit_price, marker=">", markersize=3, markeredgecolor=exit_colors[o_idx], markerfacecolor=exit_colors[o_idx])
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
    print('running')
    df = load_back_test_results()
    days = df['day'].unique()
    ticker = df['symbol'].tolist()[0]
    strategy = df['strategy'].tolist()[0]
    with PdfPages(reports_dir + 'visualize_option_' + strategy + '.pdf') as report:
        strategies = list(set(df['strategy'].to_list()))
        for day in days:
            try:
                t_day = df[df['day']==day]
                entry_point_list = []
                exit_point_list = []
                entry_price_list = []
                exit_price_list = []
                for strategy in strategies:
                    t_day_strat = t_day[t_day['strategy'] == strategy]
                    entry_points = list(set(t_day_strat['entry_time'].tolist()))
                    exit_points = list(set(t_day_strat['exit_time'].tolist()))
                    entry_prices = [t_day_strat[t_day_strat['entry_time'] == entry_point]['spot_entry_price'].to_list()[0] for
                                    entry_point in entry_points]
                    # print(entry_prices)
                    exit_prices = [t_day_strat[t_day_strat['exit_time'] == exit_point]['spot_exit_price'].to_list()[0] for exit_point in
                                   exit_points]
                    entry_point_list.append(entry_points)
                    exit_point_list.append(exit_points)
                    entry_price_list.append(entry_prices)
                    exit_price_list.append(exit_prices)
                plot_intraday_chart(report, ticker, day, '1Min', entry_point_list, exit_point_list, entry_price_list, exit_price_list)
            except Exception as e:
                print(e)
            pass
run()