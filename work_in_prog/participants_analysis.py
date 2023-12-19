import numpy as np
import sys
from pathlib import Path
import sys
root_path = str(Path(__file__).resolve().parent.parent)
sys.path.append(root_path)

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
	get_daily_option_data,
get_daily_option_oi_data,
get_daily_option_price_data,
get_daily_option_volume_data)

from backtest.settings import reports_dir
from config import default_symbols
import time
from datetime import datetime
import calendar

class OptionFeeder:
	def __init__(self, t_date):
		self.t_date = t_date
		call_oi_df = get_daily_option_oi_data('BANK NIFTY', t_date, 'CE')
		call_oi_df_cross = call_oi_df.pivot_table('oi', ['timestamp'], 'instrument')
		call_oi_df_cross.fillna(method='bfill', inplace=True)
		call_oi_df_cross.fillna(method='ffill', inplace=True)
		self.call_oi_feed = call_oi_df_cross.to_dict('index')

		call_price_df = get_daily_option_price_data('BANK NIFTY', t_date, 'CE')
		call_price_df_cross = call_price_df.pivot_table('price', ['timestamp'], 'instrument')
		call_price_df_cross.fillna(method='bfill', inplace=True)
		call_price_df_cross.fillna(method='ffill', inplace=True)
		self.call_price_feed = call_price_df_cross.to_dict('index')

		call_volume_df = get_daily_option_volume_data('BANK NIFTY', t_date, 'CE')
		call_volume_df_cross = call_volume_df.pivot_table('volume', ['timestamp'], 'instrument')
		call_volume_df_cross.fillna(method='bfill', inplace=True)
		call_volume_df_cross.fillna(method='ffill', inplace=True)
		self.call_volume_feed = call_volume_df_cross.to_dict('index')

		put_oi_df = get_daily_option_oi_data('BANK NIFTY', t_date, 'PE')
		put_oi_df_cross = put_oi_df.pivot_table('oi', ['timestamp'], 'instrument')
		put_oi_df_cross.fillna(method='bfill', inplace=True)
		put_oi_df_cross.fillna(method='ffill', inplace=True)
		self.put_oi_feed = put_oi_df_cross.to_dict('index')

		put_price_df = get_daily_option_price_data('BANK NIFTY', t_date, 'PE')
		put_price_df_cross = put_price_df.pivot_table('price', ['timestamp'], 'instrument')
		put_price_df_cross.fillna(method='bfill', inplace=True)
		put_price_df_cross.fillna(method='ffill', inplace=True)
		self.put_price_feed = put_price_df_cross.to_dict('index')

		put_volume_df = get_daily_option_volume_data('BANK NIFTY', t_date, 'PE')
		put_volume_df_cross = put_volume_df.pivot_table('volume', ['timestamp'], 'instrument')
		put_volume_df_cross.fillna(method='bfill', inplace=True)
		put_volume_df_cross.fillna(method='ffill', inplace=True)
		self.put_volume_feed = put_volume_df_cross.to_dict('index')



		spot_df = get_daily_tick_data('BANK NIFTY', t_date)
		spot_df_cross = spot_df.set_index(['timestamp'])
		self.spot_feed = spot_df_cross.to_dict('index')
		self.all_ts = list(self.spot_feed.keys())
		self.all_ts.sort()
		self.pending_data = True
		self.call_back = None

	def generate_feed(self):
		if self.all_ts:
			ts = self.all_ts.pop(0)
			self.call_back('call_oi_feed', self.call_oi_feed[ts])
			self.call_back('call_price_feed', self.call_price_feed[ts])
			self.call_back('call_volume_feed', self.call_volume_feed[ts])
			self.call_back('put_oi_feed', self.put_oi_feed[ts])
			self.call_back('put_price_feed', self.put_price_feed[ts])
			self.call_back('put_volume_feed', self.put_volume_feed[ts])
			self.call_back('spot_feed', self.spot_feed[ts])
			self.call_back('generate_signal', {})
		else:
			self.pending_data = False

class CallAnalyser:
	def __init__(self):
		self.open_int_series = {}
		self.price_series = {}
		self.volume_series = {}
		self.total_oi_series = []
		self.total_volume_series = []

	def oi_feed(self, oi_feed):
		for inst, oi in oi_feed.items():
			if inst not in self.open_int_series:
				self.open_int_series[inst] = []
			self.open_int_series[inst].append(oi)
		self.total_oi_series.append(sum(oi_feed.values()))

	def price_feed(self, price_feed):
		for inst, price in price_feed.items():
			if inst not in self.price_series:
				self.price_series[inst] = []
			self.price_series[inst].append(price)

	def volume_feed(self, volume_feed):
		for inst, volume in volume_feed.items():
			if inst not in self.volume_series:
				self.volume_series[inst] = []
			self.volume_series[inst].append(volume)
		self.total_volume_series.append(sum(volume_feed.values()))

	def analyse(self):
		if len(self.total_oi_series) >= 6:
			last_oi = self.total_oi_series[-1]
			mean_oi = np.mean(self.total_oi_series[-6:-1])
			if (last_oi*1.00/mean_oi) -1 > 0.01:
				print('Buildup++++++')
			elif (last_oi*1.00/mean_oi) -1 < -0.05:
				print('covering----')
				print((last_oi * 1.00 / mean_oi) - 1)
			else:
				print('balance====')

class PutAnalyser(CallAnalyser):
	def __init__(self):
		CallAnalyser.__init__(self)

class SpotAnalyser:
	def __init__(self):
		self.price_series = {}

	def price_feed(self, spot_feed):
		for inst, oi in spot_feed.items():
				if inst not in self.price_series:
					self.price_series[inst] = []
				self.price_series[inst].append(oi)

class OptionChainAnalyser:
	def __init__(self):
		self.call_analyser = CallAnalyser()
		self.put_analyser = PutAnalyser()
		self.spot_analyser = SpotAnalyser()

	def call_oi_feed(self, call_oi_feed):
		self.call_analyser.oi_feed(call_oi_feed)

	def call_price_feed(self, call_price_feed):
		self.call_analyser.price_feed(call_price_feed)

	def call_volume_feed(self, call_volume_feed):
		self.call_analyser.volume_feed(call_volume_feed)

	def put_oi_feed(self, put_oi_feed):
		self.put_analyser.oi_feed(put_oi_feed)

	def put_price_feed(self, put_price_feed):
		self.put_analyser.price_feed(put_price_feed)

	def put_volume_feed(self, put_volume_feed):
		self.put_analyser.volume_feed(put_volume_feed)

	def spot_feed(self, spot_feed):
		self.spot_analyser.price_feed(spot_feed)

	def generate_signal(self):
		self.call_analyser.analyse()



class BackTester:
	def __init__(self, t_date):
		self.t_date = t_date
		self.option_feeder = OptionFeeder(t_date)
		self.option_feeder.call_back = self.process_feed
		self.option_chain_analyser = OptionChainAnalyser()

	def process_feed(self, category, feed):
		if category == 'call_oi_feed':
			self.option_chain_analyser.call_oi_feed(feed)

		if category == 'call_price_feed':
			self.option_chain_analyser.call_price_feed(feed)

		if category == 'call_volume_feed':
			self.option_chain_analyser.call_volume_feed(feed)

		if category == 'put_oi_feed':
			self.option_chain_analyser.put_oi_feed(feed)

		if category == 'put_price_feed':
			self.option_chain_analyser.put_price_feed(feed)

		if category == 'put_volume_feed':
			self.option_chain_analyser.put_volume_feed(feed)

		if category == 'spot_feed':
			self.option_chain_analyser.spot_feed(feed)

		if category == 'generate_signal':
			self.option_chain_analyser.generate_signal()

	def run(self):
		while self.option_feeder.pending_data:
			self.option_feeder.generate_feed()



t_date = '2023-12-15'
bt_machine = BackTester(t_date)
bt_machine.run()
