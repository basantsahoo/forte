from helper.utils import locate_point


def get_neuron(neuron_type=None, strategy=None, neuron_id=0,  signal_type=None, min_activation_strength=1, trade_eval=[],  activation_subscriptions=[], validity_period=60, flush_hist=True, register_instr=False, reversal_subscriptions=[]):
    if neuron_type in ['FixedForLifeNeuron']:
        return FixedForLifeNeuron(strategy, neuron_id, signal_type, min_activation_strength, trade_eval,  activation_subscriptions, validity_period, flush_hist, register_instr, reversal_subscriptions)
    elif neuron_type in ['CurrentMemoryPurgeableNeuron']:
        return CurrentMemoryPurgeableNeuron(strategy, neuron_id, signal_type, min_activation_strength, trade_eval,  activation_subscriptions, validity_period, flush_hist, register_instr, reversal_subscriptions)
    elif neuron_type in ['PriceAction']:
        return PriceAction(strategy, neuron_id, signal_type, min_activation_strength, trade_eval,  activation_subscriptions, validity_period, flush_hist, register_instr, reversal_subscriptions)
    elif neuron_type in ['UniqueHistPurgeableNeuron']:
        return UniqueHistPurgeableNeuron(strategy, neuron_id, signal_type, min_activation_strength, trade_eval,  activation_subscriptions, validity_period, flush_hist, register_instr, reversal_subscriptions)
    else:
        raise Exception("Signal Queue is not defined")

"""
def get_queue(strategy, category, flush_hist=True):
    if category[0] in ['STATE']:
        return FreshOnlyNoFlushSignalQueue(strategy, category, flush_hist)
    elif category[1] in ['INDICATOR_TREND']:
        return FreshOnlySignalQueue(strategy, category, flush_hist)
    elif category in [('OPTION', 'PRICE_DROP')]:
        return FreshOnlySignalQueue(strategy, category, flush_hist)
    elif 'PRICE_ACTION' in category[0]:
        return PriceActionQueue(strategy, category, flush_hist)
    elif 'CANDLE' in category[0]:
        return AccumulateNoDuplicateSignalQueue(strategy, category, flush_hist)
    elif 'TECHNICAL' in category[0]:
        return NonEvaluatedFreshSignalOnlyQueue(strategy, category, flush_hist)
    else:
        raise Exception("Signal Queue is not defined")
"""


class Neuron:
    def __init__(self, strategy, neuron_id, signal_type, min_activation_strength, trade_eval, activation_subscriptions, validity_period, flush_hist, register_instr, reversal_subscriptions):
        self.strategy = strategy
        self.id = neuron_id
        self.signal_type = signal_type
        self.min_activation_strength = min_activation_strength
        self.trade_eval = trade_eval
        self.signal_type = signal_type
        self.min_activation_strength = min_activation_strength
        self.validity_period = validity_period
        self.flush_hist = flush_hist
        self.register_instr = register_instr
        #self.reversal_subscriptions = reversal_subscriptions
        self.signals = []
        self.last_signal_time = None

        self.signal_forward_channels = []
        self.activation_forward_channels = []
        self.active = False
        self.pending_trade_eval = False
        self.activation_dependency = {}
        for back_neuron_id in activation_subscriptions:
            self.activation_dependency[back_neuron_id] = False

    def receive_signal(self, signal):
        return False
        #print(self.category, len(self.queue))

    def get_signal(self, pos=-1):
        return self.signals[pos]

    def flush(self):
        if self.flush_hist:
            self.signals = []
            self.check_activation()

    def remove_last(self):
        del self.signals[-1]

    def has_signal(self):
        return bool(self.signals)

    def get_pattern_height(self, pos=-1):
        return 0

    def eval_entry_criteria(self):
        test_criteria = self.trade_eval
        curr_ts = self.strategy.insight_book.spot_processor.last_tick['timestamp']
        if not test_criteria:
            return True
        #print(criteria)
        try:
            pattern = self.signals[test_criteria[0]]
        except:
            return False
        #print(pattern)
        strength = pattern['strength']
        signal = pattern.get('signal', "")
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(test_criteria[0])

        test = test_criteria[1] + test_criteria[2] + repr(test_criteria[3])
        """
        print(self.category)
        print(test)
        print(strength)
        """
        res = eval(test)
        self.pending_evaluation = False
        return res

    def eval_exit_criteria(self):
        criteria = self.trade_eval
        curr_ts = self.strategy.insight_book.spot_processor.last_tick['timestamp']
        #print('eval_exit_criteria', criteria)
        if not criteria:
            return True
        #print(criteria)
        try:
            pattern = self.signals[criteria[0]]
        except:
            return False  # Different from entry

        #print(pattern)
        signal = pattern['signal']
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(criteria[0])

        test = criteria[1] + criteria[2] + repr(criteria[3])
        res = eval(test)
        return res

    def check_validity(self):
        last_tick_time = self.strategy.insight_book.spot_processor.last_tick['timestamp']
        self.signals = [signal for signal in self.signals if last_tick_time - signal['signal_time'] >= self.validity_period * 60]
        self.check_activation()

    def get_attributes(self, pos=-1):
        res = {}
        pattern = self.signals[pos]
        if pattern['info'].get('price_list', None) is not None:
            res['pattern_price'] = pattern['info']['price_list']
        if pattern['info'].get('time_list', None) is not None:
            res['pattern_time'] = pattern['info']['time_list']
        if pattern['info'].get('time', None) is not None:
            res['pattern_time'] = pattern['info']['time']
        if pattern['info'].get('candle', None) is not None:
            res['pattern_price'] = pattern['info']['candle']
        if pattern['info'].get('time_list', None) is not None:
            res['pattern_time'] = pattern['info']['time_list']

        if 'strike' in pattern:
            res['strike'] = pattern['strike']
        if 'kind' in pattern:
            res['kind'] = pattern['kind']
        if 'money_ness' in pattern:
            res['money_ness'] = pattern['money_ness']

        if res.get('pattern_price', None):
            pattern_df = self.strategy.insight_book.get_inflex_pattern_df().dfstock_3
            pattern_location = locate_point(pattern_df, max(res['pattern_price']))
            res['pattern_location'] = pattern_location
        if pattern['info'].get('price_list', None) is not None:
            res['pattern_height'] = self.get_pattern_height()
        res['strength'] = pattern['strength']
        return res

    def get_activation_dependency(self):
        status = True
        for st in self.activation_dependency.values():
            status = status and st
        return status

    def forward_signal(self, info={}):
        info = {'code': 'signal', 'n_id': self.id}
        for channel in self.signal_forward_channels:
            channel(info)

    def forward_activation(self, status):
        info = {'code': 'activation', 'n_id' : self.id, 'status':status}
        for channel in self.activation_forward_channels:
            channel(info)

    def add_activation_forward_channel(self, channel):
        self.activation_forward_channels.append(channel)

    def add_signal_forward_channel(self, channel):
        self.signal_forward_channels.append(channel)

    def remove_activation_forward_channel(self, channel):
        self.activation_forward_channels.remove(channel)

    def remove_signal_forward_channel(self, channel):
        self.signal_forward_channels.remove(channel)

    def reverse_signal_received(self):
        #print('Neuron id==', repr(self.id), "REVERSE  LOG")
        if self.signals and len(self.signals) < self.min_activation_strength:
            self.signals = []
        self.check_activation()

    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            #print('receive_communication activation', self.id, info)
        if info['code'] == 'signal':
            self.reverse_signal_received()
            #print('receive_communication reverse signal', self.id, info)


    def send_communication(self):
        pass

    def pre_log(self):
        print('Neuron id==',  repr(self.id), "PRE  LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.get_activation_dependency(), 'current count ==', len(self.signals))

    def post_log(self):
        print('Neuron id==', repr(self.id), "POST LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.get_activation_dependency(), 'current count ==', len(self.signals))

    def communication_log(self, info):
        print('Neuron id==', repr(self.id), "COM  LOG", 'From Neuron id==', info['n_id'], "code==", info['code'], "status==",info.get('status', None))

    def check_activation(self):
        if len(self.signals) >= self.min_activation_strength:
            new_status = True
            if self.register_instr:
                self.strategy.register_instrument(self.signals[-1])
        else:
            new_status = False
        if new_status != self.active:
            self.active = new_status
            self.forward_activation(new_status)
            self.post_log()

class CurrentMemoryPurgeableNeuron(Neuron):   #FreshNoHist(Neuron)
    """Always keeps the last signal"""
    def receive_signal(self, signal):
        self.pre_log()
        if self.get_activation_dependency():
            self.signals = [signal]
            self.last_signal_time = signal['signal_time']
            self.pending_trade_eval = True
            self.forward_signal()
            self.check_activation()


class FixedForLifeNeuron(Neuron): #BinaryCurrentOrHistory
    """Always keeps the last signal"""
    def receive_signal(self, signal):
        if not self.signals:
            self.signals = [signal]
            self.last_signal_time = signal['signal_time']
            self.pending_trade_eval = True
            self.active = True
            self.forward_signal()
            self.forward_activation(True)

    def flush(self):
        pass

    def check_validity(self):
        pass

    def remove_last(self):
        pass


class CurrentMemoryNonPurgeableNeuron(Neuron): #FreshOnlyNoFlushSignalQueue
    """Always keeps the last signal and never flushes"""
    def receive_signal(self, signal):
        if self.get_activation_dependency():
            self.signals = [signal]
            self.last_signal_time = signal['signal_time']
            self.pending_trade_eval = True
            self.forward_signal()
            if len(self.signals) >= self.min_activation_strength:
                self.active = True
                self.forward_activation(True)


    def flush(self):
        pass

    def check_validty(self):
        pass

    def remove_last(self):
        pass


class UniqueHistPurgeableNeuron(Neuron): #NoDuplicateSeries
    """
    Accumulates all fresh signals which are not duplicate
    """
    def receive_signal(self, signal):
        self.pre_log()
        if self.get_activation_dependency():
            if signal['signal_time'] != self.last_signal_time:
                self.signals.append(signal)
                self.last_signal_time = signal['signal_time']
                self.pending_trade_eval = True
                self.forward_signal()
                self.check_activation()

class NonEvaluatedFreshSignalOnlyQueue(Neuron):
    """
    Keeps only latest signals and allows evaluation for signals which are not evaluated earlier
    """
    def receive_signal(self, signal):
        print('NonEvaluatedFreshSignalOnlyQueue+++++++++++ receive', 'id==',repr(self.id), "cat==", self.signal_type, signal)
        self.signals = [signal]
        self.last_signal_time = signal['signal_time']
        self.pending_trade_eval = True
        return True

    def has_signal(self):
        return bool(self.signals) and self.pending_trade_eval


class PriceAction(UniqueHistPurgeableNeuron):
    # get_overlap([matched_pattern['time_list'][1], matched_pattern['time_list'][2]], [self.last_match['time_list'][1], self.last_match['time_list'][2]])
    def get_pattern_height(self, pos=-1):
        #print('execute+++++++get_pattern_height')
        pattern = self.signals[pos]
        #print(pattern)
        pattern_match_prices = pattern['info']['price_list'] if ('INDICATOR_' in pattern['indicator'] and 'TREND' not in pattern['indicator']) else [0, 0, 0, 0]
        #print(pattern_match_prices)
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = lowest_high_point - neck_point
        return pattern_height

    # Should solve for all patterns. we should check
    def get_pattern_target(self, pos=-1, ref_point= -1, factor=1):
        height = self.get_pattern_height(pos)
        pattern = self.signals[pos]
        pattern_match_prices = pattern['info']['price_list'] if ('INDICATOR_' in pattern['indicator'] and 'TREND' not in pattern['indicator']) else [0, 0, 0, 0]
        return pattern_match_prices[ref_point] + factor * height
        #return {'dist': height, 'ref' : pattern_match_prices[ref_point]}
