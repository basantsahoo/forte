from settings import market_profile_db,reports_dir
from db.db_engine import get_db_engine
from dynamics.profile.market_profile import HistMarketProfileService
from portfolio.backtest_portfolio_manager import PortfolioManager
import json
from dynamics.profile.utils import NpEncoder
import pandas as pd
import numpy as np
from datetime import datetime
from trend.tick_price_smoothing import PriceInflexDetector
#from trend.tick_price_smoothing_bkp import PriceInflexDetector
import itertools

engine = get_db_engine()
# NIFTYBANK-INDEX
default_symbols =  ['NSE:NIFTY50-INDEX']


def get_ratios(grid):
	rats = [[round((x / y - 1), 6) for y in grid] for x in grid]
	rats = [[float(x) if x != 0 else 1024 for x in y] for y in rats]
	return rats



def get_grid2():
	p0 = 100
	p1_on_p0_slabs = [0.002, 0.02, 0.002]
	rng = np.arange(p1_on_p0_slabs[0], p1_on_p0_slabs[1] + p1_on_p0_slabs[2], p1_on_p0_slabs[2])
	p1_prices = [p0 * (1+ ret) for ret in rng]
	p0_p1_prices = list(itertools.product([p0], p1_prices))
	p0_p1_prices = [list(x) for x in p0_p1_prices]
	p2_on_p1_slabs = [-0.002, -0.018, -0.002]
	rng = np.arange(p2_on_p1_slabs[0], p2_on_p1_slabs[1] + p2_on_p1_slabs[2], p2_on_p1_slabs[2])
	p2_prices = [p1 * (1+ ret) for ret in rng for p1 in p1_prices]
	p0_p1_p2_prices = list(itertools.product(p0_p1_prices, p2_prices))

	def flatten(L):
		for item in L:
			try:
				yield from flatten(item)
			except TypeError:
				yield item

	p0_p1_p2_flat_list = [list(flatten(l)) for l in p0_p1_p2_prices]
	p0_p1_p2_flat_list = [x for x in p0_p1_p2_flat_list if (x[2] < x[1]) and  (x[2] >= x[0])]
	#print(len(p0_p1_p2_flat_list))
	p3_on_p1_slabs = [-0.003, 0.003, 0.02]
	rng = np.arange(p3_on_p1_slabs[0], p3_on_p1_slabs[1] + p3_on_p1_slabs[2], p3_on_p1_slabs[2])
	p3_prices = [p1 * (1+ ret) for ret in rng for p1 in p1_prices]
	#print(len(p3_prices))
	p0_p1_p2_p3_prices = list(itertools.product(p0_p1_p2_flat_list, p3_prices))
	p0_p1_p2_p3_flat_list = [list(flatten(l)) for l in p0_p1_p2_p3_prices]
	p0_p1_p2_p3_flat_list = [x for x in p0_p1_p2_p3_flat_list if x[2] < x[3]]
	p0_p1_p2_p3_flat_list = [x for x in p0_p1_p2_p3_flat_list if (x[1]*(1+0.003) >= x[3] and x[1]*(1-0.003) <= x[3])]
	print('total grids for ', len(p0_p1_p2_p3_flat_list))
	return p0_p1_p2_p3_flat_list



def get_grid():
	grid_range = [
		[None, [-0.002, -0.01, -0.002], [0.0, -0.008, -0.002], [-0.002, -0.012, -0.002]],
		[[0.002, 0.01, 0.002], None, [0.002, 0.01, 0.002], [-0.005, 0.005, 0.002]],
		[[0.0, 0.008, 0.002], [-0.002, -0.01, -0.002], None, [-0.0015, -0.0115, -0.002]],
	]
	pattern_grid = []
	for lst in grid_range:
		grid = []
		for itm in lst:
			if itm is None:
				grid.append([1024])
			else:
				rng = np.arange(itm[0], itm[1] + itm[2], itm[2])
				bins = []
				for i in range(len(rng) - 1):
					bins.append([rng[i], rng[i + 1]])
				grid.append(bins)
		grids = list(itertools.product(*grid))
		pattern_grid.append(grids)

	# print(pattern_grid)

	final_grids = []
	grid_length = len(pattern_grid[0])
	for i in range(grid_length):
		tmp_arr = []
		for item in pattern_grid:
			tmp_arr.append(list(item[i]))
		final_grids.append(tmp_arr)
	return final_grids


def generate_pattern_config(pattern, price_target,time=30, ratios=None):

	if pattern == 'DT':
		first_ratio = [1024, 1024, 1024, 1024]
		second_ratio = [ratios[0], 1024, 1024, 1024]
		third_ratio = [1024, ratios[1], 1024, 1024]
		forth_ratio = [1024, 1024, ratios[2], 1024]

		config = {
			'len': 4,
			'pattern': ['SPL', 'SPH', 'SPL', 'SPH'],
			'trade_type': 'SELL',
			'exit': {'time': time, 'price': price_target}
		}
		if len(ratios) < len(config['pattern']):
			ratios.append([1024 for x in range(len(config['pattern']))])
		config['params'] = ratios
		return config


def get_all_days(symbol):
	print('called again')
	conn = engine.connect()
	stmt_1 = "select distinct date from minute_data where symbol = '{0}' order by date desc"
	rs = conn.execute(stmt_1.format(symbol))
	days = list(rs)
	days = [x[0] for x in days]
	conn.close()
	return days



def get_data(symbol, trade_day):
	stmt_1 = "select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and date = date('{1}') order by timestamp asc"
	conn = engine.connect()
	rs = conn.execute(stmt_1.format(symbol, trade_day))
	hist_data = list(rs)
	hist_data = [list(x) for x in hist_data]
	converted = []
	for minute_candle in hist_data:
		tmp = {
			'timestamp': minute_candle[0],
			'symbol': symbol,
			'open': minute_candle[1],
			'high': minute_candle[2],
			'low': minute_candle[3],
			'close': minute_candle[4],
			'volume': minute_candle[5]
		}
		converted.append(tmp)
	conn.close()
	return converted #(x for x in converted)

results = []
grids = get_grid2()
grids = [[100,100.59, 100.33, 100.53 ]]
days = get_all_days(default_symbols[0])
counter = 1
for grid in grids:
	print(counter)
	print(grid)
	ratios = get_ratios(grid)
	#print(ratios)
	pattern_config = generate_pattern_config('DT', 0.003, 30, ratios)
	#print(pattern_config)
	for day in days[0:100]:
		print(day)
		start_time = datetime.now()
		price_list = get_data(default_symbols[0], day)
		pm = PortfolioManager(trade_date=day)
		pm.pattern_detectors.append(PriceInflexDetector('NSE:NIFTY50-INDEX', callback=pm.pattern_signal, pattern_config=pattern_config))
		#pm.pattern_detectors.append(PriceInflexDetector('NSE:NIFTY50-INDEX'))
		for price in price_list:
			pm.price_input(price)
		#pm.pattern_detectors[0].dfstock_3.to_csv(reports_dir + 'temp_df.csv')
		print(pm.position_book)
		for st_id, strategy in pm.position_book.items():
			position = strategy['position']
			for trigger, trade in position.items():
				arr = {'day' : day, 'symbol':st_id[0], 'strategy':st_id[1], 'trigger': trigger, 'exit_time': trade['exit_time'], 'exit_type': trade['exit_type'], 'realized_pnl': round(trade['realized_pnl'],2), 'un_realized_pnl': round(trade['un_realized_pnl'],2)}
				results.append(arr)

		end_time = datetime.now()

	print((end_time-start_time).total_seconds())
	print(results)
	counter += 1
	pd.DataFrame(results).to_csv(reports_dir + 'bt_all_results.csv')