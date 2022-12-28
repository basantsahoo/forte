import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

#from strategies.sma_cross_over_buy import SMACrossBuy
#from strategies_bkp.range_break_low_for_regression import RangeBreakDownStrategy
from strategies.candle_aggregator import CandleAggregator
from strategies.price_action_aggregator import PatternAggregator
from strategies.double_top_break_strategy import DoubleTopBreakStrategy
from strategies.state_cap_strategy import StateCapStrategy
from research.backtest import strategy_back_tester
import pandas as pd
from settings import reports_dir
from datetime import datetime

#strategy_list = ['PatternAggregator', 'CandleAggregator']
strategy_list = ['StateCapStrategy']
strategy_classes = [eval(strategy) for strategy in strategy_list]
strategy_kwargs = [{'pattern':'STATE', 'order_type':'SELL', 'exit_time':360, 'period':1}]
symbols = ['NIFTY']
days = []
for_past_days = 150
"""
import inspect
print(inspect.getfullargspec(type(StateCapStrategy).__init__))
strategy = StateCapStrategy('x', **strategy_kwargs[0])
"""
results = strategy_back_tester.test(strategy_classes, strategy_kwargs, symbols, days=days, for_past_days=for_past_days, to_date="2022-01-27")
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
part_results.to_csv(reports_dir + file_name + '.csv', index=False)
