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
from reporting.charts import day_open_statistics,plot_profile_chart
from helper.utils import get_pivot_points, get_overlap
from dynamics.profile.utils import get_next_highest_index, get_next_lowest_index
from PyPDF2 import PdfFileMerger, PdfFileReader
from dynamics.profile.market_profile import HistMarketProfileService
import matplotlib
### only required in unix
matplotlib.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def plot_daily_chart(ticker, day, period, no_of_hist_days):
	today_df = get_daily_profile_data(ticker, day)
	prev_week_data = get_pivot_points(get_prev_week_candle(ticker, day))
	#print(prev_week_data)
	final_df = today_df
	for idx in range(1, no_of_hist_days+1):
		hist_df = get_nth_day_profile_data(ticker, day, idx)
		final_df = pd.concat([hist_df, final_df])
	#final_df["date"] = final_df["date"].apply(lambda x: x.strftime('%d-%m-%Y'))
	fig = go.Figure(data=[
		go.Candlestick(x=final_df['date'], open=final_df['open'], high=final_df['high'], low=final_df['low'],
					   close=final_df['close'], name=day,  text=day)])
	#fig.layout.xaxis.type = 'category'
	fig.layout = dict(xaxis=dict(type="category"), yaxis=dict(tickformat=".1f"))
	fig.layout['xaxis']['rangeslider'] = {'visible': False}
	#fig.layout = dict(yaxis=dict(tickformat=".1f"))
	#fig.show()
	fig.update_layout(
		title_text=day +  "_daily"
	)
	try:
		fig.add_hline(round(prev_week_data['R2'], 2), line_color="red", line_width=2)
		fig.add_hline(round(prev_week_data['S2'], 2), line_color="green", line_width=2)
		fig.add_hline(round(prev_week_data['R3'], 2), line_color="red", line_width=2)
		fig.add_hline(round(prev_week_data['S3'], 2), line_color="green", line_width=2)
		#fig.add_hline(round(prev_week_data['R4'], 2), line_color="red", line_width=2)
		#fig.add_hline(round(prev_week_data['S4'], 2), line_color="green", line_width=2)
		fig.add_hline(round(prev_week_data['Pivot'], 2), line_color="blue", line_width=2)
	except:
		pass
	plotly.io.write_image(fig, reports_dir + ticker + "/" + day + '_daily.pdf', format='pdf')

#def convert
def plot_intraday_chart(ticker, day, period, no_of_hist_days, show=False):
	openings = []
	markers = []
	profile_data_list = []
	today_df = get_daily_tick_data(ticker, day)
	prev_week_data = get_pivot_points(get_prev_week_candle(ticker, day))

	#print(prev_week_data)

	today_df_cp = today_df.copy()
	today_df_cp['symbol'] = ticker
	today_df_cp = today_df_cp[['timestamp', 'symbol', 'open','high','low', 'close', 'volume']]
	profile_data_list.append(today_df_cp.to_dict('records'))


	today_df['timestamp'] = pd.to_datetime(today_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
	today_df = today_df.set_index('timestamp')
	today_df = convert_to_n_period_candles(today_df, period)
	first_15_mins = today_df.to_dict("records")[0]
	today_df = today_df.reset_index()
	final_df = today_df
	openings.append(list(today_df['timestamp'])[0])
	markers.append(get_uk_opening_time(list(today_df['timestamp'])[0]))

	for idx in range(1, no_of_hist_days+1):
		try:
			hist_df = get_nth_day_hist_data(ticker, day, idx)
			hist_df_cp = hist_df.copy()
			hist_df_cp['symbol'] = ticker
			hist_df_cp = hist_df_cp[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
			profile_data_list.append(hist_df_cp.to_dict('records'))
			hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
			hist_df = hist_df.set_index('timestamp')
			hist_df = convert_to_n_period_candles(hist_df, period)
			hist_df = hist_df.reset_index()
			final_df = pd.concat([hist_df, final_df])
			openings.append(list(hist_df['timestamp'])[0])
			markers.append(get_uk_opening_time(list(hist_df['timestamp'])[0]))
		except Exception as e:
			print(e)
	openings = [x.strftime('%d-%m') + " " + x.strftime('%H:%M') for x in openings]
	markers = [x.strftime('%d-%m') + " " + x.strftime('%H:%M') for x in markers]
	final_df["timestamp"] = final_df["timestamp"].apply(lambda x: x.strftime('%d-%m') + " " + x.strftime('%H:%M'))
	fig = go.Figure(data=[
		go.Candlestick(x=final_df['timestamp'], open=final_df['open'], high=final_df['high'], low=final_df['low'],
					   close=final_df['close'], name=day,  text=day)])

	# fig.layout = dict(xaxis=dict(type="category", categoryorder='category ascending'), yaxis=dict(tickformat=".1f"))
	fig.layout = dict(xaxis=dict(type="category"), yaxis=dict(tickformat=".1f"))
	fig.layout['xaxis']['rangeslider'] = {'visible': False}
	fig.update_layout(
		title_text=day + "_intraday      " + calendar.day_name[dt.datetime.strptime(day, '%Y-%m-%d').weekday()],
		paper_bgcolor='rgba(0,0,0,0)',
		plot_bgcolor='rgba(0,0,0,0)'
	)
	#print(markers)
	"""
	fig.add_shape(
		type='line',
		x0=list(final_df['date'])[0],
		y0=17500,
		x1=list(final_df['date'])[100],
		y1=17500,
		fillcolor='yellow')
	"""

	#fig.add_hline(17500, list(final_df['date'])[0])
	# fig.update_layout(xaxis_rangeslider_visible=False)
	for opening in openings:
		fig.add_vline(opening, line_dash="dash", line_color="black", line_width=1)

	for marker in markers:
		fig.add_vline(marker, line_dash="dash", line_color="gray", line_width=1)
	yday_profile = get_nth_day_profile_data(ticker, day, 1).to_dict('records')[0]
	#print(yday_profile)
	fig.add_hline(yday_profile['high'], line_color="darkred", line_width=2)
	fig.add_hline(yday_profile['va_h_p'], line_color="red", line_dash="dash", line_width=1)
	fig.add_hline(yday_profile['poc_price'], line_color="blue", line_dash="dash", line_width=2)
	fig.add_hline(yday_profile['va_l_p'], line_color="lightgreen", line_dash="dash", line_width=1)
	fig.add_hline(yday_profile['low'], line_color="green", line_width=2)
	try:
		fig.add_hline(round(prev_week_data['R1'],2), line_color="red", line_width=2)
		fig.add_hline(round(prev_week_data['Pivot'], 2), line_color="blue", line_width=2)
		fig.add_hline(round(prev_week_data['S1'],2), line_color="green", line_width=2)
	except:
		pass
	today_profile = get_daily_profile_data(ticker, day).to_dict('records')[0]
	fig.add_hline((today_profile['ib_l_acc'] + today_profile['ib_h_acc'])*0.5, line_color="yellow",line_dash="dash", line_width=1)
	fig.add_hrect(y0=today_profile['ib_l_acc'], y1=today_profile['ib_h_acc'], line_width=0, fillcolor="blue", opacity=0.1)

	if show:
		fig.show()
	else:
		plotly.io.write_image(fig, reports_dir + ticker + "/" + day + '_intraday.pdf', format='pdf')

	"""
	profile chart
	"""
	try:
		with PdfPages(reports_dir + ticker + "/" + day + '_profile.pdf') as report:
			y_s = []
			for data in profile_data_list:
				processor = HistMarketProfileService()
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


			layout_cols = len(profile_data_list)+1
			for dt_idx in range(len(profile_data_list)):
				data = profile_data_list[dt_idx]
				chrt_idx += 1

				processor = HistMarketProfileService()
				processor.process_input_data(data)
				processor.calculateMeasures()
				processed_data = processor.get_profile_data()[0]
				#print(processed_data)
				tick_size = processed_data['tick_size']
				price_bins = processed_data['price_bins']

				min_y_s = int(min(y_s))
				max_y_s = int(max(y_s))
				min_price_bin = int(min(price_bins))
				max_price_bin = int(max(price_bins))
				excluded_bins = []
				if min_y_s < min_price_bin:
					bin_to_add = [i for i in range(min_y_s,min_price_bin,tick_size)]
					excluded_bins.extend(bin_to_add)
				if max_y_s > max_price_bin:
					bin_to_add = [i for i in range(max_price_bin+tick_size,max_y_s+tick_size,tick_size)]
					excluded_bins.extend(bin_to_add)
				print_matrix = processed_data['print_matrix']
				df = pd.DataFrame(print_matrix.T)
				df.index = price_bins
				#print(excluded_bins)
				for p_idx in list(excluded_bins):
					df.loc[p_idx] = [ 0 for i in range(df.shape[1])]
				df = df.sort_index(axis=0)

				#print(df)
				prints = list(string.ascii_uppercase)[0:print_matrix.shape[0]]
				df.columns = prints
				first_minute = data[0]
				#print(first_minute)
				high_idx = get_next_highest_index(price_bins,first_minute['high'])
				low_idx = get_next_lowest_index(price_bins,first_minute['low'])
				#print(high_idx, low_idx)
				#print(price_bins[low_idx], price_bins[high_idx])
				open_bins = [i for i in range(int(price_bins[low_idx]), int(price_bins[high_idx]+tick_size), tick_size)]
				#print(open_bins)
				df.insert(loc=0, column='*', value=0)
				df.loc[open_bins, '*'] = 1
				df.loc[open_bins, 'A'] = 0
				#print(df)
				c_date = dt.datetime.fromtimestamp(data[0]['timestamp']).strftime('%Y-%m-%d')
				if dt_idx == len(profile_data_list)-1:
					df_tmp = df.iloc[:,:3]
					ax = fig.add_subplot(1, layout_cols, chrt_idx)
					text = day_open_statistics(first_minute, first_15_mins, yday_profile)
					#text = str(yday_profile['above_poc']) + "/" + str(yday_profile['below_poc']) + '\n' + text
					#print(processed_data)
					text = "yesterday range " + str(round(yday_profile['high'] - yday_profile['low'])) + '\n' + text

					overlap_va = get_overlap(processed_data['initial_balance'], [yday_profile['va_l_p'], yday_profile['va_h_p']])
					overlap_va_pct = round(overlap_va/(processed_data['initial_balance'][1] - processed_data['initial_balance'][0]) * 100)
					overlap_rng = get_overlap(processed_data['initial_balance'], [yday_profile['low'], yday_profile['high']])
					overlap_rng_pct = round(overlap_rng/(processed_data['initial_balance'][1] - processed_data['initial_balance'][0]) * 100)
					text = "today OB " + str(round(processed_data['initial_balance_acc'][1] - processed_data['initial_balance_acc'][0])) + " overlap " + str(overlap_va_pct)+"/" + str(overlap_rng_pct) + "/" +str(overlap_rng_pct-overlap_va_pct)+ '%\n' + text
					plot_profile_chart(ax,df_tmp,c_date,True,True,text)
					"""
					print(y_s)
					print(yday_profile)
					print(y_s.index(yday_profile['va_h_p']))
					print(y_s.index(yday_profile['va_l_p']))
					print(y_s.index(yday_profile['poc_price']))
					"""
					chrt_idx += 1
					ax.hlines(y=y_s.index(yday_profile['va_h_p']), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='red')
					ax.hlines(y=y_s.index(yday_profile['va_l_p']), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='lightgreen')
					ax.hlines(y=y_s.index(yday_profile['poc_price']), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='blue')
					ax.text(8.8, y_s.index(yday_profile['poc_price'])+0.3, str(int(yday_profile['above_poc'])) + "/" + str(int(yday_profile['below_poc'])), fontsize=5, style='italic', color="red")
					op_idx_L = get_next_lowest_index(y_s, first_minute['open'])
					op_idx_H = get_next_highest_index(y_s, first_minute['open'])
					op_idx = 0.5*(op_idx_L + op_idx_H)
					ax.text(1, op_idx, '--', fontsize=10, style='italic', color='red')
					ax.text(-2, y_s.index(yday_profile['va_l_p']) , str(yday_profile['va_l_p']), fontsize=4, style='italic')
					ax.text(-2, y_s.index(yday_profile['va_h_p']) , str(yday_profile['va_h_p']), fontsize=4, style='italic')
					ax.text(-2, y_s.index(yday_profile['poc_price']), str(yday_profile['poc_price']), fontsize=4, style='italic')
					yday_L = get_next_lowest_index(y_s, yday_profile['low'])
					#print(yday_L)
					yday_H = get_next_highest_index(y_s, yday_profile['high'])
					#print(yday_H)
					ax.hlines(y=yday_L, linewidth=1, xmin=0, xmax=100, color='green')
					ax.hlines(y=yday_H, linewidth=1, xmin=0, xmax=100, color='red')
					ax.text(-2, yday_L , str(yday_profile['low']), fontsize=4, style='italic')
					ax.text(-2, yday_H, str(yday_profile['high']), fontsize=4, style='italic')

				# ax.text(-1, y_s.index(processed_data['value_area_price'][1] , str(processed_data['value_area_price'][1])), fontsize=4, style='italic')

				#plt.axhline(y_s.index(yday_profile['va_h_p']), color="blue", linewidth=0.5)
					#plt.axhline(y_s.index(yday_profile['va_l_p']), color="blue", linewidth=0.5)
					#plt.axhline(y_s.index(yday_profile['poc_price']), color="pink", linestyle='--', linewidth=1)
				ax = fig.add_subplot(1, layout_cols, chrt_idx)

				rem_y_label = True if dt_idx > 0 else False
				plot_profile_chart(ax, df, c_date, rem_y_label)
				if not rem_y_label:
					#yday_profile['va_h_p']
					pass
				else:
					rev_ys = range(int(min(y_s)), int(max(y_s)+ tick_size), tick_size)
					ax.hlines(y=rev_ys.index(processed_data['value_area_price'][0]), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='lightgreen')
					ax.hlines(y=rev_ys.index(processed_data['value_area_price'][1]), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='red')
					ax.hlines(y=rev_ys.index(processed_data['poc_price']), linewidth=0.5, xmin=0, xmax=100, linestyles="dashed", color='blue')
					ax.text(13.4, rev_ys.index(processed_data['poc_price'])+0.3, str(int(processed_data['above_poc'])) + "/" + str(int(processed_data['below_poc'])), fontsize=4, style='italic')
					ax.text(-2, rev_ys.index(processed_data['value_area_price'][0]), str(processed_data['value_area_price'][0]), fontsize=4, style='italic')
					ax.text(-2, rev_ys.index(processed_data['value_area_price'][1]), str(processed_data['value_area_price'][1]), fontsize=4, style='italic')
					ax.text(-2, rev_ys.index(processed_data['poc_price']), str(processed_data['poc_price']), fontsize=4, style='italic')
			#print(processed_data['value_area_price'])
				#print(price_bins)
			report.savefig()
			plt.clf()
	except Exception as e:
		print(day)
		print(e)

def generate_historical_chart(ticker, filtered_days):
	if not os.path.exists(reports_dir):
		os.makedirs(reports_dir)
	if not os.path.exists(reports_dir + ticker):
		os.makedirs(reports_dir + ticker)
	files = glob.glob(reports_dir + ticker + '/*')
	for f in files:
		os.remove(f)
	#print(filtered_days)
	for day in filtered_days:
		#plot_intraday_chart('NSE:NIFTY50-INDEX', '2018-12-17','15Min', 5)
		plot_daily_chart(ticker, day['date'], '1D', 50)
		plot_intraday_chart(ticker, day['date'],'15Min', 1)

	merger = PdfFileMerger()
	files = os.listdir(reports_dir + ticker)
	files.sort(key=lambda f: os.path.getctime(os.path.join(reports_dir + ticker, f)))

	for filename in files:
		if filename.endswith(".pdf"):
			with open(reports_dir + ticker + "/" + filename, 'rb') as source:
				tmp = PdfFileReader(source)
				merger.append(tmp)
	file_name = ticker + "_" + 'historical_chart'
	merger.write(reports_dir + file_name + '.pdf')


def generate(tickers=[], trade_days=[], filter={}):
	if len(tickers) == 0:
		tickers = default_symbols #[x.split(":")[1] for x in default_symbols]
	for ticker in tickers:
		tmp_trade_days = trade_days
		if len(tmp_trade_days) == 0:
			tmp_trade_days = get_filtered_days(ticker, filter)
		generate_historical_chart(ticker, tmp_trade_days)

def email(tickers, last_day):
	print('emailing')
	for ticker in tickers:
		file_name = ticker + "_" + 'historical_chart.pdf'
		mail_content = "Daily Profile of " + ticker
		sender_address = 'insightfunnel01@gmail.com'
		receiver_address = "basant@essenvia.com"
		sender_pass = 'xafwofkjrfchitpl'
		message = MIMEMultipart()
		message['From'] = sender_address
		message['To'] = receiver_address
		message['Subject'] = 'Daily Profile of ' + ticker
		message.attach(MIMEText(mail_content, 'plain'))

		binary_pdf = open(reports_dir + file_name, 'rb')
		payload = MIMEBase('application', 'octate-stream', Name=file_name)
		payload.set_payload((binary_pdf).read())

		# enconding the binary into base64
		encoders.encode_base64(payload)

		# add header with pdf name
		payload.add_header('Content-Decomposition', 'attachment', filename=file_name)
		message.attach(payload)
		"""
		with open(reports_dir + file_name, 'rb') as f:
			text = f.read()
			message.attach(MIMEText(text))
		"""
		#message.attach(MIMEText(open(reports_dir + file_name).read()))
		# Create SMTP session for sending the mail
		session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
		session.starttls()  # enable security
		# login with mail_id and password
		session.login(sender_address, sender_pass)
		text = message.as_string()
		session.sendmail(sender_address, receiver_address, text)
		session.quit()


def run():
	tickers = default_symbols #[x.split(":")[1] for x in default_symbols]
	last_day = get_pending_profile_dates(default_symbols[0])
	generate(tickers=tickers, trade_days = last_day)
	email(tickers, last_day[0]['date'])


#generate(ticker)
#generate(ticker, filter={'day': 'Friday'}) ##this changed by me

