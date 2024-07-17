import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

from db.market_data import get_prev_week_consolidated_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from servers.server_settings import reports_dir
import pandas as pd
import datetime as dt
from reporting.charts import plot_profile_chart
import traceback
from dynamics.profile.utils import get_next_highest_index, get_next_lowest_index
import os
import glob
from PyPDF2 import PdfFileMerger, PdfFileReader



def plot_weekly_profile(symbol, day, week_start_day, start_time):
    t_day = datetime.strptime(day, '%Y-%m-%d') if type(day) == str else day
    t_day_ordinal = t_day.toordinal()
    recent_week_start_str = datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d')
    print(recent_week_start_str)
    prev_week_start_str = datetime.strftime(datetime.fromordinal(t_day_ordinal-7), '%Y-%m-%d')
    print(prev_week_start_str)
    profile_data_list = []
    df = get_prev_week_consolidated_minute_data_by_start_day(symbol, recent_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df['symbol'] = symbol
    df['ltp'] = df['close']
    profile_data_list.append(df.to_dict('records'))
    df = get_prev_week_consolidated_minute_data_by_start_day(symbol, prev_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df['symbol'] = symbol
    df['ltp'] = df['close']
    profile_data_list.append(df.to_dict('records'))
    try:
        with PdfPages(reports_dir + symbol +"_weekly" + "/" + day + "_" + week_start_day + '_profile.pdf') as report:
            y_s = []
            for data in profile_data_list:
                processor = WeeklyMarketProfileService()
                processor.set_trade_date_from_time(data[0]['timestamp'], data[-1]['timestamp'])
                processor.process_hist_data(data)
                processor.calculateProfile()
                price_bins = processor.price_bins
                y_s.extend(list(price_bins))
            y_s = list(set(y_s))
            y_s.sort()
            chrt_idx = 0
            profile_data_list.reverse()
            fig = plt.figure()
            plt.tight_layout()

            #layout_cols = len(profile_data_list) + 1
            layout_cols = len(profile_data_list)
            for dt_idx in range(len(profile_data_list)):
                data = profile_data_list[dt_idx]
                chrt_idx += 1
                processor = WeeklyMarketProfileService()
                processor.set_trade_date_from_time(data[0]['timestamp'], data[-1]['timestamp'])
                processor.process_hist_data(data)
                processor.calculateProfile()
                processed_data = processor.market_profile
                if dt_idx < len(profile_data_list)-1:
                    last_week_profile = processed_data
                price_bins = processor.price_bins
                tick_size = processor.tick_size

                min_y_s = int(min(y_s))
                max_y_s = int(max(y_s))
                min_price_bin = int(min(price_bins))
                max_price_bin = int(max(price_bins))
                excluded_bins = []
                if min_y_s < min_price_bin:
                    bin_to_add = [i for i in range(min_y_s, min_price_bin, tick_size)]
                    excluded_bins.extend(bin_to_add)
                if max_y_s > max_price_bin:
                    bin_to_add = [i for i in range(max_price_bin + tick_size, max_y_s + tick_size, tick_size)]
                    excluded_bins.extend(bin_to_add)
                print_matrix = processor.print_matrix
                df = pd.DataFrame(print_matrix.T)
                df.index = price_bins
                # print(excluded_bins)
                for p_idx in list(excluded_bins):
                    df.loc[p_idx] = [0 for i in range(df.shape[1])]
                df = df.sort_index(axis=0)

                # print(df)
                #prints = list(string.ascii_uppercase)[0:print_matrix.shape[0]]
                #prints = [str(i+1) for i in range(1000)][0:print_matrix.shape[0]]
                prints = processor.tpo_letters
                df.columns = prints
                c_date = dt.datetime.fromtimestamp(data[0]['timestamp']).strftime('%Y-%m-%d')
                ax = fig.add_subplot(1, layout_cols, chrt_idx)
                rem_y_label = True if dt_idx > 0 else False
                plot_profile_chart(ax, df, c_date, rem_y_label, xlim=30)
                if not rem_y_label:
                    # yday_profile['va_h_p']
                    pass
                else:
                    rev_ys = range(int(min(y_s)), int(max(y_s) + tick_size), tick_size)
                    ax.hlines(y=y_s.index(last_week_profile['value_area_price'][0]), linewidth=0.5, xmin=0, xmax=100,
                              linestyles="dashed", color='lightgreen')
                    ax.hlines(y=y_s.index(last_week_profile['value_area_price'][1]), linewidth=0.5, xmin=0, xmax=100,
                              linestyles="dashed", color='red')
                    ax.hlines(y=y_s.index(last_week_profile['poc_price']), linewidth=0.5, xmin=0, xmax=100,
                              linestyles="dashed", color='blue')
                    ax.text(13.4, y_s.index(last_week_profile['poc_price']) + 0.3,
                            str(int(processed_data['above_poc'])) + "/" + str(int(processed_data['below_poc'])),
                            fontsize=4, style='italic')
                    ax.text(-2, y_s.index(last_week_profile['value_area_price'][0]),
                            str(last_week_profile['value_area_price'][0]), fontsize=4, style='italic')
                    ax.text(-2, y_s.index(last_week_profile['value_area_price'][1]),
                            str(last_week_profile['value_area_price'][1]), fontsize=4, style='italic')
                    ax.text(-2, y_s.index(last_week_profile['poc_price']), str(last_week_profile['poc_price']), fontsize=4,
                            style='italic')
                    lw_L = get_next_lowest_index(y_s, last_week_profile['low'])
                    lw_H = get_next_highest_index(y_s, last_week_profile['high'])
                    ax.hlines(y=lw_L, linewidth=1, xmin=0, xmax=100, color='green')
                    ax.hlines(y=lw_H, linewidth=1, xmin=0, xmax=100, color='red')
                    ax.text(-2, lw_L, str(last_week_profile['low']), fontsize=4, style='italic')
                    ax.text(-2, lw_H, str(last_week_profile['high']), fontsize=4, style='italic')

            # print(processed_data['value_area_price'])
            # print(price_bins)
            report.savefig()
            plt.clf()
    except Exception as e:
        print(day)
        print(e)
        print(traceback.format_exc())


def generate_historical_weekly_profile_chart(ticker, filtered_days, week_start_day, start_time):

    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    if not os.path.exists(reports_dir + ticker + "_weekly"):
        os.makedirs(reports_dir + ticker + "_weekly")
    files = glob.glob(reports_dir + ticker + "_weekly" + '/*')
    for f in files:
        os.remove(f)
    for day in filtered_days:
        plot_weekly_profile(ticker, day, week_start_day, start_time)

    merger = PdfFileMerger()
    files = os.listdir(reports_dir + ticker + "_weekly")
    files.sort(key=lambda f: os.path.getctime(os.path.join(reports_dir + ticker + "_weekly", f)), reverse=True)

    for filename in files:
        if filename.endswith(".pdf"):
            with open(reports_dir + ticker + "_weekly" + "/" + filename, 'rb') as source:
                tmp = PdfFileReader(source)
                merger.append(tmp)
    file_name = ticker + "_" + 'weekly_profile_chart_26_08'
    merger.write(reports_dir + file_name + '.pdf')

from config import default_symbols
def generate(tickers=['NIFTY'], days_past=7):
    dateToday = datetime.strptime('2024-04-10', '%Y-%m-%d')#date.today()
    curr_ordinal = dateToday.toordinal()
    print(curr_ordinal)
    last_ordinal = curr_ordinal-days_past
    print(last_ordinal)
    trade_days = list(range(curr_ordinal, last_ordinal, -7))
    print(trade_days)
    trade_days = [datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d') for t_day_ordinal in trade_days]
    print(trade_days)
    if len(tickers) == 0:
        tickers = default_symbols #[x.split(":")[1] for x in default_symbols]
    for ticker in tickers:
        generate_historical_weekly_profile_chart(ticker, trade_days, week_start_day="Friday", start_time="9:15:00")

generate(days_past=270)