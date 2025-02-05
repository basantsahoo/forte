from db.market_data import get_prev_week_minute_data_by_start_day, get_curr_week_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from datetime import datetime, date
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
from config import default_symbols
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders



def plot_weekly_profile(symbol, day, week_start_day, start_time):
    t_day = datetime.strptime(day, '%Y-%m-%d') if type(day) == str else day
    t_day_ordinal = t_day.toordinal()
    recent_week_start_str = datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d')
    profile_data_list = []
    df = get_curr_week_minute_data_by_start_day(symbol, recent_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df['symbol'] = symbol
    df['ltp'] = df['close']
    profile_data_list.append(df.to_dict('records'))
    df = get_prev_week_minute_data_by_start_day(symbol, recent_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df['symbol'] = symbol
    df['ltp'] = df['close']
    profile_data_list.append(df.to_dict('records'))
    try:
        with PdfPages(reports_dir + symbol +"_weekly" + "/" + day + "_" + week_start_day + '_profile.pdf') as report:
            y_s = []
            for data in profile_data_list:
                processor = WeeklyMarketProfileService()
                processor.set_trade_date_from_time(data[0]['timestamp'], data[-1]['timestamp'])
                processor.process_input_data(data)
                processor.calculateMeasures()
                processed_data = processor.get_profile_data()[0]
                price_bins = processed_data['price_bins']
                y_s.extend(list(price_bins))
            y_s = list(set(y_s))
            y_s.sort()
            chrt_idx = 0
            profile_data_list.reverse()
            fig = plt.figure()
            plt.tight_layout()

            layout_cols = len(profile_data_list) + 1
            for dt_idx in range(len(profile_data_list)):
                data = profile_data_list[dt_idx]
                chrt_idx += 1
                processor = WeeklyMarketProfileService()
                processor.set_trade_date_from_time(data[0]['timestamp'], data[-1]['timestamp'])
                processor.process_input_data(data)
                processor.calculateMeasures()
                processed_data = processor.get_profile_data()[0]
                if dt_idx < len(profile_data_list)-1:
                    last_week_profile = processed_data
                price_bins = processed_data['price_bins']
                tick_size = processed_data['tick_size']

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
                print_matrix = processed_data['print_matrix']
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
                plot_profile_chart(ax, df, c_date, rem_y_label)
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
    file_name = ticker + "_" + 'weekly_profile_chart'
    merger.write(reports_dir + file_name + '.pdf')


def generate(tickers=[], days_past=7):
    dateToday = date.today() #datetime.strptime('2022-12-26', '%Y-%m-%d')
    curr_ordinal = dateToday.toordinal()
    last_ordinal = curr_ordinal-days_past
    trade_days = list(range(curr_ordinal, last_ordinal, -7))
    trade_days = [datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d') for t_day_ordinal in trade_days]
    if len(tickers) == 0:
        tickers = default_symbols #[x.split(":")[1] for x in default_symbols]
    for ticker in tickers:
        generate_historical_weekly_profile_chart(ticker, trade_days, week_start_day="Friday", start_time="9:15:00")

def email(tickers):
    print('emailing')
    for ticker in tickers:
        file_name = ticker + "_" + 'weekly_profile_chart.pdf'
        mail_content = "Current Week Profile of " + ticker
        sender_address = 'insightfunnel01@gmail.com'
        receiver_address = "basant@essenvia.com"
        sender_pass = 'xafwofkjrfchitpl'
        message = MIMEMultipart()
        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = "Current Week Profile of " + ticker
        message.attach(MIMEText(mail_content, 'plain'))

        binary_pdf = open(reports_dir + file_name, 'rb')
        payload = MIMEBase('application', 'octate-stream', Name=file_name)
        payload.set_payload((binary_pdf).read())

        # enconding the binary into base64
        encoders.encode_base64(payload)

        # add header with pdf name
        payload.add_header('Content-Decomposition', 'attachment', filename=file_name)
        message.attach(payload)
        # Create SMTP session for sending the mail
        session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
        session.starttls()  # enable security
        # login with mail_id and password
        session.login(sender_address, sender_pass)
        text = message.as_string()
        session.sendmail(sender_address, receiver_address, text)
        session.quit()

def run():
    tickers = default_symbols
    generate(tickers=tickers, days_past=7)
    email(tickers)

#run()
#generate()