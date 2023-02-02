from helper.utils import locate_point
from research.queues.signal_queue import SignalQueue
from research.strategies.signal_setup import get_signal_key
from research.queues.watchers import get_watcher


#neuron_type="fifo/fixed",stream_size=1/1000,
class Neuron:
    def __init__(self, manager, **kwargs):
        self.manager = manager
        self.id = kwargs['id']
        self.signal_type = get_signal_key(kwargs['signal_type'])
        self.min_activation_strength = kwargs['min_activation_strength']
        self.max_activation_strength = kwargs['max_activation_strength']
        self.trade_eval = kwargs['trade_eval']
        self.flush_hist = kwargs['flush_hist']
        self.register_instr = kwargs['register_instr']
        self.signal_queue = SignalQueue(**kwargs['signal_queue_info'])
        self.update_watcher_info = kwargs['update_watcher_info']
        self.reset_watcher_info = kwargs['reset_watcher_info']
        self.signal_forward_channels = []
        self.activation_forward_channels = []
        self.threshold_forward_channels = []
        self.active = False
        self.pending_trade_eval = False
        self.activation_dependency = {}
        self.watcher_list = []
        self.watcher_thresholds = {'high': None, 'low': None, 'close':None}
        for back_neuron_id in kwargs['activation_subscriptions']:
            self.activation_dependency[back_neuron_id] = False

    def receive_signal(self, signal):
        #print('receive_signal  ', self.id)
        if self.dependency_satisfied():
            self.add_to_signal_queue(signal)

    def dependency_satisfied(self):
        status = True
        for st in self.activation_dependency.values():
            status = status and st
        return status

    def add_to_signal_queue(self, signal):
        new_signal = self.signal_queue.new_signal(signal)
        if new_signal:
            self.pending_trade_eval = True
            self.forward_signal()
            self.forward_threshold_change()
            self.check_activation_status_change()

    def forward_signal(self, info={}):
        info = {'code': 'signal', 'n_id': self.id}
        for channel in self.signal_forward_channels:
            channel(info)

    def check_activation_status_change(self):
        if (len(self.signal_queue.signals) >= self.min_activation_strength) and (len(self.signal_queue.signals) <= self.max_activation_strength):
            new_status = True
        else:
            new_status = False
        if new_status != self.active:
            print("Neuron id ========", self.id, "status changed. new activation stats=====", new_status)
            if new_status:
                if self.register_instr:
                    self.manager.strategy.register_instrument(self.signals[-1])
                self.create_watchers()
            else:
                self.remove_watchers()
            self.active = new_status
            self.forward_state_change(new_status) #Inform only when changed
            self.post_log()

    def create_watchers(self):
        if self.update_watcher_info:
            self.new_watcher('watcher_update_signal')
        if self.reset_watcher_info:
            self.new_watcher('watcher_reset_signal')

    def new_watcher(self, code='watcher_update_signal'):
        watcher_info = self.update_watcher_info.copy() if code == 'watcher_update_signal' else self.reset_watcher_info.copy()
        q_signal_key = get_signal_key(watcher_info['signal_type'])
        watcher_info['signal_type'] = q_signal_key
        watcher_id = len(self.watcher_list)
        if watcher_info['type'] in ['HighBreach']:
            threshold = self.get_watcher_threshold('high')
        else:
            threshold = self.get_watcher_threshold('close')
        watcher = get_watcher(self, watcher_id, watcher_info, threshold)
        watcher.code = code
        watcher.activation_forward_channels.append(self.receive_communication)
        self.watcher_list.append(watcher)
        print("Watcher id",watcher_id, " created for Neuron id====", self.id)

    def get_watcher_threshold(self, th_type):
        th = self.watcher_thresholds[th_type]
        if th is None:
            th = self.signal_queue.get_signal(-1)['info'][th_type] if self.signal_queue.signals else None
        return th

    def remove_watchers(self, watcher_id=None):
        if watcher_id is None:
            for watcher in self.watcher_list:
                print('watcher id ', watcher.id, ' removed from Neuron id====', self.id)
                watcher.activation_forward_channels = []
            self.watcher_list = []
        else:
            for w in range(len(self.watcher_list)):
                if self.watcher_list[w].id == watcher_id:
                    del self.watcher_list[w]
                    break

    def forward_state_change(self, status):

        info = {'code': 'activation', 'n_id': self.id, 'status':status}
        for channel in self.activation_forward_channels:
            channel(info)

    def forward_threshold_change(self):
        for channel in self.threshold_forward_channels:
            th_type = channel['th_type']
            comm_fn = channel['comm_fn']
            th = self.get_watcher_threshold(th_type)
            comm_fn(th_type, th)

    def flush(self):
        if self.flush_hist:
            self.reset()

    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            #print('receive_communication activation', self.id, info)
        elif info['code'] == 'signal':
            self.reset_neuron_signal()
        elif info['code'] == 'watcher_update_signal':
            self.watcher_thresholds[info['threshold_type']] = info['new_threshold']
            self.forward_threshold_change()
            self.remove_watchers()
            self.create_watchers()
        elif info['code'] == 'watcher_reset_signal':
            self.reset()

    def reset_neuron_signal(self):
        #print('Neuron id==', repr(self.id), "REVERSE  LOG")
        if not self.active:
            self.reset()

    def reset(self):
        self.forward_threshold_change()
        self.signal_queue.reset()
        self.remove_watchers()
        self.watcher_thresholds = {'high': None, 'low': None, 'close': None}
        self.check_activation_status_change()

    def check_validity(self):
        last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        self.signal_queue.check_validity(last_tick_time)
        self.check_activation_status_change()
        for watcher in self.watcher_list:
            if watcher.life_span_complete():
                del watcher

    def has_signal(self):
        return self.active

    def pre_log(self):
        last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        print(last_tick_time, ' Neuron id==',  repr(self.id), "PRE  LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.dependency_satisfied(), 'current count ==', len(self.signal_queue.signals))

    def post_log(self):
        print('Neuron id==', repr(self.id), "POST LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.dependency_satisfied(), 'current count ==', len(self.signal_queue.signals))

    def communication_log(self, info):
        last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        if info['code'] not in ['watcher_update_signal', 'watcher_reset_signal']:
            print(last_tick_time, ' Neuron id==', repr(self.id), "COM  LOG", 'From Neuron id==', info['n_id'], "sent code==", info['code'], "==" ,info.get('status', None))
        else:
            print(last_tick_time, ' Neuron id==', repr(self.id), "COM  LOG", 'From Watcher id==', info['n_id'], "sent code==", info['code'], "==" ,info.get('status', None))

    def get_attributes(self, pos=-1):
        res = {}
        pattern = self.signal_queue.get_signal(pos)
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
            pattern_df = self.manager.strategy.insight_book.get_inflex_pattern_df().dfstock_3
            pattern_location = locate_point(pattern_df, max(res['pattern_price']))
            res['pattern_location'] = pattern_location
        if pattern['info'].get('price_list', None) is not None:
            res['pattern_height'] = self.get_pattern_height()
        res['strength'] = pattern['strength']
        return res

    def get_pattern_height(self, pos=-1):
        return 0

    def eval_entry_criteria(self):
        test_criteria = self.trade_eval
        curr_ts = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
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
        curr_ts = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
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

    def get_signal_high(self):
        return self.get_watcher_threshold('high')
        #signal = self.signal_queue.get_signal(-1)
        #return signal['info']['high']


class CurrentMemoryPurgeableNeuron2(Neuron):   #FreshNoHist(Neuron) #Changed to fixed for life for test
    """Always keeps the last signal"""
    def receive_signal(self, signal):
        #self.pre_log()
        if self.get_activation_dependency() and not self.signals:
            self.signals = [signal]
            self.last_signal_time = signal['signal_time']
            self.pending_trade_eval = True
            self.forward_signal()
            self.check_activation()

    def get_signal_high(self):
        signal = self.get_signal(-1)
        print(signal)
        return signal['info']['high']

class UniqueHistPurgeableNeuron2(Neuron): #NoDuplicateSeries
    """
    Accumulates all fresh signals which are not duplicate
    """
    def receive_signal(self, signal):
        #self.pre_log()
        if self.get_activation_dependency():
            if signal['signal_time'] != self.last_signal_time:
                self.signals.append(signal)
                self.last_signal_time = signal['signal_time']
                self.pending_trade_eval = True
                self.forward_signal()
                self.check_activation()
