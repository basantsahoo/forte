from os import listdir
from os.path import isfile, join
import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
import pandas as pd
import numpy as np
from datetime import datetime
import json
import traceback
import math
import itertools
from entities.trading_day import TradeDateTime, NearExpiryWeek
from backtest_structure.settings import reports_dir
from arc.algo_portfolio import AlgoPortfolioManager
from arc.data_interface_for_backtest import AlgorithmBacktestIterface
from arc.option_market_book import OptionMarketBook
from db.market_data import (get_all_days)
import helper.utils as helper_utils
from strat_machine.strategy_manager import StrategyManager
from trade_master.strategy_trade_manager_pool import StrategyTradeManagerPool
from arc.data_loader_ip import MultiDayOptionDataLoader, MultiDaySpotDataLoader
from configurations.exclude_trade_days import exclude_trade_days
from backtest_structure.bt_strategies import *
from multiprocessing import Pool
MAX_JOBS = 5


class StartegyBackTester:
    def __init__(self, strat_config):
        self.strat_config = strat_config
        self.strat_config['strategy_info'] = {}
        self.strat_config['trade_manager_info'] = {}
        self.strat_config['combinator_info'] = {}
        self.processing_error_days = []

    def back_test_helper(self, subscribed_assets):
        start_time = datetime.now()
        weeks = list(set([NearExpiryWeek(TradeDateTime(day)) for day in self.strat_config['run_params']['test_days']]))
        weeks.sort()
        maxjobs = min(len(weeks), MAX_JOBS)
        week_schedule = [1 for i in range(maxjobs)]
        if len(weeks) > maxjobs:
            unalocated_weeks = len(weeks) - maxjobs
            for idx in range(unalocated_weeks):
                week_schedule[np.mod(idx, maxjobs)] += 1
        job_params = []
        begin = 0
        for week_counts in week_schedule:
            job_params.append(list(range(begin, begin + week_counts)))
            begin += week_counts
        #print(job_params)

        job_day_params = []
        for idx, week_indices in enumerate(job_params):
            job_weeks = [weeks[idx] for idx in week_indices]
            test_days_to_trading_days = [TradeDateTime(day) for day in self.strat_config['run_params']['test_days']]
            job_days_by_week = [
                [day.date_string for day in test_days_to_trading_days if (day >= week.start_date) and (day <= week.end_date)]
                for week in job_weeks
            ]
            all_job_days = [day for week_days in job_days_by_week for day in week_days]

            job_day_params.append((all_job_days, subscribed_assets, idx))
        #print(job_day_params)

        # job_params = [([1] , 0) for i in range(maxjobs)]
        p = Pool(maxjobs)
        res = p.map(self.back_test, job_day_params)
        results = list(itertools.chain.from_iterable(res))
        # print(self.section_pdf_list)
        p.close()
        p.join()
        end_time = datetime.now()
        print((end_time - start_time).total_seconds(), "seconds run time")
        return results

    def back_test(self, day_list_and_assets):
        day_list, subscribed_assets, process_id = day_list_and_assets
        print(day_list, subscribed_assets)
        results = []
        for day in day_list:
            try:
                in_day = TradeDateTime(day) #if type(day) == str else day.strftime('%Y-%m-%d')
                t_day = in_day.date_string
                market_book = OptionMarketBook(in_day.date_string, assets=subscribed_assets, record_metric=self.strat_config['run_params']['record_metric'], insight_log=self.strat_config['run_params'].get('insight_log', False), live_mode=False, spot_only=self.strat_config['run_params'].get('spot_only', False), process_id=process_id)
                place_live = False
                interface = None
                if self.strat_config['run_params'].get("send_to_oms", False):
                    interface = AlgorithmBacktestIterface(process_id=process_id)
                    place_live = True
                pm = AlgoPortfolioManager(place_live, interface, process_id=process_id)
                pm.market_book = market_book
                market_book.pm = pm
                record_metric = self.strat_config['run_params'].get("record_metric", False)
                strategy_manager = StrategyManager(market_book=market_book, record_metric=record_metric)
                trade_pool = StrategyTradeManagerPool(market_book=market_book, strategy_manager=strategy_manager)
                #story_book.profile_processor = processor
                for deployed_strategy in self.strat_config['strategy_info'].values():
                    start = datetime.now()
                    #print('deployed_strategy=====', deployed_strategy)
                    strategy_class = eval(deployed_strategy['class'])
                    strategy_manager.add_strategy(strategy_class, deployed_strategy)
                    end = datetime.now()
                    #print('strategy init took', (end - start).total_seconds())

                for deployed_tm in self.strat_config['trade_manager_info'].values():
                    start = datetime.now()
                    #print('deployed_strategy=====', deployed_strategy)
                    trade_pool.add(deployed_tm)
                    end = datetime.now()
                    #print('strategy init took', (end - start).total_seconds())


                for deployed_combinator in self.strat_config['combinator_info'].values():
                    strategy_manager.add_combinator(deployed_combinator)
                    end = datetime.now()
                    print('Combinator init took', (end - start).total_seconds())
                strategy_manager.clean_up_combinators()
                strategy_manager.clean_up_strategies()

                market_book.strategy_manager = strategy_manager
                if self.strat_config['run_params'].get('spot_only', False):
                    data_loader = MultiDaySpotDataLoader(assets=subscribed_assets, trade_days=[t_day])
                else:
                    data_loader = MultiDayOptionDataLoader(assets=subscribed_assets, trade_days=[t_day], spot_only=self.strat_config['run_params'].get('spot_only', False))

                while data_loader.data_present:
                    feed_list_ = data_loader.generate_next_feed()
                    feed_list_ = list(feed_list_)
                    #print(feed_list_)
                    for feed_ in feed_list_:
                        if feed_:
                            if feed_['feed_type'] == 'market_close':
                                market_book.market_close_for_day()
                            else:
                                pm.feed_stream(feed_)
                                market_book.feed_stream(feed_)

                            #time.sleep(0.005)
                #print(pm.position_book.items())
                try:
                    for strategy_tuple, trade_details in pm.position_book.items():
                        #print(strategy_tuple)
                        position = trade_details['position']

                        strategy_id = strategy_tuple[0]
                        signal_id = strategy_tuple[1]
                        trade_id = strategy_tuple[2]
                        leg_group_id = strategy_tuple[3]
                        strategy_signal_generator = strategy_manager.get_deployed_strategy_from_id(strategy_id)
                        for leg_id, leg_info in position.items():
                            try:
                                t_symbol = leg_info['symbol']
                                trade_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].trades[trade_id].to_partial_dict()
                                trade_trigger_time = trade_details['trade_trigger_time']
                                t_day = datetime.fromtimestamp(trade_trigger_time)
                                _tmp = {'day': t_day.strftime('%d-%m-%Y'), 'symbol': t_symbol, 'strategy': strategy_id, 'signal_id': signal_id, 'trade_id': trade_id}
                                _tmp['week_day'] = datetime.strptime(t_day, '%Y-%m-%d').strftime('%A') if type(t_day) == str else t_day.strftime('%A')
                                _tmp_2 = {'leg': leg_id, 'side': leg_info['side'], 'entry_price': leg_info['entry_price'], 'exit_price': leg_info['exit_price'] , 'realized_pnl': round(leg_info['realized_pnl'], 2), 'un_realized_pnl': round(leg_info['un_realized_pnl'], 2)}

                                leg_group_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].trades[trade_id].leg_groups[leg_group_id].to_partial_dict()
                                leg_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].trades[trade_id].leg_groups[leg_group_id].legs[leg_id].to_partial_dict()
                                _tmp = {**_tmp, **trade_details, **leg_group_details, **_tmp_2, **leg_details}
                                signal_custom_details = strategy_signal_generator.trade_manager.tradable_signals[signal_id].custom_features
                                signal_params = ['pattern_height']
                                for signal_param in signal_params:
                                    if signal_param in signal_custom_details:
                                        _tmp[signal_param] = signal_custom_details[signal_param]
                                if market_book.record_metric:
                                    params = strategy_signal_generator.trade_manager.params_repo.get((signal_id, trade_id), {})
                                    #print('params====', params)
                                    _tmp = {**_tmp, **params}
                                results.append(_tmp)
                            except Exception as e:
                                print(traceback.format_exc())
                except Exception as e:
                    #self.processing_error_days.append(day)
                    print('error on', day)
                    print(e)
                    print(traceback.format_exc())
                # print(results)
            except Exception as e:
                #self.processing_error_days.append(day)
                print('error on', day)
                print(e)
                print(traceback.format_exc())

        return results


    def run(self):
        # Strategies
        strategies_path = str(Path(__file__).resolve().parent.parent) + "/deployments/strategies/"
        strategyfiles = [f for f in listdir(strategies_path) if isfile(join(strategies_path, f))]
        for fl in strategyfiles:
            with open(strategies_path + fl, 'r') as bt_config:
                strategy_info = json.load(bt_config)
                if strategy_info['id'] in self.strat_config['strategies']:
                    self.strat_config['strategy_info'][strategy_info['id']] = strategy_info
        trade_manager_path = str(Path(__file__).resolve().parent.parent) + "/deployments/trade_managers/"
        trade_manager_files = [f for f in listdir(trade_manager_path) if isfile(join(trade_manager_path, f))]
        for fl in trade_manager_files:
            with open(trade_manager_path + fl, 'r') as bt_config:
                tm_info = json.load(bt_config)
                if tm_info['strategy_id'] in self.strat_config['strategies']:
                    self.strat_config['trade_manager_info'][tm_info['strategy_id']] = tm_info

        # Combinators
        combinators_path = str(Path(__file__).resolve().parent.parent) + "/deployments/combinators/"
        combinator_files = [f for f in listdir(combinators_path) if isfile(join(combinators_path, f))]
        for fl in combinator_files:
            with open(combinators_path + fl, 'r') as bt_config:
                combinator_info = json.load(bt_config)
                if combinator_info['id'] in self.strat_config['combinators']:
                    self.strat_config['combinator_info'][combinator_info['id']] = combinator_info

        #print(self.strat_config['combinator_info'])
        combination_strategies = [x for combinator in self.strat_config['combinator_info'].values() for x in combinator['combinations']]
        #print(combination_strategies)
        strategies_path = str(Path(__file__).resolve().parent.parent) + "/deployments/combinators/strategies/"
        strategyfiles = [f for f in listdir(strategies_path) if isfile(join(strategies_path, f))]
        for fl in strategyfiles:
            with open(strategies_path + fl, 'r') as bt_config:
                strategy_info = json.load(bt_config)
                if strategy_info['id'] in combination_strategies:
                    self.strat_config['strategy_info'][strategy_info['id']] = strategy_info

        trade_manager_path = str(Path(__file__).resolve().parent.parent) + "/deployments/combinators/trade_managers/"
        trade_manager_files = [f for f in listdir(trade_manager_path) if isfile(join(trade_manager_path, f))]
        for fl in trade_manager_files:
            with open(trade_manager_path + fl, 'r') as bt_config:
                tm_info = json.load(bt_config)
                if tm_info['strategy_id'] in combination_strategies:
                    self.strat_config['trade_manager_info'][tm_info['strategy_id']] = tm_info


        subscribed_assets = list(set([tm['asset'] for tm in self.strat_config['trade_manager_info'].values()]))
        #print(subscribed_assets)
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
                days = [x for x in days if x.strftime('%Y-%m-%d') not in exclude_trade_days['BANKNIFTY']]
                #print(days)
                self.strat_config['run_params']['test_days'] = self.strat_config['run_params']['test_days'] + days
        result = self.back_test_helper(subscribed_assets)
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
        strat_config_file = 'back_test_strategies.json'
    strat_config_path = str(Path(__file__).resolve().parent.parent) + "/deployments/" + strat_config_file
    with open(strat_config_path, 'r') as bt_config:
        strat_config = json.load(bt_config)

    back_tester = StartegyBackTester(strat_config)
    results = back_tester.run()
    results = pd.DataFrame(results)

    part_results = results  # [['day',	'symbol',	'strategy',	'signal_id',	'trigger',	'entry_time',	'exit_time',	'entry_price',	'exit_price',	'realized_pnl',	'un_realized_pnl',	'week_day',	'seq',	'target',	'stop_loss',	'duration',	'quantity',	'exit_type', 'neck_point',	'pattern_height',	'pattern_time', 'pattern_price', 'pattern_location']]
    search_days = results['day'].to_list()
    file_name = strat_config_file.split('.')[0]
    file_path = reports_dir + file_name + '_mp.csv'



    # Columns to group by
    groupby_columns = ['strategy', 'symbol', 'signal_id', 'trade_id', 'lg_id', 'leg']
    exclude_columns = [col for col in part_results.columns if col not in groupby_columns]


    def keep_non_blank_exit_price(group):
        # Check if there's any non-blank exit_price in the group
        non_blank_rows = group.dropna(subset=['exit_price'])
        if not non_blank_rows.empty:
            # If there are non-blank rows, keep the first one (assuming only one such row per group)
            return non_blank_rows
        else:
            # Otherwise, keep the original group (which contains the NaN exit_price row)
            return group


    result_df = part_results.groupby(groupby_columns, as_index=False).apply(keep_non_blank_exit_price).reset_index(drop=True)
    # Reset index to flatten the multi-index resulting from groupby
    result_df = result_df.drop_duplicates(subset=groupby_columns, keep='first').reset_index(drop=True)
    result_df = result_df.sort_values(by=['trade_trigger_time', 'strategy', 'trade_id'], ascending=[True,True, True], na_position='first')
    trade_group_by_columns = ['strategy', 'signal_id', 'trade_id']
    trade_level_df = part_results.groupby(trade_group_by_columns, as_index=False).agg({'realized_pnl': ['sum']}).reset_index(drop=True)
    trade_level_df.columns = trade_group_by_columns + ['realized_pnl']
    print(trade_level_df)
    #print('results=====', result_df)
    print('total P&L', result_df['realized_pnl'].sum())
    print('Accuracy', len([x for x in result_df['realized_pnl'].to_list() if x>0])/len(result_df['realized_pnl'].to_list()))
    print('Trade Accuracy', len([x for x in trade_level_df['realized_pnl'].to_list() if x > 0]) / len(trade_level_df['realized_pnl'].to_list()))
    print('No of Days', len(result_df['day'].unique()))
    result_df['trade_entry_time_read'] = result_df['trade_trigger_time'].apply(lambda x: datetime.fromtimestamp(x))
    result_df['lg_exit_time_read'] = result_df['lg_exit_time'].apply(lambda x: datetime.fromtimestamp(x) if x is not None and not math.isnan(x)  else x)

    print('saving result to file', file_path)

    result_df.to_csv(file_path, index=False)
    print('processing error in days ===', back_tester.processing_error_days)
