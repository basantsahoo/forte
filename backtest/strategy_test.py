import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
import pandas as pd
from datetime import datetime
import time
import json
import traceback

#from strategies.sma_cross_over_buy import SMACrossBuy
#from strategies_bkp.range_break_low_for_regression import RangeBreakDownStrategy

from backtest.settings import reports_dir
from research.strategies.aggregators import CandleAggregator, PatternAggregator
from research.strategies.double_top_break_strategy import DoubleTopBreakStrategy
from research.strategies.state_cap_strategy import StateCapStrategy
from research.strategies.opening_trend_bearish import OpeningBearishTrendStrategy
from live_algo.friday_candle_first_30_mins import FridayCandleFirst30Buy,FridayCandleFirst30Sell, FridayCandleBuyFullDay

from dynamics.profile.market_profile import HistMarketProfileService
from infrastructure.arc.algo_portfolio import AlgoPortfolioManager
from infrastructure.arc.insight import InsightBook
from db.market_data import (get_all_days, get_daily_tick_data, get_daily_option_data_2)
import helper.utils as helper_utils

default_symbols =  ['NIFTY', 'BANKNIFTY']


class StartegyBackTester:
    def __init__(self, strat_config):
        self.strat_config = strat_config

    def configure(self):
        if len(self.strat_config.symbols) == 0:
            self.strat_config.symbols = default_symbols

    def back_test(self, symbol):
        results = []
        start_time = datetime.now()
        for day in self.strat_config['test_days']:
            print(day)
            print('=========================================================================================')

            processor = HistMarketProfileService()
            pm = AlgoPortfolioManager()
            in_day = day if type(day) == str else day.strftime('%Y-%m-%d')
            story_book = InsightBook(symbol, in_day, record_metric=self.strat_config['record_metric'], candle_sw=self.strat_config['candle_sw'])
            story_book.pm = pm
            #story_book.profile_processor = processor
            for s_id in range(len(self.strat_config['strategies'])):
                print('strategy=====', self.strat_config['strategies'][s_id])
                strategy_class = eval(self.strat_config['strategies'][s_id])
                strategy_kwargs = self.strat_config['strategy_kwargs'][s_id]
                story_book.add_strategy(strategy_class, strategy_kwargs)
            price_list = get_daily_tick_data(symbol, day)
            option_list = get_daily_option_data_2(symbol, day)
            print(option_list)
            price_list['symbol'] = helper_utils.root_symbol(symbol)
            price_list = price_list.to_dict('records')
            ivs = helper_utils.generate_random_ivs()
            try:
                for i in range(len(price_list)):
                    price = price_list[i]
                    iv = ivs[i]
                    #processor.process_input_data([price])
                    #processor.calculateMeasures()
                    pm.price_input(price)
                    story_book.price_input_stream(price, iv)
                    time.sleep(0.005)

                for strategy, trade_details in pm.position_book.items():
                    #print(strategy)
                    position = trade_details['position']
                    strategy_signal_generator = story_book.get_signal_generator_from_id(strategy[1])
                    for trigger_id, trade in position.items():
                        #print(trigger_id)
                        #print(trade)
                        _tmp = {'day': day, 'symbol': strategy[0], 'strategy': strategy[1], 'signal_id':  strategy[2], 'trigger': trigger_id, 'side': trade['side'], 'entry_time': trade['entry_time'], 'exit_time': trade['exit_time'], 'entry_price': trade['entry_price'], 'exit_price': trade['exit_price'] , 'realized_pnl': round(trade['realized_pnl'], 2), 'un_realized_pnl': round(trade['un_realized_pnl'], 2)}
                        _tmp['week_day'] = datetime.strptime(day, '%Y-%m-%d').strftime('%A') if type(day) == str else day.strftime('%A')
                        trigger_details = strategy_signal_generator.tradable_signals[strategy[2]]['triggers'][trigger_id]
                        _tmp = {**_tmp, **trigger_details}
                        signal_details = strategy_signal_generator.tradable_signals[strategy[2]]
                        signal_params = ['pattern_height']
                        for signal_param in signal_params:
                            if signal_param in signal_details:
                                _tmp[signal_param] = signal_details[signal_param]
                        if story_book.record_metric:
                            params = strategy_signal_generator.params_repo.get((strategy[2], trigger_id), {})
                            #print('params====', params)
                            _tmp = {**_tmp, **params}
                        results.append(_tmp)
            except Exception as e:

                print('error on', day)
                print(e)
                print(traceback.format_exc())
            # print(results)

        end_time = datetime.now()
        print((end_time - start_time).total_seconds())
        # print(results)
        return results


    def run(self):
        if not self.strat_config['symbols']:
            self.strat_config["symbols"] = default_symbols
        final_result = []
        for symbol in self.strat_config['symbols']:
            if len(self.strat_config['test_days']) == 0:
                all_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
                to_date = datetime.strptime(self.strat_config['to_date'], '%Y-%m-%d') if type(self.strat_config['to_date']) == str else self.strat_config['to_date']
                end_date = max(x for x in all_days if x <= to_date.date())
                end_date_index = all_days.index(end_date)
                for_past_days = int(self.strat_config['for_past_days']) if type(self.strat_config['for_past_days']) == str else self.strat_config['for_past_days']
                start_date_index = min(end_date_index + for_past_days, len(all_days))
                days = all_days[end_date_index:start_date_index]
                days = [x for x in days if (datetime.strptime(x, '%Y-%m-%d').strftime('%A') if type(x) == str else x.strftime('%A')) in self.strat_config['week_days']] if self.strat_config['week_days'] else days
                self.strat_config['test_days'] = days
            result = self.back_test(symbol)
            final_result.extend(result)
        return final_result


if __name__ == '__main__':
    argv = sys.argv[1:]
    print(argv)
    kwargs = {kw[0]: kw[1] for kw in [ar.split('=') for ar in argv if ar.find('=') > 0]}
    args = [arg for arg in argv if arg.find('=') < 0]
    if 'strat_config' in kwargs:
        strat_config_file = kwargs['strat_config']
    elif args:
        strat_config_file = args[0]
    else:
        strat_config_file = 'scenarios/default.json'
    strat_config_path = str(Path(__file__).resolve().parent) + "/scenarios/" + strat_config_file

    with open(strat_config_path) as bt_config:
        strat_config = json.load(bt_config)

    back_tester = StartegyBackTester(strat_config)
    results = back_tester.run()
    results = pd.DataFrame(results)
    part_results = results  # [['day',	'symbol',	'strategy',	'signal_id',	'trigger',	'entry_time',	'exit_time',	'entry_price',	'exit_price',	'realized_pnl',	'un_realized_pnl',	'week_day',	'seq',	'target',	'stop_loss',	'duration',	'quantity',	'exit_type', 'neck_point',	'pattern_height',	'pattern_time', 'pattern_price', 'pattern_location']]
    part_results['entry_time_read'] = part_results['entry_time'].apply(lambda x: datetime.fromtimestamp(x))
    search_days = results['day'].to_list()
    file_name = strat_config_file.split('.')[0]
    print('total P&L', part_results['realized_pnl'].sum())
    print('saving result to file', reports_dir + file_name + '.csv')
    part_results.to_csv(reports_dir + file_name + '.csv', index=False)
