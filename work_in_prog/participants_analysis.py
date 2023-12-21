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

from datetime import datetime, timedelta

d = '2023-11-24 09:15'
dt = datetime.strptime(d, '%Y-%m-%d %H:%M')

candle_minutes = 15
trade_hold_period = 30
roll_period = 30


class OptionFeeder:
	def __init__(self, t_date):
		self.t_date = t_date
		call_oi_df = get_daily_option_oi_data('BANK NIFTY', t_date, 'CE')
		call_oi_df_cross = call_oi_df.pivot_table('oi', ['timestamp'], 'instrument')
		call_oi_df_cross.fillna(method='bfill', inplace=True)
		call_oi_df_cross.fillna(method='ffill', inplace=True)
		call_oi_df_cross = call_oi_df_cross[call_oi_df_cross.index % (candle_minutes * 60) == 0]
		call_oi_df_cross.to_csv('call_oi_df_cross_'+t_date+'.csv')
		self.call_oi_feed = call_oi_df_cross.to_dict('index')

		call_price_df = get_daily_option_price_data('BANK NIFTY', t_date, 'CE')
		call_price_df_cross = call_price_df.pivot_table('price', ['timestamp'], 'instrument')
		call_price_df_cross.fillna(method='bfill', inplace=True)
		call_price_df_cross.fillna(method='ffill', inplace=True)
		call_price_df_cross = call_price_df_cross[call_price_df_cross.index % (candle_minutes * 60) == 0]
		self.call_price_feed = call_price_df_cross.to_dict('index')

		call_volume_df = get_daily_option_volume_data('BANK NIFTY', t_date, 'CE')
		call_volume_df_cross = call_volume_df.pivot_table('volume', ['timestamp'], 'instrument')
		call_volume_df_cross.fillna(method='bfill', inplace=True)
		call_volume_df_cross.fillna(method='ffill', inplace=True)
		call_volume_df_cross = call_volume_df_cross[call_volume_df_cross.index % (candle_minutes * 60) == 0]
		self.call_volume_feed = call_volume_df_cross.to_dict('index')

		put_oi_df = get_daily_option_oi_data('BANK NIFTY', t_date, 'PE')

		put_oi_df_cross = put_oi_df.pivot_table('oi', ['timestamp'], 'instrument')
		put_oi_df_cross.fillna(method='bfill', inplace=True)
		put_oi_df_cross.fillna(method='ffill', inplace=True)
		put_oi_df_cross = put_oi_df_cross[put_oi_df_cross.index % (candle_minutes * 60) == 0]
		put_oi_df_cross.to_csv('put_oi_df_cross_'+t_date+'.csv')
		self.put_oi_feed = put_oi_df_cross.to_dict('index')

		put_price_df = get_daily_option_price_data('BANK NIFTY', t_date, 'PE')
		put_price_df_cross = put_price_df.pivot_table('price', ['timestamp'], 'instrument')
		put_price_df_cross.fillna(method='bfill', inplace=True)
		put_price_df_cross.fillna(method='ffill', inplace=True)
		put_price_df_cross = put_price_df_cross[put_price_df_cross.index % (candle_minutes * 60) == 0]
		self.put_price_feed = put_price_df_cross.to_dict('index')

		put_volume_df = get_daily_option_volume_data('BANK NIFTY', t_date, 'PE')
		put_volume_df_cross = put_volume_df.pivot_table('volume', ['timestamp'], 'instrument')
		put_volume_df_cross.fillna(method='bfill', inplace=True)
		put_volume_df_cross.fillna(method='ffill', inplace=True)
		put_volume_df_cross = put_volume_df_cross[put_volume_df_cross.index % (candle_minutes * 60) == 0]
		put_volume_df_cross.to_csv('put_volume_df_cross.csv')
		self.put_volume_feed = put_volume_df_cross.to_dict('index')



		spot_df = get_daily_tick_data('BANK NIFTY', t_date)
		spot_df_cross = spot_df.set_index(['timestamp'])
		spot_df_cross = spot_df_cross[spot_df_cross.index % (candle_minutes * 60) == 0]
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
		self.max_oi = 0
		self.attention_oi = 0
		self.minutes_past = 0

	def oi_feed(self, oi_feed):

		for inst, oi in oi_feed.items():
			if inst not in self.open_int_series:
				self.open_int_series[inst] = []
			self.open_int_series[inst].append(oi)
		total_oi = sum(oi_feed.values())
		self.total_oi_series.append(total_oi)
		if total_oi > self.max_oi:
			self.max_oi = total_oi
		if total_oi > self.attention_oi:
			self.attention_oi = total_oi

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
		signal = 0
		if len(self.total_oi_series) >= roll_period/candle_minutes:
			last_oi = self.total_oi_series[-1]
			mean_oi = np.mean(self.total_oi_series[-int(roll_period/candle_minutes):-1])
			if (last_oi*1.00/mean_oi) -1 > 0.01:
				#print('Buildup++++++')
				pass
			elif (last_oi*1.00/self.attention_oi) -1 < -0.05:
				print('covering----')
				#print((last_oi * 1.00 / self.attention_oi) - 1)
				self.attention_oi = last_oi
				signal = 1
			else:
				#print('balance====')
				pass
		return signal

	def get_long_call_option_strike(self, spot):
		return str(int(spot/100)*100 + 500)

	def get_long_put_option_strike(self, spot):
		return str(int(spot/100)*100 - 500)

	def get_option_ltp(self, option_strike):
		return self.price_series[option_strike][-1]

class PutAnalyser(CallAnalyser):
	def __init__(self):
		CallAnalyser.__init__(self)

class SpotAnalyser:
	def __init__(self):
		self.price_series = {}
		self.ltp = 0

	def price_feed(self, spot_feed):
		self.ltp = spot_feed['close']
		for inst, oi in spot_feed.items():
				if inst not in self.price_series:
					self.price_series[inst] = []
				self.price_series[inst].append(oi)

class Trade:
	def __init__(self, instrument, position, entry_price, trade_duration):
		self.instrument = instrument
		self.position = position
		self.entry_price = entry_price
		self.trade_duration = trade_duration
		self.time_passed = -1
		self.closed = False
		self.pnl = 0
		self.exit_price = 0
		self.entry_time = 0
		self.exit_time = 0

	def evaluate(self):
		self.time_passed += 1
		if not self.closed and self.time_passed >= self.trade_duration:
			return True
		else:
			return False

	def close(self, exit_price):
		self.pnl = self.position * (exit_price - self.entry_price)
		self.exit_price = exit_price
		self.closed = True

class OptionChainAnalyser:
	def __init__(self):
		self.call_analyser = CallAnalyser()
		self.put_analyser = PutAnalyser()
		self.spot_analyser = SpotAnalyser()
		self.trade_book = []
		self.minutes_past = -1

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
		self.minutes_past += 1

		signal = self.call_analyser.analyse()
		if signal:
			spot_price = self.spot_analyser.ltp
			print('spot_price++++', spot_price)
			option_strike = self.call_analyser.get_long_call_option_strike(spot_price)
			option_price = self.call_analyser.get_option_ltp(option_strike)
			trade = Trade((option_strike, 'CE'), 1, option_price, trade_hold_period/candle_minutes)
			trade.entry_time = self.minutes_past
			self.trade_book.append(trade)
		"""
		signal = self.put_analyser.analyse()
		if signal:
			spot_price = self.spot_analyser.ltp
			print('spot_price++++', spot_price)
			option_strike = self.put_analyser.get_long_put_option_strike(spot_price)
			option_price = self.put_analyser.get_option_ltp(option_strike)
			trade = Trade((option_strike, 'PE'), 1, option_price, trade_hold_period/candle_minutes)
			trade.entry_time = self.minutes_past
			self.trade_book.append(trade)
		"""
		for trade in self.trade_book:
			if trade.evaluate():
				analyser = self.put_analyser if trade.instrument[1] == 'PE' else self.call_analyser
				option_price = analyser.get_option_ltp(trade.instrument[0])
				trade.close(option_price)
				trade.exit_time = self.minutes_past

	def print_trades(self):
		print('==================================print_trades==============================')
		total_pnl = 0
		for trade in self.trade_book:
			total_pnl += trade.pnl
			print('instrument ====', trade.instrument)
			print('entry_time ====', (dt + timedelta(minutes=trade.entry_time * candle_minutes)).strftime('%H:%M'))
			print('exit_time ====', (dt + timedelta(minutes=trade.exit_time * candle_minutes)).strftime('%H:%M'))
			print('entry_price ====', trade.entry_price)
			print('exit_price ====', trade.exit_price)
			print('pnl=======================================', trade.pnl)
		print('total pnl=======', total_pnl)
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
		self.option_chain_analyser.print_trades()



t_dates = ['2023-11-30', '2023-12-01', '2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07', '2023-12-08', '2023-12-11', '2023-12-12', '2023-12-13', '2023-12-14', '2023-12-15']
t_dates = ['2023-12-07', '2023-12-08', '2023-12-11', '2023-12-12', '2023-12-13']
for t_date in t_dates:
	print('*********************************  t_date @@@@@@@@@', t_date)
	bt_machine = BackTester(t_date)
	bt_machine.run()
