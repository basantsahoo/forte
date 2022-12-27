import time
import numpy as np
from itertools import compress
import pandas as pd
import os
import datetime
from dateutil.relativedelta import relativedelta
from db.db_engine import get_db_engine
from profile.market_profile import HistMarketProfileService
from fyers.historical_data import FyersFeed
from config import default_symbols
import helper.utils as helper_utils
# NSE:NIFTYBANK-INDEX
# NSE:NIFTY50-INDEX
#https://feedback.truedata.in/knowledge-base/article/market-data-api-ws_api-symbol-lists
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
	hist_fetcher = FyersFeed.getInstance()
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
			for d in range(1,delta.days+1):
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
			start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
			end_ts = int(time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S")))
			response = hist_fetcher.get_hist_data(helper_utils.get_fyers_index_symbol(symbol),str(start_ts),str(end_ts))
			#print(response)
			hist_data = response.get('candles')
			if hist_data:
				if IDX == 1:
					# print(hist_data)
					pass

				try:
					converted = []
					for minute_candle in hist_data:
						tick_date_time = datetime.datetime.fromtimestamp(minute_candle[0])
						if not int(tick_date_time.strftime("%H")) > 15:
							time_string = tick_date_time.strftime("%H") + ":" + tick_date_time.strftime(
								"%M") + ":" + tick_date_time.strftime("%S")
							tmp = {
								'date': trade_day,
								'time_string': time_string,
								'timestamp': minute_candle[0],
								'symbol': helper_utils.get_nse_index_symbol(symbol),
								'open': minute_candle[1],
								'high': minute_candle[2],
								'low': minute_candle[3],
								'close': minute_candle[4],
								'volume': minute_candle[5]
							}
							converted.append(tmp)
					df = pd.DataFrame(converted)
					df.to_sql('minute_data', conn, if_exists="append", index=False)
					#print(df.head())
				except Exception as e:
					print(trade_day, symbol)
					print(e)


#download(['2022-02-03'])
def run():
	download()
	#download(['2022-03-17'], ['NSE:NIFTY2232417000PE'])