import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import  get_overlap
from statistics import mean
import dynamics.patterns.utils as pattern_utils

"""
signal_received -> process_signal -> evaluate_signal -> True -> add_tradable_signal -> sigkey ->  initiate_signal_trades -> get_trades -> trigger_entry
new price -> evaluate -> monitor_position ->  trigger_exit

"""
#Check 13 May last pattern again why it was not triggered
class DoubleTopStrategy(BaseStrategy):
    def __init__(self, insight_book, pattern, order_type, exit_time, period, trend=None, min_tpo=None, max_tpo=None, record_metric=True):
        BaseStrategy.__init__(self, insight_book, order_type, min_tpo, max_tpo)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time)
        #print(self.id)
        self.price_pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend

    def get_trades(self, pattern_match_prices, idx=1, curr_price=None,):
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = lowest_high_point - neck_point
        curr_price = curr_price
        last_candle = self.insight_book.last_tick
        if idx == 1:
            return {'seq': idx, 'target': neck_point - pattern_height, 'stop_loss':lowest_high_point + 2,'duration': 20, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}
        elif idx == 2:
            return {'seq': idx, 'target': max(neck_point - 2 * pattern_height, pattern_match_prices[0]), 'stop_loss': highest_high_point+ 2, 'duration': 45, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}

    def add_tradable_signal(self,matched_pattern):
        sig_key = self.add_new_signal()
        #print('after+++++++', sig_key)
        pattern_match_prices = matched_pattern['price_list']
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        pattern_height = lowest_high_point - pattern_match_prices[2]

        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = pattern_height
        self.tradable_signals[sig_key]['max_triggers'] = 4
        return sig_key

    def suitable_market_condition(self,matched_pattern):
        last_wave = self.insight_book.intraday_waves[matched_pattern['time_list'][1]]
        market_params = self.get_market_params()
        #print(market_params)
        mu_0 = market_params['mu_0'] if 'mu_0' in market_params else 0
        mu_n = market_params['mu_n'] if 'mu_n' in market_params else 0
        five_min_trend = market_params['five_min_trend']
        dist_frm_level = market_params['dist_frm_level']
        lw_total_energy_ht = last_wave['total_energy_ht']
        static_ratio = market_params['static_ratio']
        suitable = True
        criteria = [{'op': 'and', 'logical_test': 'mu_0 <= 0.765 and dist_frm_level > -47 and lw_total_energy_ht < 7.765'},
                    {'op': 'or', 'logical_test': '(mu_0 > 0.765 and five_min_trend <= -0.015)'},
                    {'op': 'and', 'logical_test': '(static_ratio > 0.165)'},
                    {'op': 'and', 'logical_test': '(mu_n > 0.295)'}
                    ]
        """
        condition = condition and mu_0 <= 0.765 and dist_frm_level > -47 and lw_total_energy_ht < 7.765
        condition = condition or (mu_0 > 0.765 and five_min_trend <= -0.015)
        condition = condition and (static_ratio > 0.165)
        condition = condition and (mu_n > 0.165)
        """
        for condition in criteria:
            if condition['op'] == 'and':
                suitable = suitable and eval(condition['logical_test'])
            elif condition['op'] == 'or':
                suitable = suitable or eval(condition['logical_test'])

        return True

    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_trades(curr_signal['pattern']['price_list'], trd_idx) for trd_idx in range(next_trigger, next_trigger+1+1)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type, sig_key, triggers)

    def evaluate_signal(self, matched_pattern):
        #print('process_pattern_signal+++++++++++')
        # looking for overlap in time

        last_match_ol = 0 if self.last_match is None else get_overlap([matched_pattern['time_list'][1], matched_pattern['time_list'][2]], [self.last_match['time_list'][1], self.last_match['time_list'][2]])
        signal_passed = False
        #print(last_match_ol)
        """
        determine whether a new signal
        """
        if last_match_ol == 0 and self.suitable_market_condition(matched_pattern):  # matched_pattern['time_list][2] != self.last_match['time_list][2]:
            self.last_match = matched_pattern
            # print('received new pattern++++', matched_pattern)
            """
            Control when a signal is considered for trade
            """
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            pattern_location = self.locate_point(pattern_df, max(matched_pattern['price_list']))
            # test 3 double tops in upper side of market result in sharp fall? 3rd after 2:50?
            if self.record_metric:
                last_wave = self.insight_book.intraday_waves[matched_pattern['time_list'][1]]
                self.strategy_params['pattern_time'] = matched_pattern['time_list']
                self.strategy_params['pattern_price'] = matched_pattern['price_list']
                self.strategy_params['pattern_location'] = pattern_location
                keys = ['total_energy_pyr', 'total_energy_ht', 'static_ratio', 'dynamic_ratio', 'd_en_ht', 's_en_ht', 'd_en_pyr', 's_en_pyr']
                for key in keys:
                    self.strategy_params['lw_'+ key] = last_wave[key]
            if pattern_location > -1:
                signal_passed = True
        return signal_passed


    def process_incomplete_signals_2(self):
        #print('process_incomplete_signals+++++++++')

        if not self.insight_book.pm.reached_risk_limit(self.id) and self.tradable_signals: #risk limit not reached and there are some signals
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            for key, signal in self.tradable_signals.items():
                pattern_end_time = signal['pattern']['time_list'][-1]
                if not signal['trade_completed'] and np.array(pattern_df.Time)[-1] > pattern_end_time:
                    next_trigger = len(signal['triggers']) + 1
                    #print('Inside', next_trigger)
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



