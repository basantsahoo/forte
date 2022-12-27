"""
import os
import pandas as pd
import numpy as np
import string

#from matplotlib.finance import candlestick_ohlc
#from mpl_finance import candlestick_ohlc
from mplfinance.original_flavor import candlestick_ohlc
from settings import reports_dir
from config import default_symbols
import time
import datetime as dt
import calendar
from dateutil import tz
import plotly.graph_objects as go
import plotly
import glob

from reporting.charts import day_open_statistics,plot_profile_chart
from helper.utils import get_pivot_points, get_overlap
from profile.utils import get_next_highest_index, get_next_lowest_index
from PyPDF2 import PdfFileMerger, PdfFileReader
from profile.market_profile import HistMarketProfileService
import matplotlib
#matplotlib.use('Agg')  ### only required in unix

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
"""
from reporting.charts import box_plot_by_group, line_plot
from matplotlib.backends.backend_pdf import PdfPages
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
	get_pending_profile_dates,
	get_aggregate_option_data_ts,
	get_option_data_with_time_jump,
	get_daily_option_data)

from settings import reports_dir
from config import default_symbols
import time
from datetime import datetime
import calendar


def generate_historical_chart(ticker, filtered_days={}):
	df = get_aggregate_option_data_ts(ticker)
	#print(df.groupby('date').nth(-1).reset_index())
	df['day'] = df['date'].apply(lambda x : calendar.day_name[x.weekday()])
	with PdfPages(reports_dir + 'participant_report_' + ticker + '.pdf') as report:
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90)
		line_plot(report, df.groupby('date').nth(0).reset_index(), 'date', ['total_oi'])
		line_plot(report, df.groupby('date').nth(-1).reset_index(), 'date', ['total_oi'])
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90, filter={'day': 'Monday'})
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90, filter={'day': 'Tuesday'})
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90, filter={'day': 'Wednesday'})
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90, filter={'day': 'Thursday'})
		box_plot_by_group(report, df, 'total_oi', 'date', rotation_x=90, filter={'day': 'Friday'})


def generate(tickers=[], trade_days=[], filter={}):
	if len(tickers) == 0:
		tickers = default_symbols #[x.split(":")[1] for x in default_symbols]
	for ticker in tickers:
		tmp_trade_days = trade_days
		if len(tmp_trade_days) == 0:
			tmp_trade_days = get_filtered_days(ticker, filter)
		generate_historical_chart(ticker, tmp_trade_days)



def run():
	print('running+++++')
	tickers = ['NIFTY BANK']#['NIFTY BANK']
	generate(tickers=tickers, trade_days = ['2022-11-15'])


#run()
"""
df = get_option_data_with_time_jump('BANK NIFTY', '2022-09-27')
df['day'] = df['date'].apply(lambda x : calendar.day_name[x.weekday()])
df['pct_oi_change'] = df['total_oi'].pct_change()
df['return'] = df['spot'].pct_change()
df['regime_1'] = df['pct_oi_change'].apply(lambda x: 'E' if x > 0.02 else 'C' if x < -0.02 else 'B')
df['pcr'] = df['put_oi'] / df['call_oi']
"""
t_date = '2022-11-23'
df = get_daily_option_data('BANK NIFTY', t_date)
spot_df = get_daily_tick_data('BANK NIFTY', t_date)
spot_df = spot_df.set_index(['timestamp'])

df_cross = df.pivot_table('oi', ['timestamp'], 'instrument')
#print(df_cross)
df_cross.fillna(0, inplace=True)
option_data_cross_ts_inst = df_cross.to_dict('index')
spot_dict = spot_df.to_dict('index')
all_ts = list(option_data_cross_ts_inst.keys())
first_entry = option_data_cross_ts_inst[all_ts[0]]
oi_change_dict = {}
spot_change_dict = {}
for i in range(1, len(all_ts)):
	prev_ts_data = option_data_cross_ts_inst[all_ts[i-1]]
	prev_spot_data = spot_dict[all_ts[i-1]]
	oi_change_dict[all_ts[i]] = {}
	spot_change_dict[all_ts[i]] = round((prev_spot_data['close'] - spot_dict[all_ts[i]]['close']) if all_ts[i] in spot_dict else 0)
	for inst, oi in option_data_cross_ts_inst[all_ts[i]].items():
		oi_delta = oi - prev_ts_data[inst]
		oi_change_dict[all_ts[i]][inst] = oi_delta

for ts, cross_data in oi_change_dict.items():
	total_change = sum(cross_data.values())
	print('total_change========================' , total_change)
	total_call_oi = sum([oi for inst, oi in option_data_cross_ts_inst[ts].items() if inst[-2::] == 'CE'])
	total_put_oi = sum([oi for inst, oi in option_data_cross_ts_inst[ts].items() if inst[-2::] == 'PE'])
	put_exit = [{inst: oi_delta} for inst, oi_delta in cross_data.items() if oi_delta < 0 and inst[-2::] == 'PE']
	put_add = [{inst: oi_delta} for inst, oi_delta in cross_data.items() if oi_delta > 0 and inst[-2::] == 'PE']
	call_exit = [{inst: oi_delta} for inst, oi_delta in cross_data.items() if oi_delta < 0 and inst[-2::] == 'CE']
	call_add = [{inst: oi_delta} for inst, oi_delta in cross_data.items() if oi_delta > 0 and inst[-2::] == 'CE']
	total_put_exit = abs(sum([list(x.values())[0] for x in put_exit]))
	total_put_add = sum([list(x.values())[0] for x in put_add])
	total_call_exit = abs(sum([list(x.values())[0] for x in call_exit]))
	total_call_add = sum([list(x.values())[0] for x in call_add])

	scen = 'PE|' if total_put_exit > total_put_add else 'PA|'
	scen += ('CE|' if total_call_exit > total_call_add else 'CA|')
	total_oi_dir = 'N' if (total_put_oi/total_call_oi - 1) < -0.1  else 'P' if (total_put_oi/total_call_oi - 1) > 0.1 else 'B'
	scen += total_oi_dir
	print(scen)
	print('spot_change++', spot_change_dict.get(ts, 0))
	"""
	if total_put_exit > total_put_add:
		print('PE')
	else:
		print('PA')

	if total_call_exit > total_call_add:
		print('CE')
	else:
		print('CA')
	"""