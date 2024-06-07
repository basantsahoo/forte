import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
import pandas as pd
from datetime import datetime
import json
import traceback
import math

from backtest.settings import reports_dir
from arc.algo_portfolio import AlgoPortfolioManager
from arc.data_interface_for_backtest import AlgorithmBacktestIterface
from arc.option_market_book import OptionMarketBook
from db.market_data import (get_all_days)
import helper.utils as helper_utils
from arc.strategy_manager import StrategyManager
from entities.trading_day import TradeDateTime
from dynamics.option_market.data_loader import MultiDayOptionDataLoader
from dynamics.option_market.exclude_trade_days import exclude_trade_days
from backtest_2024.bt_strategies import *

default_symbols =  ['NIFTY', 'BANKNIFTY']


class StartegyBackTester:
    def __init__(self, strat_config):
        self.strat_config = strat_config

    def back_test(self, asset):
        results = []
        start_time = datetime.now()
        for day in self.strat_config['run_params']['test_days']:
            try:
                in_day = TradeDateTime(day) #if type(day) == str else day.strftime('%Y-%m-%d')
                t_day = in_day.date_string
                market_book = OptionMarketBook(in_day.date_string, assets=[asset], record_metric=self.strat_config['run_params']['record_metric'], insight_log=self.strat_config['run_params'].get('insight_log', False), live_mode=False)
                place_live = False
                interface = None
                if self.strat_config['run_params'].get("send_to_oms", False):
                    interface = AlgorithmBacktestIterface()
                    place_live = True
                pm = AlgoPortfolioManager(place_live, interface)
                market_book.pm = pm
                record_metric = self.strat_config['run_params'].get("record_metric", False)
                strategy_manager = StrategyManager(market_book=market_book, record_metric=record_metric)
                #story_book.profile_processor = processor
                for deployed_strategy in self.strat_config['strategies']:
                    start = datetime.now()
                    #print('deployed_strategy=====', deployed_strategy)
                    strategy_class = eval(deployed_strategy['class'])
                    strategy_manager.add_strategy(strategy_class, deployed_strategy)
                    end = datetime.now()
                    print('strategy init took', (end - start).total_seconds())
                market_book.strategy_manager = strategy_manager
                data_loader = MultiDayOptionDataLoader(asset=asset, trade_days=[t_day], spot_only=False)
                while data_loader.data_present:
                    feed_ = data_loader.generate_next_feed()
                    #print(feed_)
                    if feed_:
                        if feed_['feed_type'] == 'market_close':
                            market_book.market_close_for_day()
                        else:
                            market_book.feed_stream(feed_)
                            pm.feed_stream(feed_)
                            #time.sleep(0.005)
                #print(pm.position_book.items())
                try:
                    for strategy_tuple, trade_details in pm.position_book.items():
                        #print(strategy)
                        position = trade_details['position']
                        strategy_id = strategy_tuple[0]
                        signal_id = strategy_tuple[1]
                        trade_id = strategy_tuple[2]
                        leg_group_id = strategy_tuple[3]
                        strategy_signal_generator = strategy_manager.get_deployed_strategy_from_id(strategy_id)
                        for leg_id, leg_info in position.items():
                            print(leg_id)
                            print(leg_info)
                            t_symbol = leg_info['symbol']
                            _tmp = {'day': day, 'symbol': t_symbol, 'strategy': strategy_id, 'trade_id': trade_id, 'leg_group': leg_group_id, 'leg': leg_id, 'side': leg_info['side'], 'entry_time': leg_info['entry_time'], 'exit_time': leg_info['exit_time'], 'entry_price': leg_info['entry_price'], 'exit_price': leg_info['exit_price'] , 'realized_pnl': round(leg_info['realized_pnl'], 2), 'un_realized_pnl': round(leg_info['un_realized_pnl'], 2)}
                            _tmp['week_day'] = datetime.strptime(day, '%Y-%m-%d').strftime('%A') if type(day) == str else day.strftime('%A')
                            #trigger_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].trades[trade_id].leg_groups[leg_group_id].legs[leg_id]
                            trigger_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].trades[trade_id].leg_groups[leg_group_id].legs[leg_id].to_partial_dict()
                            print(trigger_details)
                            _tmp = {**_tmp, **trigger_details}
                            signal_custom_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].custom_features
                            signal_params = ['pattern_height']
                            for signal_param in signal_params:
                                if signal_param in signal_custom_details:
                                    _tmp[signal_param] = signal_custom_details[signal_param]
                            if market_book.record_metric:
                                params = strategy_signal_generator.params_repo.get((signal_id, trade_id), {})
                                #print('params====', params)
                                _tmp = {**_tmp, **params}
                            results.append(_tmp)
                except Exception as e:

                    print('error on', day)
                    print(e)
                    print(traceback.format_exc())
                # print(results)
            except Exception as e:
                print('error on', day)
                print(e)
                print(traceback.format_exc())

        end_time = datetime.now()
        print((end_time - start_time).total_seconds())
        print(results[0])
        """
        if results:
            results_df = pd.DataFrame(results)
            for deployed_strategy in self.strat_config['strategies']:
                save_strategy_run_params()
        """
        return results


    def run(self):
        subscribed_assets = list(set([strategy['trade_manager_info']['asset'] for strategy in self.strat_config['strategies']]))
        final_result = []
        for symbol in subscribed_assets:
            if len(self.strat_config['run_params']['test_days']) == 0:
                all_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
                to_date = datetime.strptime(self.strat_config['run_params']['to_date'], '%Y-%m-%d') if type(self.strat_config['run_params']['to_date']) == str else self.strat_config['run_params']['to_date']
                end_date = max(x for x in all_days if x <= to_date.date())
                end_date_index = all_days.index(end_date)
                for_past_days = int(self.strat_config['run_params']['for_past_days']) if type(self.strat_config['run_params']['for_past_days']) == str else self.strat_config['run_params']['for_past_days']
                start_date_index = min(end_date_index + for_past_days, len(all_days))
                days = all_days[end_date_index:start_date_index]
                days.sort()
                days = [x for x in days if (datetime.strptime(x, '%Y-%m-%d').strftime('%A') if type(x) == str else x.strftime('%A')) in self.strat_config['run_params']['week_days']] if self.strat_config['run_params']['week_days'] else days
                days = [x for x in days if x.strftime('%Y-%m-%d') not in exclude_trade_days['NIFTY']]
                #print(days)
                self.strat_config['run_params']['test_days'] = days
            result = self.back_test(symbol)
            final_result.extend(result)
        return final_result


if __name__ == '__main__':
    argv = sys.argv[1:]
    kwargs = {kw[0]: kw[1] for kw in [ar.split('=') for ar in argv if ar.find('=') > 0]}
    args = [arg for arg in argv if arg.find('=') < 0]
    if 'strat_config' in kwargs:
        strat_config_file = kwargs['strat_config']
    elif args:
        strat_config_file = args[0]
    else:
        #strat_config_file = 'ema_act_with_reverse_tick_nifty.json'
        strat_config_file = 'buy_call_option_on_volume.json'
    strat_config_path = str(Path(__file__).resolve().parent) + "/scenarios/" + strat_config_file
    with open(strat_config_path, 'r') as bt_config:
        strat_config = json.load(bt_config)

    back_tester = StartegyBackTester(strat_config)
    results = back_tester.run()
    results = pd.DataFrame(results)
    print('results=====',results)
    part_results = results  # [['day',	'symbol',	'strategy',	'signal_id',	'trigger',	'entry_time',	'exit_time',	'entry_price',	'exit_price',	'realized_pnl',	'un_realized_pnl',	'week_day',	'seq',	'target',	'stop_loss',	'duration',	'quantity',	'exit_type', 'neck_point',	'pattern_height',	'pattern_time', 'pattern_price', 'pattern_location']]
    print('total P&L', part_results['realized_pnl'].sum())
    print('Accuracy', len([x for x in part_results['realized_pnl'].to_list() if x>0])/len(part_results['realized_pnl'].to_list()))
    print('No of Days', len(part_results['day'].unique()))
    part_results['entry_time_read'] = part_results['entry_time'].apply(lambda x: datetime.fromtimestamp(x))
    part_results['exit_time_read'] = part_results['exit_time'].apply(lambda x: datetime.fromtimestamp(x) if x is not None and not math.isnan(x)  else x)
    search_days = results['day'].to_list()
    file_name = strat_config_file.split('.')[0]
    file_path = reports_dir + file_name + '.csv'

    print('saving result to file', file_path)
    part_results.to_csv(file_path, index=False)
