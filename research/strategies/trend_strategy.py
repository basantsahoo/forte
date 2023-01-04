import numpy as np
from research.strategies.core_strategy import BaseStrategy
from helper.utils import get_exit_order_type, pattern_param_match
from helper.utils import pattern_param_match, get_overlap
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils

#Check 13 May last pattern again why it was not triggered
class TrendStrategy(BaseStrategy):
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
        self.minimum_quantity = 1
        self.counter = 0

    def locate_point(self, df, threshold):
        above = len(np.array(df.index[df.Close > threshold]))
        below = len(np.array(df.index[df.Close <= threshold]))
        pct = (1 - above/(above + below)) * 100
        return pct
    # array of targets, stoploss and time - when one is triggered target and stoploss is removed and time is removed from last

    def get_dt_trades(self, pattern_match_prices, idx=1, curr_price=None,):
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = lowest_high_point - neck_point
        curr_price = curr_price
        last_candle = self.insight_book.last_tick
        if idx == 1:
            return {'seq': idx, 'target': 50, 'stop_loss': 20,'duration': 20, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point}
        elif idx == 2:
            return {'seq': idx, 'target': 75, 'stop_loss': 40, 'duration': 45, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point}

    def add_tradable_signal(self,matched_pattern):
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = {}
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        self.tradable_signals[sig_key]['triggers'] = {}
        self.tradable_signals[sig_key]['targets'] = []
        self.tradable_signals[sig_key]['stop_losses'] = []
        self.tradable_signals[sig_key]['time_based_exists'] = []
        self.tradable_signals[sig_key]['max_triggers'] = 4
        self.tradable_signals[sig_key]['trade_completed'] = False
        return sig_key

    def confirm_trade_from_trigger(self, sig_key, triggers):
        curr_signal = self.tradable_signals[sig_key]
        for trigger in triggers:
            curr_signal['targets'].append(trigger['target'])
            curr_signal['stop_losses'].append(trigger['stop_loss'])
            curr_signal['time_based_exists'].append(trigger['duration'])
            curr_signal['triggers'][trigger['seq']] = trigger


    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_dt_trades(curr_signal['pattern']['price_list'], trd_idx) for trd_idx in range(next_trigger, next_trigger+1+1)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type,sig_key,triggers, qty=total_quantity)


    def trigger_entry(self, order_type, sig_key, triggers, qty):
        response = self.insight_book.pm.place_oms_entry_order(self.insight_book.ticker, order_type, qty)
        if response:
            for trigger in triggers:
                if self.record_metric:
                    self.params_repo[(sig_key, trigger['seq'])] = self.get_market_params()  # We are interested in signal features, trade features being stored separately
                self.insight_book.pm.strategy_entry_signal(self.insight_book.ticker, self.id, sig_key, trigger['seq'], order_type, trigger['quantity'])
                self.confirm_trade_from_trigger(sig_key, triggers)

    def trigger_exit(self, signal_id, trigger_id, exit_type=None):
        quantity = self.tradable_signals[signal_id]['triggers'][trigger_id]['quantity']
        response = self.insight_book.pm.place_oms_exit_order(self.insight_book.ticker, self.id, signal_id, trigger_id, quantity)
        if response:
            last_candle = self.insight_book.last_tick
            self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, signal_id, trigger_id, quantity)
            self.tradable_signals[signal_id]['triggers'][trigger_id]['closed'] = True
            self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_type'] = exit_type
            self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_price'] = last_candle['close']

    def trigger_exit_at_low(self, signal_id, trigger_id):
        lowest_candle = self.get_lowest_candle()
        self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, signal_id, trigger_id, lowest_candle)

    def process_pattern_signal(self, matched_pattern):
        #print('process_pattern_signal+++++++++++')
        # looking for overlap in time
        last_match_ol = 0 if self.last_match is None else get_overlap([matched_pattern['time_list'][1], matched_pattern['time_list'][2]], [self.last_match['time_list'][1], self.last_match['time_list'][2]])
        #print(last_match_ol)
        """
        determine whether a new signal
        """
        if last_match_ol == 0:  # matched_pattern['time_list][2] != self.last_match['time_list][2]:
            self.last_match = matched_pattern
            # print('received new pattern++++', matched_pattern)
            """
            Control when a signal is considered for trade
            """
            pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            pattern_location = self.locate_point(pattern_df, max(matched_pattern['price_list']))
            # test 3 double tops in upper side of market result in sharp fall? 3rd after 250?
            if self.record_metric:
                self.strategy_params['pattern_time'] = matched_pattern['time_list']
                self.strategy_params['pattern_price'] = matched_pattern['price_list']
                self.strategy_params['pattern_location'] = pattern_location

            if pattern_location > -1:
                sig_key = self.add_tradable_signal(matched_pattern)
                self.initiate_signal_trades(sig_key)


    def evaluate(self):
        #self.process_incomplete_signals()
        self.close_existing_positions()

    def close_existing_positions(self):
        last_candle = self.insight_book.last_tick
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    exit_type = None
                    #print(trigger_details)
                    if last_candle['close'] < trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] >= trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - signal['pattern']['time_list'][-1] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

