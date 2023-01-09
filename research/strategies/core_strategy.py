import numpy as np
from datetime import datetime
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type

#Check 13 May last pattern again why it was not triggered
class BaseStrategy:
    def __init__(self,
                 insight_book=None,
                 id=None,
                 pattern=None,
                 order_type="BUY",
                 exit_time=10,
                 period=5,
                 trend=None,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 target_pct = [0.002,0.003, 0.004, 0.005],
                 stop_loss_pct = [0.001,0.002, 0.002,0.002],
                 weekdays_allowed=[],
                 criteria=[]
                 ):
        self.id = id
        self.insight_book = insight_book
        self.price_pattern = pattern
        self.order_type = order_type
        self.exit_time = exit_time
        self.period = period
        self.trend = trend
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal) #Dont go past 4
        self.max_signal = max_signal
        self.target_pct = target_pct
        self.stop_loss_pct = stop_loss_pct
        self.criteria = criteria
        self.weekdays_allowed = weekdays_allowed

        self.activated = True
        self.is_aggregator = False

        self.params_repo = {}
        self.signal_params = {} #self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.tradable_signals ={}
        self.minimum_quantity = 1

    def get_trades(self, pattern_price_info, idx=1, neck_point=0):
        last_candle = self.insight_book.last_tick
        close_point = last_candle['close']
        side = get_broker_order_type(self.order_type)
        return {'seq': idx, 'target': close_point * (1 + side * self.target_pct[idx-1]), 'stop_loss':close_point * (1 - side * self.stop_loss_pct[idx-1]),'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':last_candle['timestamp']}

    def set_up(self):
        week_day_criterion = (not self.weekdays_allowed) or datetime.strptime(self.insight_book.trade_day, '%Y-%m-%d').strftime('%A') in self.weekdays_allowed
        activation_criterion = week_day_criterion
        if not activation_criterion:
            self.deactivate()

    """Deactivate when not required to run in a particular day"""
    def deactivate(self):
        self.activated = False
        self.insight_book.remove_strategy(self)

    def time_lapsed_since_mkt_open(self):
        time_lapsed = self.insight_book.last_tick['timestamp'] - self.insight_book.ib_periods[0]
        return time_lapsed

    def time_lapsed_since_trade_begin(self, min, trade_open_time):
        time_lapsed = self.insight_book.last_tick['timestamp'] - trade_open_time
        return time_lapsed

    def target_achieved(self, trade_open_price, th):
        return (1 - self.ltp/trade_open_price) >= th

    def stoploss_reached(self, trade_open_price, th):
        return (1 - self.ltp/self.trade_open_price) <= -1 *abs(th)

    def pivot_target(self, trade_open_price, th):
        #print('pivot_target')
        pivot_pts = list(self.insight_book.pivots.values())
        #print(pivot_pts)

        if self.side in ['BUY', 'LONG']:
            #print('in buy')
            pivot_targets = [x for x in pivot_pts if x > trade_open_price]
            pivot_targets.sort()
            #print(pivot_targets)
            return self.ltp > pivot_targets[th] * (1-0.001)
        else:
            #print('in sell')
            pivot_targets = [x for x in pivot_pts if x < trade_open_price]
            pivot_targets.sort()
            #print(pivot_targets)
            return self.ltp < pivot_targets[th] * (1 + 0.001)


    def get_lowest_candle(self):
        lowest_candle = None
        for (ts,candle) in reversed(self.insight_book.market_data.items()):
            #print(candle)
            if candle['low'] == self.insight_book.range['low']:
                lowest_candle = candle
                break
        return lowest_candle

    def locate_point(self, df, threshold):
        above = len(np.array(df.index[df.Close > threshold]))
        below = len(np.array(df.index[df.Close <= threshold]))
        pct = (1 - above / (above + below)) * 100
        return pct
        # array of targets, stoploss and time - when one is triggered target and stoploss is removed and time is removed from last

    def relevant_signal(self, pattern, pattern_match_idx):
        #print('relevant_signal' , self.price_pattern , pattern)
        return self.price_pattern == pattern

    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.insight_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def trigger_entry(self, order_type, sig_key, triggers):
        #print('trigger_entry',triggers)
        #print(sig_key, order_type)
        #print(triggers)
        for trigger in triggers:
            if self.record_metric:
                mkt_parms = self.insight_book.activity_log.get_market_params()
                if self.signal_params:
                    mkt_parms = {**mkt_parms, **self.signal_params}
                self.params_repo[(sig_key, trigger['seq'])] = mkt_parms  # We are interested in signal features, trade features being stored separately
        signal_info = {'symbol': self.insight_book.ticker, 'strategy_id': self.id, 'signal_id': sig_key, 'order_type': order_type, 'triggers': [{'seq': trigger['seq'], 'qty': trigger['quantity']} for trigger in triggers]}
        self.confirm_trigger(sig_key, triggers)
        self.insight_book.pm.strategy_entry_signal(signal_info)

    def trigger_exit(self, signal_id, trigger_id, exit_type=None):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.tradable_signals[signal_id]['triggers'][trigger_id]['quantity']
        last_candle = self.insight_book.last_tick
        signal_info = {'symbol': self.insight_book.ticker, 'strategy_id': self.id, 'signal_id': signal_id,
                       'trigger_id': trigger_id,
                       'qty': quantity}

        self.tradable_signals[signal_id]['triggers'][trigger_id]['closed'] = True
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_type'] = exit_type
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_price'] = last_candle['close']
        self.insight_book.pm.strategy_exit_signal(signal_info)

    def trigger_exit_at_low(self, signal_id, trigger_id):
        lowest_candle = self.get_lowest_candle()
        self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, signal_id, trigger_id, lowest_candle)

    def add_new_signal_to_journal(self):
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = {}
        self.tradable_signals[sig_key]['triggers'] = {}
        self.tradable_signals[sig_key]['targets'] = []
        self.tradable_signals[sig_key]['stop_losses'] = []
        self.tradable_signals[sig_key]['time_based_exists'] = []
        self.tradable_signals[sig_key]['trade_completed'] = False
        self.tradable_signals[sig_key]['max_triggers'] = self.triggers_per_signal
        return sig_key

    """
    Define custom strategy parameters here
    add_tradable_signal gives stretegies to define their own parameters to be added signals for record keeping
    """
    def add_tradable_signal(self, pattern_match_idx):
        sig_key = self.add_new_signal_to_journal()
        return sig_key

    def confirm_trigger(self, sig_key, triggers):
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
        triggers = [self.get_trades(curr_signal['pattern'], trd_idx) for trd_idx in range(next_trigger, next_trigger+self.triggers_per_signal)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type,sig_key,triggers)

    def process_signal(self, pattern, pattern_match_idx):
        if self.relevant_signal(pattern, pattern_match_idx) and (len(self.tradable_signals.keys()) < self.max_signal):
            #print('process_signal in core++++++++++++++++++++++++++', self.id, "tpo====", self.insight_book.curr_tpo, "minutes past===", len(self.insight_book.market_data.items()), "last tick===" , self.insight_book.last_tick['timestamp'])
            signal_passed = self.evaluate_signal(pattern_match_idx) #len(self.tradable_signals.keys()) < self.max_signals+5  #
            if signal_passed:
                sig_key = self.add_tradable_signal(pattern_match_idx)
                self.initiate_signal_trades(sig_key)

    def evaluate_signal(self, signal):
        return False

    def calculate_custom_signal(self):
        return False
    """will be used by strategy which doesnt have a pattern/trend signal"""
    def process_custom_signal(self):
        signal_found = self.calculate_custom_signal() #len(self.tradable_signals.keys()) < self.max_signals+5  #
        if signal_found:
            sig_key = self.add_tradable_signal(pattern_match_idx)
            self.initiate_signal_trades(sig_key)

    def process_incomplete_signals(self):
        pass

    def evaluate(self):
        self.process_incomplete_signals()
        self.monitor_existing_positions()

    def monitor_sell_positions(self):
        last_candle = self.insight_book.last_tick
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] < trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] >= trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_buy_positions(self):
        last_candle = self.insight_book.last_tick
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] >= trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] < trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_existing_positions(self):
        if self.order_type == 'BUY':
            self.monitor_buy_positions()
        elif self.order_type == 'SELL':
            self.monitor_sell_positions()

    def suitable_market_condition(self):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo() #(self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)
        suitable = enough_time and suitable_tpo
        if suitable:
            market_params = self.insight_book.activity_log.get_market_params()
            d2_ad_resistance_pressure = market_params['d2_ad_resistance_pressure']
            five_min_trend = market_params['five_min_trend']
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params['d2_cd_new_business_pressure']
            open_type = market_params['open_type']
            flag = not self.criteria
            for condition in self.criteria:
                flag = flag or eval(condition['logical_test'])
            suitable = suitable and flag
        return suitable



