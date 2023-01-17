import numpy as np
from datetime import datetime
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from arc.signal_queue import SignalQueue
from dynamics.constants import PRICE_ACTION_INTRA_DAY, CANDLE_5, INDICATOR_DOUBLE_TOP, PATTERN_STATE, STATE_OPEN_TYPE, OPEN_TYPE_ABOVE_VA
from research.strategies.signal_setup import get_signal_key, get_target_fn

class BaseStrategy:
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",
                 spot_instruments = ['SPOT'],
                 derivative_instruments=[],
                 exit_time=10,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 target_pct = [0.002,0.003, 0.004, 0.005],
                 stop_loss_pct = [0.001,0.002, 0.002,0.002],
                 weekdays_allowed=[],
                 entry_criteria = [],
                 exit_criteria_list = [],
                 filter_conditions=[],
                 spot_targets = [],
                 inst_targets = []
                 ):
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id
        self.insight_book = insight_book
        self.order_type = order_type
        self.spot_instruments = spot_instruments
        self.derivative_instruments = derivative_instruments
        self.exit_time = exit_time
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal) #Dont go past 4
        self.max_signal = max_signal
        self.target_pct = target_pct
        self.stop_loss_pct = stop_loss_pct
        self.entry_criteria = entry_criteria
        self.filter_conditions = filter_conditions
        self.exit_criteria_list = exit_criteria_list
        self.spot_targets = spot_targets
        self.inst_targets = inst_targets
        self.weekdays_allowed = weekdays_allowed

        self.activated = True
        self.is_aggregator = False

        self.params_repo = {}
        self.signal_params = {} #self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.tradable_signals ={}
        self.minimum_quantity = 1
        self.cover = 200 if self.derivative_instruments and self.order_type == 'SELL' else 0
        self.inst_to_trade = []
        if len(target_pct) < self.triggers_per_signal:
            raise Exception("Triggers and targets of unequal size")
        """
        self.entry_criteria = [
            {'OPEN_TYPE' : [-1, 'signal', "==", 'GAP_UP']},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', "<=", 20]},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', ">=", 5]},
            {'DT': [-1, 'pattern_height', ">=", -100]},
            {'TREND': [-1, "all_waves[-1]['dist']", ">=", -100]}
        ]
        self.exit_criteria_list = [[
            {'CANDLE_5_DOJI_SELL': [-1, 'time_lapsed', ">=", 5]}
        ]]
        """
        self.entry_signal_queues = {pattern: SignalQueue(self,pattern) for pattern in
                                    [get_signal_key(list(set(criteria.keys()))[0]) for criteria in self.entry_criteria]}

        temp_patterns = []
        for criteria_list in self.exit_criteria_list:
            for criteria in criteria_list:
                temp_patterns.append(get_signal_key(list(criteria.keys())[0]))
        temp_patterns = list(set(temp_patterns))
        self.exit_signal_queues = {pattern: SignalQueue(self,pattern) for pattern in temp_patterns}

        print('self.entry_signal_queues+++++++++++', self.entry_signal_queues)
        print('self.exit_signal_queues+++++++++++', self.exit_signal_queues)
        #self.spot_targets = ['DT_HEIGHT_TARGET',  'LAST_N_CANDLE_BODY_TARGET', 'PCT_SPOT']
        #self.inst_targets = []
        #self.prepare_targets()


    def prepare_targets(self):
        def calculate(target):
            target_fn = get_target_fn(target)
            #print(target_fn)
            rs = 0
            if target_fn['category'] == 'signal_queue':
                queue = self.entry_signal_queues[target_fn['mapped_object']]
                mapped_fn = target_fn['mapped_fn']
                kwargs = target_fn.get('kwargs', {})
                #print('queue.'+ mapped_fn + "()")
                rs = eval('queue.' + mapped_fn)(**kwargs)
            elif target_fn['category'] == 'global':
                obj = target_fn['mapped_object']
                mapped_fn = target_fn['mapped_fn']
                kwargs = target_fn.get('kwargs', {})
                fn_string = 'self.' + ( obj + '.' if obj else '') + mapped_fn #+ '()'
                #print(fn_string)
                rs = eval(fn_string)(**kwargs)
            #print(rs)
            return rs

        tgt_list = []
        for target in self.spot_targets:
            tgt_list.append(calculate(target))
            #print(tgt_list)
        return tgt_list

    def initiate_signal_trades(self):
        all_inst = self.spot_instruments + self.derivative_instruments
        for trade_inst in all_inst:
            sig_key = self.add_tradable_signal()
            #print('initiate_signal_trades+++++', sig_key)
            curr_signal = self.tradable_signals[sig_key]
            next_trigger = len(curr_signal['triggers']) + 1
            triggers = [self.get_trades(trade_inst, trd_idx) for trd_idx in range(next_trigger, next_trigger+self.triggers_per_signal)]
            # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
            #total_quantity = sum([trig['quantity'] for trig in triggers])
            self.trigger_entry(trade_inst,self.order_type,sig_key,triggers)
        self.process_post_entry()


    def get_trades(self, instr, idx=1):
        targets = self.prepare_targets()
        last_candle = self.get_last_tick(instr)
        close_point = last_candle['close']
        side = get_broker_order_type(self.order_type)

        return {
            'seq': idx,
            'instrument': instr,
            'cover': self.cover,
            'target': close_point * (1 + side * self.target_pct[idx-1]),
            'stop_loss':close_point * (1 - side * self.stop_loss_pct[idx-1]),
            'duration': self.exit_time,
            'quantity': self.minimum_quantity,
            'exit_type':None,
            'entry_price':last_candle['close'],
            'exit_price':None,
            'trigger_time':last_candle['timestamp']
        }

    def set_up(self):
        week_day_criterion = (not self.weekdays_allowed) or datetime.strptime(self.insight_book.trade_day, '%Y-%m-%d').strftime('%A') in self.weekdays_allowed
        activation_criterion = week_day_criterion
        if not activation_criterion:
            self.deactivate()

    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.insight_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def inst_is_option(self, inst):
        return inst not in self.spot_instruments

    def get_last_tick(self, instr='SPOT'):
        if self.inst_is_option(instr):
            last_candle = self.insight_book.option_processor.get_last_tick(instr)
        else:
            last_candle = self.insight_book.spot_processor.last_tick
        return last_candle

    def trigger_entry(self, trade_inst, order_type, sig_key, triggers):
        for trigger in triggers:
            if self.record_metric:
                mkt_parms = self.insight_book.activity_log.get_market_params()
                if self.signal_params:
                    mkt_parms = {**mkt_parms, **self.signal_params}
                self.params_repo[(sig_key, trigger['seq'])] = mkt_parms  # We are interested in signal features, trade features being stored separately
                self.signal_params = {}
        updated_symbol = self.insight_book.ticker + "_" + trade_inst if self.inst_is_option(trade_inst) else self.insight_book.ticker
        cover = triggers[0].get('cover', 0)
        signal_info = {'symbol': updated_symbol, 'cover': cover, 'strategy_id': self.id, 'signal_id': sig_key, 'order_type': order_type, 'triggers': [{'seq': trigger['seq'], 'qty': trigger['quantity']} for trigger in triggers]}
        self.confirm_trigger(sig_key, triggers)
        self.insight_book.pm.strategy_entry_signal(signal_info, option_signal=self.inst_is_option(trade_inst))
        for pattern_queue in self.entry_signal_queues.values():
            pattern_queue.flush()

    def trigger_exit(self, signal_id, trigger_id, exit_type=None):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.tradable_signals[signal_id]['triggers'][trigger_id]['quantity']
        instrument = self.tradable_signals[signal_id]['triggers'][trigger_id]['instrument']
        updated_symbol = self.insight_book.ticker + "_" + instrument if self.inst_is_option(instrument) else self.insight_book.ticker
        signal_info = {'symbol': updated_symbol, 'strategy_id': self.id, 'signal_id': signal_id,
                       'trigger_id': trigger_id,
                       'qty': quantity}
        last_candle = self.get_last_tick(instrument)
        self.tradable_signals[signal_id]['triggers'][trigger_id]['closed'] = True
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_type'] = exit_type
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_price'] = last_candle['close']
        self.insight_book.pm.strategy_exit_signal(signal_info, option_signal=self.inst_is_option(instrument))

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

    def add_tradable_signal(self):
        sig_key = self.add_new_signal_to_journal()
        return sig_key

    def confirm_trigger(self, sig_key, triggers):
        curr_signal = self.tradable_signals[sig_key]
        for trigger in triggers:
            curr_signal['targets'].append(trigger['target'])
            curr_signal['stop_losses'].append(trigger['stop_loss'])
            curr_signal['time_based_exists'].append(trigger['duration'])
            curr_signal['triggers'][trigger['seq']] = trigger


    def register_instrument(self, signal):
        pass

    def process_post_entry(self):
        pass


    def register_signal(self, signal):
        if signal['indicator'] != 'INDICATOR_TREND':
            print('register+++++++++++', signal)
        if (signal['category'], signal['indicator']) in self.entry_signal_queues:
            self.entry_signal_queues[(signal['category'], signal['indicator'])].receive_signal(signal)
        if (signal['category'], signal['indicator']) in self.exit_signal_queues:
            self.exit_signal_queues[(signal['category'], signal['indicator'])].receive_signal(signal)
        self.register_instrument(signal)


    def look_for_trade(self):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo()
        filter_criteria_met = self.evaluate_filter_condition()
        signal_present = self.all_entry_signal()
        #print('+++++++++++++++++++++++++')
        #print(enough_time)
        #print(suitable_tpo)
        #print(market_criteria_met)
        #print(signal_present)
        if enough_time and suitable_tpo and signal_present and filter_criteria_met:
            signal_passed = self.evaluate_entry() and self.custom_evaluation()
            if signal_passed:
                self.record_params()
                self.initiate_signal_trades()

    def all_entry_signal(self):
        #print([queue.has_signal() for queue in self.entry_signal_queues.values()])
        return self.entry_signal_queues and all([queue.has_signal() for queue in self.entry_signal_queues.values()])

    def custom_evaluation(self):
        return True

    def process_custom_signal(self):
        pass

    def evaluate_entry(self, signal=None):
        print('evaluate entry+++')
        passed = True
        for list_item in self.entry_criteria:
            pattern_comb, criteria = list(list_item.items())[0]
            pattern_comb = get_signal_key(pattern_comb)
            queue = self.entry_signal_queues[pattern_comb]
            last_spot_candle = self.insight_book.spot_processor.last_tick
            res = queue.eval_entry_criteria(criteria, last_spot_candle['timestamp'])
            passed = res and passed
            if not passed:
                break
        return passed

    def evaluate_exit(self, signal=None):
        passed = False
        for list_of_criteria in self.exit_criteria_list:
            criteria_list_passed = True
            for criteria_dict in list_of_criteria: # And condition for all items in list
                pattern_comb, criteria = list(criteria_dict.items())[0]
                pattern_comb = get_signal_key(pattern_comb)
                queue = self.exit_signal_queues[pattern_comb]
                print(queue.category)
                last_spot_candle = self.insight_book.spot_processor.last_tick
                res = queue.eval_exit_criteria(criteria, last_spot_candle['timestamp'])
                if res:
                    queue.flush()

                criteria_list_passed = res and criteria_list_passed
                if not criteria_list_passed: #Break if one fails
                    break
            passed = passed or criteria_list_passed
            if passed:
                break
        return passed

    def evaluate(self):
        #self.process_incomplete_signals()
        self.monitor_existing_positions()
        self.look_for_trade()

    def monitor_sell_positions(self):
        exit_criteria_met = self.evaluate_exit()
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    last_candle = self.get_last_tick(trigger_details['instrument'])
                    if exit_criteria_met:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='EC')
                    elif last_candle['close'] < trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] >= trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_buy_positions(self):
        exit_criteria_met = self.evaluate_exit()
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    last_candle = self.get_last_tick(trigger_details['instrument'])
                    #print(trigger_details)
                    if exit_criteria_met:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='EC')
                    elif last_candle['close'] >= trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                    elif last_candle['close'] < trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_existing_positions(self):
        if self.order_type == 'BUY':
            self.monitor_buy_positions()
        elif self.order_type == 'SELL':
            self.monitor_sell_positions()

    def evaluate_filter_condition(self, signal={}):
        satisfied = not self.filter_conditions
        if not satisfied:
            market_params = self.insight_book.activity_log.get_market_params()
            d2_ad_resistance_pressure = market_params['d2_ad_resistance_pressure']
            five_min_trend = market_params.get('five_min_trend', 0)
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params['d2_cd_new_business_pressure']
            open_type = market_params['open_type']
            tpo = market_params['tpo']
            strength = signal.get('strength', 0)
            kind = signal.get('kind', "")
            money_ness = signal.get('money_ness', "")
            for condition in self.filter_conditions:
                satisfied = satisfied or eval(condition['logical_test'])
        return satisfied


