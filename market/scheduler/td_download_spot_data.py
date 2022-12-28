
import time
import numpy as np
from itertools import compress
import pandas as pd
import os
import datetime
from dateutil.relativedelta import relativedelta
from db.db_engine import get_db_engine
from truedata_ws.websocket.TD_hist import HistoricalREST, cache_symbol_id
#from truedata_ws.websocket.TD import TD


import infrastructure.truedata.settings as td_settings
from config import default_symbols
import helper.utils as helper_utils
import logging

log_format = "(%(asctime)s) %(levelname)s :: %(message)s (PID:%(process)d Thread:%(thread)d)"
log_formatter = logging.Formatter(log_format)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.WARNING)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger('hist_downloader')
logger.addHandler(log_handler)
logger.setLevel(log_handler.level)
logger.debug("Logger ready...")




# NSE:NIFTYBANK-INDEX
# NSE:NIFTY50-INDEX

def get_last_loaded_date(symbol):
	engine = get_db_engine()
	conn = engine.connect()
	qry = "select max(date) as last_date from minute_data where symbol = '{}'".format(symbol)
	df = pd.read_sql_query(qry, con=conn)
	print(df)
	last_date = df['last_date'].to_list()[0] if df['last_date'].to_list() else None
	conn.close()
	return last_date


def download(trade_days=[], symbols=[]):
	if len(symbols) == 0:
		symbols = default_symbols
	#symbols = [helper_utils.get_fyers_index_symbol(symbol) for symbol in default_symbols]
	hist_fetcher = HistoricalREST(td_settings.user_name, td_settings.pass_word, td_settings.hist_url, None, logger)
	#td_obj = TD(td_settings.user_name, td_settings.pass_word, log_level=logging.WARNING)

	engine = get_db_engine()


	conn = engine.connect()
	for symbol in symbols:
		tmp_trade_days = trade_days
		if len(tmp_trade_days) == 0:
			last_date = get_last_loaded_date(helper_utils.get_nse_index_symbol(symbol))
			if last_date is None:
				last_date = datetime.datetime(2018, 12, 10).date()
			#print(last_date)
			curr_date = datetime.datetime.now().date()
			delta = curr_date - last_date
			#print(delta.days)
			for d in range(1, delta.days+1):
				day_from_now = last_date + relativedelta(days=d)
				date_formated = day_from_now.strftime("%Y-%m-%d")
				tmp_trade_days.append(date_formated)
			print(tmp_trade_days)
		IDX = 0
		for trade_day in tmp_trade_days:
			print(trade_day)
			IDX += 1
			start_str = trade_day + " 09:15:00"
			end_str = trade_day + " 15:30:30"
			start_ts = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
			end_ts = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
			end_time = end_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
			start_time = start_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
			hist_data = hist_fetcher.get_historic_data(helper_utils.get_td_index_symbol(symbol), start_time=start_time, end_time=end_time, bar_size="1 min")
			if hist_data:
				if IDX == 1:
					# print(hist_data)
					pass

				try:
					converted = []
					for minute_candle in hist_data:
						tick_date_time = minute_candle['time']
						"""
						print(tick_date_time)
						print(int(tick_date_time.strftime("%H")))
						print(int(time.mktime(time.strptime(tick_date_time.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"))))
						print(1)
						"""
						if not int(tick_date_time.strftime("%H")) > 15:
							time_string = tick_date_time.strftime("%H:%M:%S")
							tmp = {
								'date': trade_day,
								'time_string': time_string,

								'timestamp': int(time.mktime(time.strptime(tick_date_time.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"))),
								'symbol': helper_utils.get_nse_index_symbol(symbol),
								'open': minute_candle['o'],
								'high': minute_candle['h'],
								'low': minute_candle['l'],
								'close': minute_candle['c'],
								'volume': minute_candle['v']
							}
							converted.append(tmp)
					df = pd.DataFrame(converted)
					df.to_sql('minute_data', conn, if_exists="append", index=False)
				except Exception as e:
					print(trade_day, symbol)
					print(e)
	conn.close()

#download(['2022-02-03'])
def run():
	download()
	#download(['2022-10-28'])
	#download(['2022-03-17'], ['NSE:NIFTY2232417000PE'])