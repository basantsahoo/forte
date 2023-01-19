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

known_spot_instruments = ['SPOT']
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
                 weekdays_allowed=[],
                 entry_criteria = [],
                 exit_criteria_list = [],
                 signal_filter_conditions=[],
                 spot_targets = [0.002,0.003, 0.004, 0.005],
                 instr_targets = [0.002,0.003, 0.004, 0.005],
                 spot_stop_losses = [-0.001,-0.002, -0.002,-0.002],
                 instr_stop_losses = [-0.001,-0.002, -0.002,-0.002]

    ):
        print('BaseStrategy', derivative_instruments)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id
        self.insight_book = insight_book
        self.order_type = order_type
        self.spot_instruments = spot_instruments if spot_instruments else []
        self.derivative_instruments = derivative_instruments if derivative_instruments else []
        self.exit_time = exit_time
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal) #Dont go past 4
        self.max_signal = max_signal
        self.entry_criteria = entry_criteria
        self.signal_filter_conditions = signal_filter_conditions
        self.exit_criteria_list = exit_criteria_list
        self.spot_targets = spot_targets
        self.instr_targets = instr_targets
        self.spot_stop_losses = spot_stop_losses
        self.instr_stop_losses = instr_stop_losses

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
        if (len(spot_targets) < self.triggers_per_signal) and (len(instr_targets) < self.triggers_per_signal):
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
        """
        self.spot_targets = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.spot_stop_loss = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.instr_targets = [0.1, 0.2, 0.3, 0.4]
        self.instr_stop_loss = [-0.1, -0.2, -0.3, -0.4]
        """
        #self.prepare_targets()

    def calculate_target(self, instr, target_level_list):
        levels = []
        last_candle = self.get_last_tick(instr)
        side = get_broker_order_type(self.order_type)
        close_point = last_candle['close']

        for target_level in target_level_list:
            if isinstance(target_level, (int, float)):
                target = close_point * (1 + side * target_level)
                levels.append(target)
            else:
                print(target_level[0])
                target_fn = get_target_fn(target_level[0])
                mapped_fn = target_fn['mapped_fn']
                kwargs = target_fn.get('kwargs', {})
                kwargs = {**kwargs, **target_level[1]}
                # print(target_fn)
                rs = 0
                if target_fn['category'] == 'signal_queue':
                    queue = self.entry_signal_queues[target_fn['mapped_object']]
                    # print('queue.'+ mapped_fn + "()")
                    rs = eval('queue.' + mapped_fn)(**kwargs)
                elif target_fn['category'] == 'global':
                    obj = target_fn['mapped_object']
                    fn_string = 'self.' + (obj + '.' if obj else '') + mapped_fn  # + '()'
                    # print(fn_string)
                    rs = eval(fn_string)(**kwargs)
                if rs:
                    levels.append(rs)
        return levels

    def get_exit_levels(self, instr):
        res = {}
        res['spot_targets'] = self.calculate_target(instr, self.spot_targets)
        res['spot_stop_losses'] = self.calculate_target(instr, self.spot_stop_losses)
        res['instr_targets'] = self.calculate_target(instr, self.instr_targets)
        res['instr_stop_losses'] = self.calculate_target(instr, self.instr_stop_losses)
        return res

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
        exit_levels = self.get_exit_levels(instr)
        print(exit_levels)
        print(instr, idx)
        last_candle = self.get_last_tick(instr)

        return {
            'seq': idx,
            'instrument': instr,
            'cover': self.cover,
            'spot_target': exit_levels['spot_targets'][idx-1] if exit_levels['spot_targets'] else None,
            'spot_stop_loss': exit_levels['spot_stop_losses'][idx-1] if exit_levels['spot_stop_losses'] else None,
            'instr_target': exit_levels['instr_targets'][idx-1] if exit_levels['instr_targets'] else None,
            'instr_stop_loss': exit_levels['instr_stop_losses'][idx-1] if exit_levels['instr_stop_losses'] else None,
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

    """Deactivate when not required to run in a particular day"""
    def deactivate(self):
        self.activated = False
        self.insight_book.remove_strategy(self)
    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.insight_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def inst_is_option(self, inst):
        return inst not in known_spot_instruments

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
        self.tradable_signals[sig_key]['trade_completed'] = False
        self.tradable_signals[sig_key]['max_triggers'] = self.triggers_per_signal
        return sig_key

    def add_tradable_signal(self):
        sig_key = self.add_new_signal_to_journal()
        return sig_key

    def confirm_trigger(self, sig_key, triggers):
        curr_signal = self.tradable_signals[sig_key]
        for trigger in triggers:
            curr_signal['triggers'][trigger['seq']] = trigger


    def register_instrument(self, signal):
        pass

    def process_post_entry(self):
        pass


    def register_signal(self, signal):
        if signal['indicator'] != 'INDICATOR_TREND':
            #print('register+++++++++++', signal)
            pass
        if signal['indicator'] == 'PRICE_DROP':
            pass
            #print('register+++++++++++', signal)

        if (signal['category'], signal['indicator']) in self.entry_signal_queues:
            if self.evaluate_signal_filter(signal):
                self.entry_signal_queues[(signal['category'], signal['indicator'])].receive_signal(signal)
                self.register_instrument(signal)
        if (signal['category'], signal['indicator']) in self.exit_signal_queues:
            self.exit_signal_queues[(signal['category'], signal['indicator'])].receive_signal(signal)



    def look_for_trade(self):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = self.valid_tpo()
        #filter_criteria_met = self.evaluate_signal_filter()
        signal_present = self.all_entry_signal()
        #print('+++++++++++++++++++++++++')
        #print(enough_time)
        #print(suitable_tpo)
        #print(market_criteria_met)
        #print(signal_present)
        if enough_time and suitable_tpo and signal_present: #and filter_criteria_met:
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
        #print('evaluate entry+++')
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
                #print(queue.category)
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
                    last_instr_candle = self.get_last_tick(trigger_details['instrument'])
                    last_spot_candle = self.get_last_tick('SPOT')
                    if exit_criteria_met:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='EC')
                    elif trigger_details['instr_target'] and last_instr_candle['close'] < trigger_details['instr_target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='IT')
                        #print(last_candle, trigger_details['target'])
                    elif trigger_details['instr_stop_loss'] and last_instr_candle['close'] > trigger_details['instr_stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='IS')
                    elif trigger_details['spot_target'] and last_spot_candle['close'] < trigger_details['spot_target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='ST')
                        #print(last_candle, trigger_details['target'])
                    elif trigger_details['spot_stop_loss'] and last_spot_candle['close'] >= trigger_details['spot_stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='SS')
                    elif last_spot_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='TC')

    def monitor_buy_positions(self):
        exit_criteria_met = self.evaluate_exit()
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    last_instr_candle = self.get_last_tick(trigger_details['instrument'])
                    last_spot_candle = self.get_last_tick('SPOT')
                    #print(trigger_details)
                    if exit_criteria_met:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='EC')
                    elif trigger_details['instr_target'] and last_instr_candle['close'] >= trigger_details['instr_target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='IT')
                    elif trigger_details['instr_stop_loss'] and last_instr_candle['close'] < trigger_details['instr_stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='IS')
                    elif trigger_details['spot_target'] and last_spot_candle['close'] >= trigger_details['spot_target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='ST')
                    elif trigger_details['spot_target'] and last_spot_candle['close'] < trigger_details['spot_target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='SS')
                    elif last_spot_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type='TC')

    def monitor_existing_positions(self):
        if self.order_type == 'BUY':
            self.monitor_buy_positions()
        elif self.order_type == 'SELL':
            self.monitor_sell_positions()

    def evaluate_signal_filter(self, signal={}):
        satisfied = not self.signal_filter_conditions
        if not satisfied:
            market_params = self.insight_book.activity_log.get_market_params()
            #print(market_params)
            d2_ad_resistance_pressure = market_params['d2_ad_resistance_pressure']

            five_min_trend = market_params.get('five_min_trend', 0)
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params['d2_cd_new_business_pressure']
            category = (signal['category'] , signal['indicator'])
            open_type = market_params['open_type']
            tpo = market_params['tpo']
            strength = signal.get('strength', 0)
            kind = signal['info'].get('kind', "")
            money_ness = signal['info'].get('money_ness', "")
            #print('inside +++++', open_type, tpo, strength, kind, money_ness)
            for condition in self.signal_filter_conditions:
                #print(condition['logical_test'])
                satisfied = satisfied or eval(condition['logical_test'])
            #print(satisfied)
        return satisfied


    def record_params(self):
        #print('inside record_params', matched_pattern)
        #print(self.insight_book.activity_log.locate_price_region())
        if self.record_metric:
            price_region = self.insight_book.activity_log.locate_price_region()
            for key, val in price_region.items():
                self.signal_params['pat_' + key] = val
            for pattern_queue in self.entry_signal_queues.values():
                pattern_attr = pattern_queue.get_atrributes()
                self.signal_params = {**self.signal_params, **pattern_attr}
