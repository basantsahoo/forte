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
get_daily_call_option_data,
get_daily_put_option_data)

from backtest.settings import reports_dir
from config import default_symbols
import time
from datetime import datetime
import calendar

class OptionFeeder:
	def __init__(self, t_date):
		self.t_date = t_date
		call_df = get_daily_call_option_data('BANK NIFTY', t_date)
		call_df_cross = call_df.pivot_table('oi', ['timestamp'], 'instrument')
		call_df_cross.fillna(method='bfill', inplace=True)
		call_df_cross.fillna(method='ffill', inplace=True)
		self.call_feed = call_df_cross.to_dict('index')
		put_df = get_daily_put_option_data('BANK NIFTY', t_date)
		put_df_cross = put_df.pivot_table('oi', ['timestamp'], 'instrument')
		put_df_cross.fillna(method='bfill', inplace=True)
		put_df_cross.fillna(method='ffill', inplace=True)
		self.put_feed = put_df_cross.to_dict('index')
		spot_df = get_daily_tick_data('BANK NIFTY', t_date)
		spot_df_cross = spot_df.set_index(['timestamp'])
		self.spot_feed = spot_df_cross.to_dict('index')
		self.all_ts = list(option_data_cross_ts_inst.keys())
		self.all_ts.sort()

	def generate_feed(self):
		ts = all_ts.pop(0)
		self.call_feed[ts]

class CallAnalyser:
	def __init__(self):
		self.open_int_series = {}
		self.price_series = {}

	def oi_feed(self, oi_feed):
		for inst, oi in oi_feed.items():
				if inst not in self.open_int_series:
					self.open_int_series[inst] = []
				self.open_int_series[inst].append(oi)


class OptionAnalyser:
	def __init__(self):
		self.call_analyser = CallAnalyser()

	def call_oi_feed(self, call_oi_feed):
		self.call_analyser.oi_feed(call_oi_feed)





t_date = '2023-12-15'
df = get_daily_option_data('BANK NIFTY', t_date)
call_df = get_daily_call_option_data('BANK NIFTY', t_date)
call_df_cross = call_df.pivot_table('oi', ['timestamp'], 'instrument')
print(call_df_cross.to_dict('index'))
put_df = get_daily_put_option_data('BANK NIFTY', t_date)
spot_df = get_daily_tick_data('BANK NIFTY', t_date)
spot_df = spot_df.set_index(['timestamp'])
spot_df.to_csv('spot_df.csv')
df_cross = df.pivot_table('oi', ['timestamp'], 'instrument')
df_cross.fillna(method='bfill', inplace=True)
df_cross.fillna(method='ffill', inplace=True)
#df_cross.to_csv('option_cross.csv')
#df_cross.fillna(0, inplace=True)
option_data_cross_ts_inst = df_cross.to_dict('index')
spot_dict = spot_df.to_dict('index')
print("Day range====", spot_df['high'].max() - spot_df['low'].min())

all_ts = list(option_data_cross_ts_inst.keys())
all_ts.sort()
first_entry = option_data_cross_ts_inst[all_ts[0]]
oi_change_dict = {}
spot_change_dict = {}
for i in range(1, len(all_ts)):
	prev_ts_option_data = option_data_cross_ts_inst[all_ts[i-1]]
	prev_spot_data = spot_dict[all_ts[i-1]]
	oi_change_dict[all_ts[i]] = {}
	spot_change_dict[all_ts[i]] = {'change': round((spot_dict[all_ts[i]]['close'] - prev_spot_data['close']) if all_ts[i] in spot_dict else 0),
	'level': spot_dict[all_ts[i]]['close'] if  all_ts[i] in spot_dict else 0}
	for inst, oi in option_data_cross_ts_inst[all_ts[i]].items():
		if inst in ['47700_CE', '47800_CE', '47900_CE', '48000_CE', '48100_CE', '48200_CE', '48300_CE', '48400_CE', '48500_CE', '47000_PE', '47100_PE', '47200_PE', '47300_PE', '47400_PE', '47500_PE', '47600_PE', '47700_PE', '47800_PE', '47900_PE', '48000_PE']:
			oi_delta = oi - prev_ts_option_data[inst]
			oi_change_dict[all_ts[i]][inst] = oi_delta

cum_change = 0
for ts, cross_data in oi_change_dict.items():
	total_change = sum(cross_data.values())
	print('ts=== ',ts, ' total_change========================' , total_change)
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
	#scen = ('CE|' if total_call_exit > total_call_add else 'CA|' if total_call_exit < total_call_add else '')
	print(scen)
	cum_change += spot_change_dict.get(ts, {}).get('change', 0)
	print('spot++', spot_change_dict.get(ts, {}).get('level', 0))
	print('cum_change++', cum_change)
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




"""
At a time index must be in balance
During balance activities must be minimum
A momentum occurs if there is activity in either side

Opening 
==========

In range means there is no overnight view change. 
Gap up / Down means there are overnight orders 
When Gapup down happens, Seller position has changed. There is a loss limit which 
they tolerate and bring market back to their range so that they can be profitable
If they can't tolerate loss, market momentum continue

What is the profit they look for over weekend? Monday, Tuesday, Thursday etc
Momentum generally doesn't continue post 3:15. But what happens if it continues?

When market decides to move, Some activities must happen in option market
We need to know what happens 

We can model it in following ways 
Identify a region of balance
Identify trend 
Indentify reversal 
Identify resistance 

Sometime When market trend in second half, sellers hold it for sometime
I think when their profit target is met, they release the market for movement  
 
"""