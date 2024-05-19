import pandas as pd
from settings import reports_dir
from dynamics.trend.tick_price_smoothing import PriceInflexDetectorForTrend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from db.market_data import get_daily_tick_data, get_all_days
from dynamics.trend.technical_patterns import pattern_engine
from matplotlib.backends.backend_pdf import PdfPages
import helper.utils as helper_utils
import numpy as np
from db.market_data import (
    #get_daily_data,
    get_daily_profile_data,
    get_daily_tick_data,
    get_nth_day_hist_data,
    get_nth_day_profile_data,
    get_uk_opening_time,
    convert_to_n_period_candles,
    get_filtered_days,
    get_prev_week_candle,
    get_pending_profile_dates)

from dynamics.profile.utils import get_next_lowest_index, get_next_highest_index
import matplotlib.pyplot as plt
from mpl_finance import candlestick_ohlc
import pandas as pd
import matplotlib.dates as mpl_dates

def load_back_test_results():
    df = pd.read_csv(reports_dir + 'ema_act_2_tick_watcher_redesign.csv', converters={'pattern_time': pd.eval})
    return df


def plot_intraday_chart_2(ticker, day, period, entry_points, exit_points):
    today_df = get_daily_tick_data(ticker, day)
    today_df['timestamp'] = pd.to_datetime(today_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    today_df = today_df.set_index('timestamp')
    today_df = convert_to_n_period_candles(today_df, period)
    today_df = today_df.reset_index()
    final_df = today_df
    ohlc = final_df.loc[:, ['timestamp', 'open', 'high', 'low', 'close']]
    ohlc.columns =  ['timestamp', 'Open', 'High', 'Low', 'Close']
    ohlc['timestamp'] = ohlc['timestamp'].apply(mpl_dates.date2num)
    print(final_df.shape)

    fig, ax = plt.subplots()
    print(ohlc.shape)
    candlestick_ohlc(ax, ohlc.values, width=0.6, colorup='green', colordown='red', alpha=0.8)

    # Setting labels & titles
    ax.set_xlabel('timestamp')
    ax.set_ylabel('Price')
    ohlc['SMA5'] = ohlc['Close'].rolling(5).mean()
    ax.plot(ohlc['timestamp'], ohlc['SMA5'], color='green', label='SMA5')

    fig.suptitle('Intraday Candlestick Chart of NIFTY50')

    # Formatting Date
    date_format = mpl_dates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(date_format)
    fig.autofmt_xdate()

    fig.tight_layout()

    plt.show()


def plot_intraday_chart(ticker, day, period, entry_points, exit_points, entry_prices, exit_prices):
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

    prices['SMA5'] = prices['close'].rolling(5).mean()
    plt.plot(prices.index, prices['SMA5'], color='green', label='SMA5')
    for idx in range(len(entry_indices)):
        entry_idx = entry_indices[idx]
        entry_price = entry_prices[idx]
        plt.plot(entry_idx, entry_price, marker="<", markersize=3, markeredgecolor="green", markerfacecolor="green")

    plt.xticks(ticks = list(range(len(prices.timestamp))), labels = prices.timestamp)
    # rotate x-axis tick labels
    plt.xticks(rotation=90, ha='right')

    # display candlestick chart
    plt.show()


def run():
    df = load_back_test_results()
    days = df['day'].unique()
    ticker = df['symbol'].tolist()[0]
    print(days[0])
    for day in days[0:1]:
        try:
            t_day = df[df['day']==day]
            entry_points = list(set(t_day['entry_time'].tolist()))
            exit_points = list(set(t_day['exit_time'].tolist()))
            entry_prices = [t_day[t_day['entry_time'] == entry_point]['entry_price'].to_list()[0] for entry_point in entry_points]
            exit_prices = [t_day[t_day['entry_time'] == exit_point]['exit_price'].to_list()[0] for exit_point in exit_points]
            print('trying', day)
            plot_intraday_chart(ticker, day, '5Min', entry_points, exit_points, entry_prices, exit_prices)
        except Exception as e:
            print(e)
        pass
