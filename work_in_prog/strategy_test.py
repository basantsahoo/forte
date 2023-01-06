import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

#from strategies.sma_cross_over_buy import SMACrossBuy
#from strategies_bkp.range_break_low_for_regression import RangeBreakDownStrategy
from research.strategies.candle_aggregator import CandleAggregator
from research.strategies.price_action_aggregator import PatternAggregator
from research.strategies.double_top_break_strategy import DoubleTopBreakStrategy
from research.strategies.state_cap_strategy import StateCapStrategy
from research.strategies.opening_trend_bearish import OpeningBearishTrendStrategy
from live_algo.friday_candle_first_30_mins import FridayCandleFirst30Buy,FridayCandleFirst30Sell, FridayCandleBuyFullDay
from research.backtest import strategy_back_tester
import pandas as pd
from settings import reports_dir
from datetime import datetime

#strategy_list = ['PatternAggregator', 'CandleAggregator']
strategy_list = ['StateCapStrategy']
strategy_kwargs = [{'pattern':'STATE', 'order_type':'SELL', 'exit_time':10, 'period':1}]
strategy_list = ['OpeningBearishTrendStrategy']
strategy_kwargs = [{'pattern':'BEAR_TREND', 'order_type':'SELL', 'exit_time':15, 'period':5}]
strategy_list = ['CandleAggregator']
strategy_kwargs = [{}]
strategy_list = ['FridayCandleFirst30Buy', 'FridayCandleFirst30Sell', 'FridayCandleBuyFullDay']
strategy_kwargs = [{}, {}, {}]
strategy_classes = [eval(strategy) for strategy in strategy_list]
symbols = ['NIFTY']
days = []
for_past_days = 10
"""
import inspect
print(inspect.getfullargspec(type(StateCapStrategy).__init__))
strategy = StateCapStrategy('x', **strategy_kwargs[0])
"""
results = strategy_back_tester.test(strategy_classes, strategy_kwargs, symbols, days=days, for_past_days=for_past_days, to_date="2022-12-28", candle_sw=0)
results = pd.DataFrame(results)
part_results = results #[['day',	'symbol',	'strategy',	'signal_id',	'trigger',	'entry_time',	'exit_time',	'entry_price',	'exit_price',	'realized_pnl',	'un_realized_pnl',	'week_day',	'seq',	'target',	'stop_loss',	'duration',	'quantity',	'exit_type', 'neck_point',	'pattern_height',	'pattern_time', 'pattern_price', 'pattern_location']]
part_results['entry_time_read'] = part_results['entry_time'].apply(lambda x: datetime.fromtimestamp(x))
search_days = results['day'].to_list()
file_name = ''
for strategy in strategy_list:
    file_name += strategy[0:4] + "_"
for symbol in symbols:
    file_name += symbol + "_"
file_name += search_days[0] if type(search_days[0]) == str else search_days[0].strftime('%Y-%m-%d') + "_"
file_name += search_days[-1] if type(search_days[-1]) == str else search_days[-1].strftime('%Y-%m-%d')
print('total P&L', part_results['realized_pnl'].sum())
print('saving result to file', reports_dir + file_name + '.csv')
part_results.to_csv(reports_dir + file_name + '.csv', index=False)
