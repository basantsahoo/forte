from helper.utils import locate_point
from research.queues.signal_queue import SignalQueue
from research.strategies.signal_setup import get_signal_key
from research.queues.watchers import get_watcher
from research.queues.process_logger import ProcessLoggerMixin


class Neuron(ProcessLoggerMixin):
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
        self.reset_on_new_signal_channels = []
        self.signal_forward_channels = []
        self.activation_forward_channels = []
        self.threshold_forward_channels = []
        self.active = False
        self.pending_trade_eval = False
        self.activation_dependency = {}
        self.watcher_list = []
        self.watcher_seq = 0
        self.watcher_thresholds = {'high': None, 'low': None, 'close': None}
        self.last_informed_thresholds = {'high': None, 'low': None, 'close': None}
        for back_neuron_id in kwargs['activation_subscriptions']:
            self.activation_dependency[back_neuron_id] = False
        self.forward_queue = []
        self.display_id = self.manager.strategy.id + " Neuron id ======== " + repr(self.id)


    def receive_activation_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            self.check_activation_status_change()
            self.feed_forward()

    def receive_reset_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'reset_signal':
            self.reset_neuron_signal()

    def receive_signal_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'queue_signal':
            #self.reset_neuron_signal()
            pass

    def receive_watcher_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'watcher_update_signal' or info['code'] == 'watcher_reset_signal':
            self.watcher_action(info)


    def receive_activation_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            self.check_activation_status_change()
            self.feed_forward()
        elif info['code'] == 'reset_signal':
            self.reset_neuron_signal()
        elif info['code'] == 'watcher_update_signal' or info['code'] == 'watcher_reset_signal':
            self.watcher_action(info)

    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            self.check_activation_status_change()
            self.feed_forward()
        elif info['code'] == 'signal':
            self.reset_neuron_signal()
        elif info['code'] == 'watcher_update_signal' or info['code'] == 'watcher_reset_signal':
            self.watcher_action(info)

