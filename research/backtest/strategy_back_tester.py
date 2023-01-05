import pandas as pd
from datetime import datetime
import time
from settings import reports_dir
from dynamics.profile.market_profile import HistMarketProfileService
from infrastructure.arc.algo_portfolio import AlgoPortfolioManager
from infrastructure.arc.insight_mini import InsightBook
from db.market_data import (get_all_days, get_daily_tick_data, prev_day_data, get_prev_week_candle, get_nth_day_profile_data)
import helper.utils as helper_utils
#from strategies_bkp.range_break import RangeBreakDownStrategy
#from strategies_bkp.sma_cross_over_buy import SMACrossBuy
from research.strategies.double_top_break_strategy import DoubleTopBreakStrategy
import traceback

default_symbols =  ['NIFTY', 'BANKNIFTY']

def back_test(strategy_classes,strategy_kwargs, symbol, days):
    results = []
    start_time = datetime.now()
    for day in days:
        print(day)
        print('=========================================================================================')

        processor = HistMarketProfileService()
        pm = AlgoPortfolioManager()
        in_day = day if type(day) == str else day.strftime('%Y-%m-%d')
        story_book = InsightBook(symbol, in_day, record_metric=True)
        story_book.pm = pm
        #story_book.profile_processor = processor
        for s_id in range(len(strategy_classes)):
            story_book.add_strategy(strategy_classes[s_id], strategy_kwargs[s_id])
        price_list = get_daily_tick_data(symbol, day)
        price_list['symbol'] = helper_utils.root_symbol(symbol)
        price_list = price_list.to_dict('records')
        ivs = helper_utils.generate_random_ivs()
        try:
            for i in range(len(price_list)):
                price = price_list[i]
                iv = ivs[i]
                # print(price)
                # print(prof_data)
                processor.process_input_data([price])
                processor.calculateMeasures()
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
                        print('params====', params)
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


def test(strategy_class=DoubleTopBreakStrategy, strategy_kwargs=[], symbols = [], days = [], for_past_days=30, to_date="2022-04-30"):
    if len(symbols) == 0:
        symbols = default_symbols
    final_result = []
    for symbol in symbols:
        if len(days) == 0:
            all_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))

            to_date = datetime.strptime(to_date, '%Y-%m-%d') if type(to_date) == str else to_date

            end_date = max(x for x in all_days if x <= to_date.date())
            end_date_index = all_days.index(end_date)
            start_date_index = min(end_date_index + for_past_days, len(all_days))
            days = all_days[end_date_index:start_date_index]
            days = [x for x in days if x.weekday() >=3]
        result = back_test(strategy_class,strategy_kwargs, symbol, days)
        final_result.extend(result)
    return final_result



