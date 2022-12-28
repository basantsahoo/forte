import numpy as np
from strategies.bs_strat import BaseStrategy
from helper.utils import get_exit_order_type, pattern_param_match
from helper.utils import pattern_param_match, get_overlap
from trend.technical_patterns import pattern_engine
from statistics import mean
import patterns.utils as pattern_utils

class PriceActionPatternStrategy(BaseStrategy):
    def __init__(self, insight_book, pattern, order_type, exit_time, period, trend=None, min_tpo=None, max_tpo=None, record_metric=True):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = pattern + "_" + str(period) + "_" + order_type + "_" + str(exit_time)
        #print(self.id)
        self.price_pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend
        self.pending_previous_trade = False
        self.pending_signals = {}
        self.tradable_signals ={}

    def locate_point(self, df, threshold):
        above = len(np.array(df.index[df.Close > threshold]))
        below = len(np.array(df.index[df.Close <= threshold]))
        pct = (1 - above/(above + below)) * 100
        return pct
    # array of targets, stoploss and time - when one is triggered target and stoploss is removed and time is removed from last

    def get_dt_trades(self,pattern_match_prices,idx=1,curr_price=None,):
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        pattern_height = lowest_high_point - pattern_match_prices[2]
        curr_price= curr_price
        if idx == 1:
            return [lowest_high_point - pattern_height, max(pattern_match_prices) + 5,10]
        elif idx == 2:
            return [max(highest_high_point - 2 * pattern_height, pattern_match_prices[0]), max(pattern_match_prices), 15]

    def add_tradable_signal(self,matched_pattern):
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = {}
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['triggers'] = []
        self.tradable_signals[sig_key]['targets'] = []
        self.tradable_signals[sig_key]['stop_losses'] = []
        self.tradable_signals[sig_key]['time_based_exists'] = []
        self.tradable_signals[sig_key]['max_triggers'] = 4
        self.tradable_signals[sig_key]['trade_completed'] = False
        return sig_key

    def trigger_trade_from_signal(self, sig_key):
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        trade = self.get_dt_trades(matched_pattern['price_list'], next_trigger)
        curr_signal['triggers'].append(next_trigger)
        curr_signal['targets'].append(trade_1[0])
        curr_signal['targets'].append(trade_2[0])
        curr_signal['stop_losses'].append(trade_1[1])
        curr_signal['stop_losses'].append(trade_2[1])
        curr_signal['time_based_exists'].append(trade_1[2])
        curr_signal['time_based_exists'].append(trade_2[2])

    def process_pattern_signal(self, matched_pattern):
        #print('process_pattern_signal+++++++++++')
        # looking for overlap in time
        last_match_ol = 0 if self.last_match is None else get_overlap([matched_pattern['time_list'][1], matched_pattern['time_list'][2]], [self.last_match['time_list'][1], self.last_match['time_list'][2]])
        print(last_match_ol)
        """
        determine whether a new signal
        """
        if last_match_ol == 0:  # matched_pattern['time_list][2] != self.last_match['time_list][2]:
            self.last_match = matched_pattern
            self.strategy_params['pattern_time'] = matched_pattern['time_list']
            """
            Control when a trade is triggered
            """
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            pattern_location = self.locate_point(pattern_df, max(matched_pattern['price_list']))
            # test 3 double tops in upper side of market result in sharp fall? 3rd after 250?
            self.strategy_params['pattern_location'] = pattern_location

            existing_signals = len(self.tradable_signals.keys())
            sig_key = self.add_tradable_signal(matched_pattern)

            for trd_idx in range(1,3):
                trade_ = self.get_dt_trades(matched_pattern['price_list'], trd_idx)
            """
            curr_signal = self.tradable_signals[sig_key]
            next_trigger = len(curr_signal['triggers']) + 1
            curr_signal['triggers'].append(next_trigger) # for 1st trigger

            trade_1 = self.get_dt_trades(matched_pattern['price_list'], 1)
            trade_2 = self.get_dt_trades(matched_pattern['price_list'], 2)
            next_trigger = len(curr_signal['triggers']) + 1 # for second trigger
            curr_signal['triggers'].append(next_trigger)
            curr_signal['targets'].append(trade_1[0])
            curr_signal['targets'].append(trade_2[0])
            curr_signal['stop_losses'].append(trade_1[1])
            curr_signal['stop_losses'].append(trade_2[1])
            curr_signal['time_based_exists'].append(trade_1[2])
            curr_signal['time_based_exists'].append(trade_2[2])
            """
            self.trigger_entry(self.order_type, stop_loss=max(matched_pattern['price_list']) + 5, targets=[], qty=4)
            # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
            
    def trigger_entry(self, order_type, qty=1, targets=[], stop_loss=None):
        #print(self.insight_book.last_tick['timestamp'], self.insight_book.get_sma(self.short_sma), self.insight_book.get_sma(self.long_sma))
        req_id = self.trigger_id + 1
        if self.record_metric:
            self.params_repo[req_id] = self.get_market_params()
            #print( self.params_repo[req_id])
        resposne = self.insight_book.pm.strategy_entry_signal(self.insight_book.ticker, self.id, self.trigger_id + 1, order_type, qty)
        if resposne:
            self.executed_orders += 1
            self.trigger_id = req_id
            self.trade_open_time = self.insight_book.last_tick['timestamp']
            self.trade_open_price = self.insight_book.last_tick['close']
            self.existing_orders.append([self.trigger_id, self.insight_book.last_tick['timestamp'], self.insight_book.last_tick['close'], order_type, qty, targets, stop_loss])

    def process_incomplete_signals(self):
        #print('process_incomplete_signals+++++++++')

        if not self.insight_book.pm.reached_risk_limit(self.id) and self.tradable_signals: #risk limit not reached and there are some signals
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            for key, signal in self.tradable_signals.items():
                pattern_end_time = signal['pattern']['time_list'][-1]
                if not signal['trade_completed'] and np.array(pattern_df.Time)[-1] > pattern_end_time:
                    next_trigger = len(signal['triggers']) + 1
                    print('Inside', next_trigger)
                    if next_trigger == 3:
                        pattern_match_prices = signal['pattern']['price_list']
                        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
                        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
                        pattern_height = lowest_high_point - pattern_match_prices[2]
                        print(pattern_end_time)
                        sub_df = pattern_df[pattern_df['Time'] > pattern_end_time]
                        trigger_1_closed = True #Additional risk management check
                        target_1_met = min(sub_df['Close']) < min(signal['targets'])
                        if target_1_met:
                            local_minima_index = sub_df.index[sub_df.Close == min(sub_df['Close'])][0]
                            #print('local_minima_index++++++++++', local_minima_index)
                            # and there is a SPH between target 1 and DT lowest high and min price after SPH breached 50% of it's retracement'
                            reversal_point = sub_df[(sub_df.index > local_minima_index) & (sub_df.SPExt == 'SPH') & (sub_df.Close < min(pattern_match_prices[1], pattern_match_prices[3]))]
                            if reversal_point.shape[0] > 0:
                                print('3rd order triggered')
                                #print(reversal_point.Close)
                                target = min(signal['targets'])-pattern_height
                                signal['targets'].append(target)
                                signal['stop_losses'].append(reversal_point.Close.tolist()[0])
                                signal['time_based_exists'].append(30)
                                self.trigger_entry(self.order_type, stop_loss=pattern_match_prices[1] + 5, targets=[],qty=4)
                    elif next_trigger == 4:
                        pass

    def process_pattern_signal_old(self, pattern_match_idx):
        print('process_pattern_signal+++++++++++')
        last_match_ol = 0 if self.last_match is None else get_overlap([pattern_match_idx[0][1], pattern_match_idx[0][2]], [self.last_match[0][1], self.last_match[0][2]])
        if last_match_ol == 0:  # pattern_match_idx[0][2] != self.last_match[0][2]:
            # print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
            # print(pattern_match_idx)
            # print(self.last_match)
            self.last_match = pattern_match_idx
            # print('going to trigger')
            self.strategy_params['pattern_time'] = pattern_match_idx[0]
            """
            Control when a trade is triggered
            """
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            pattern_location = self.locate_point(pattern_df, max(pattern_match_idx[1]))
            # test 3 double tops in upper side of market result in sharp fall? 3rd after 250?
            self.strategy_params['pattern_location'] = pattern_location
            highest_high_point = max(pattern_match_idx[1][1], pattern_match_idx[1][3])
            lowest_high_point = min(pattern_match_idx[1][1], pattern_match_idx[1][3])
            pattern_height = lowest_high_point - pattern_match_idx[1][2]
            target_1 = lowest_high_point - pattern_height
            target_2 = max(highest_high_point - 2 * highest_high_point, pattern_match_idx[1][0])
            target_3 = max(highest_high_point - 2 * highest_high_point, pattern_match_idx[1][0])
            self.trigger_entry(self.order_type, stop_loss=max(pattern_match_idx[1]) + 5, targets=[], qty=4)
            # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
    def evaluate(self):
        self.process_incomplete_signals()
        self.close_existing_positions()

    def close_existing_positions(self):
        last_candle = self.insight_book.last_tick
        for order in self.existing_orders:
            if last_candle['timestamp'] - order[1] >= self.exit_time*60:
                self.trigger_exit(order[0])
            elif order[-1] is not None and last_candle['close'] > order[-1]:
                self.trigger_exit(order[0])