from research.core_strategies.t_core_strategy import BaseStrategy
from helper.utils import  get_overlap
from research.bkp_strategies.strat_mixin import PatternMetricRecordMixin

"""
signal_received -> process_signal -> evaluate_signal -> True -> add_tradable_signal -> sigkey ->  initiate_signal_trades -> get_trades -> trigger_entry
new price -> evaluate -> monitor_position ->  trigger_exit

"""
#Check 13 May last pattern again why it was not triggered
class DoubleTopStrategy(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, id, pattern, order_type, exit_time, period, trend=None, min_tpo=None, max_tpo=None,record_metric=True, triggers_per_signal=2):
        BaseStrategy.__init__(self, insight_book, id, pattern, order_type,exit_time, period,trend, min_tpo, max_tpo, record_metric=record_metric, triggers_per_signal=triggers_per_signal)
        self.id = pattern + "_" + order_type + "_" + str(period) + "_" + str(exit_time) if id is None else id
        #print(self.id)

    def get_trades(self, pattern_match, idx=1, curr_price=None,):
        pattern_match_prices = pattern_match['price_list']
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
        sig_key = self.add_new_signal_to_journal()
        #print('after+++++++', sig_key)
        pattern_match_prices = matched_pattern['price_list']
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        pattern_height = lowest_high_point - pattern_match_prices[2]

        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = pattern_height
        # max triggers 4
        return sig_key

    def suitable_market_condition(self,matched_pattern):
        last_wave = self.insight_book.intraday_waves[matched_pattern['time_list'][1]]
        market_params = self.insight_book.activity_log.get_market_params()
        #print(market_params)
        mu_0 = market_params['mu_0'] if 'mu_0' in market_params else 0
        mu_n = market_params['mu_n'] if 'mu_n' in market_params else 0
        five_min_trend = market_params['five_min_trend']
        lc_dist_frm_level = market_params['lc_dist_frm_level']
        lw_total_energy_ht = last_wave['total_energy_ht']
        static_ratio = market_params['static_ratio']
        suitable = True
        criteria = [{'op': 'and', 'logical_test': 'mu_0 <= 0.765 and lc_dist_frm_level > -47 and lw_total_energy_ht < 7.765'},
                    {'op': 'or', 'logical_test': '(mu_0 > 0.765 and five_min_trend <= -0.015)'},
                    {'op': 'and', 'logical_test': '(static_ratio > 0.165)'},
                    {'op': 'and', 'logical_test': '(mu_n > 0.295)'}
                    ]
        """
        condition = condition and mu_0 <= 0.765 and lc_dist_frm_level > -47 and lw_total_energy_ht < 7.765
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
            matched_pattern['time'] = matched_pattern['time_list']
            matched_pattern['candle'] = matched_pattern['price_list']
            self.record_params(matched_pattern)
            # test 3 double tops in upper side of market result in sharp fall? 3rd after 2:50?
            if self.record_metric:
                last_wave = self.insight_book.intraday_waves[matched_pattern['time_list'][1]]
                self.signal_params['pattern_time'] = matched_pattern['time_list']
                self.signal_params['pattern_price'] = matched_pattern['price_list']
                self.signal_params['pattern_location'] = pattern_location
                keys = ['total_energy_pyr', 'total_energy_ht', 'static_ratio', 'dynamic_ratio', 'd_en_ht', 's_en_ht', 'd_en_pyr', 's_en_pyr']
                for key in keys:
                    self.signal_params['lw_'+ key] = last_wave[key]
            if pattern_location > -1:
                signal_passed = True
        return signal_passed

