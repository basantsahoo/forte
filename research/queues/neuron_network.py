from research.queues.neurons import get_neuron
from research.queues.watchers import get_watcher
from research.strategies.signal_setup import get_signal_key, get_target_fn
from collections import OrderedDict


class QNetwork:
    def __init__(self, strategy, signal_neurons_info):
        self.neuron_dict = OrderedDict()
        self.strategy = strategy
        self.signal_neurons_info = signal_neurons_info
        for signal_neuron in signal_neurons_info:
            self.add_neuron(signal_neuron)
        self.watcher_dict = OrderedDict()

    def get_neuron_info_from_id(self, n_id):
        for signal_neuron in self.signal_neurons_info:
            if signal_neuron['id'] == n_id:
                return signal_neuron

    def create_if_not_exists(self, neuron):
        if neuron['id'] not in self.neuron_dict:
            q_signal_key = get_signal_key(neuron['signal_type'])
            self.neuron_dict[neuron['id']] = {
                'neuron': get_neuron(
                    neuron_type=neuron['neuron_type'],
                    manager=self,
                    neuron_id=neuron['id'],
                    signal_type=q_signal_key,
                    min_activation_strength=neuron['min_activation_strength'],
                    trade_eval=neuron['trade_eval'],
                    activation_subscriptions=neuron['activation_subscriptions'],
                    validity_period=neuron.get('validity_period', None),
                    flush_hist=neuron['flush_hist'],
                    register_instr=neuron['register_instr'],
                    watcher_info=neuron.get('watcher_info', {})
                ),
                'register_instr': neuron['register_instr'],
                'apply_pre_filter': neuron['apply_pre_filter']
            }

    def start_watcher(self, neuron_id, watcher_info, signal_info):
        watcher_id = len(self.watcher_dict.keys())
        if watcher_info['type'] in ['HighBreach']:
            threshold = signal_info['high']
        self.watcher_dict[watcher_id] = get_watcher(self, watcher_id, watcher_info, threshold)
        self.create_watcher_link(neuron_id,watcher_id)

    def stop_watcher(self, watcher_id):
        self.watcher_dict[watcher_id].activation_forward_channels = []
        del self.watcher_dict[watcher_id]
        print('watcher id ', watcher_id, ' removed')

    def create_watcher_link(self, neuron_id, watcher_id):
        curr_neuron = self.neuron_dict[neuron_id]['neuron']
        linked_watcher = self.watcher_dict[watcher_id]
        linked_watcher.activation_forward_channels.append(curr_neuron.receive_communication)
        print('watcher id ', watcher_id,  ' created for Neuron id ==', neuron_id)

    def create_backward_link(self, from_id, to_id, link_type="signal"):
        curr_neuron = self.neuron_dict[from_id]['neuron']
        if to_id not in self.neuron_dict:
            tmp_neuron_info = self.get_neuron_info_from_id(to_id)
            self.create_if_not_exists(tmp_neuron_info)
        linked_neuron = self.neuron_dict[to_id]['neuron']
        if link_type == "signal":
            linked_neuron.signal_forward_channels.append(curr_neuron.receive_communication)
        elif link_type == "activation":
            linked_neuron.activation_forward_channels.append(curr_neuron.receive_communication)

    def add_neuron(self, neuron):
        self.create_if_not_exists(neuron)
        for back_neuron_id in neuron['reversal_subscriptions']:
            self.create_backward_link(neuron['id'], back_neuron_id,"signal")
        for back_neuron_id in neuron['activation_subscriptions']:
            self.create_backward_link(neuron['id'], back_neuron_id, "activation")

    def register_signal(self, signal):
        for q_id, queue_item in self.neuron_dict.items():
            if (signal['category'], signal['indicator']) == queue_item['neuron'].signal_type:
                if signal['category'] in ['STATE']:
                    proceed = True
                else:
                    proceed = not queue_item['apply_pre_filter'] or (queue_item['apply_pre_filter'] and self.strategy.pre_signal_filter(signal))
                if proceed:
                    queue_item['neuron'].receive_signal(signal)

    # Entry signal is and
    def evaluate_entry_signals(self):
        passed = True
        for q_id, queue_item in self.neuron_dict.items():
            queue = queue_item['neuron']
            res = queue.eval_entry_criteria()
            print('trade eval status of neuron==== id===', q_id, "status====", res)
            passed = res and passed
            if not passed:
                break
        return passed

    # Exit signal is or
    def evaluate_exit_signals(self):
        passed = False
        for queue_item in self.neuron_dict.values():
            queue = queue_item['neuron']
            res = queue.eval_exit_criteria()
            if res:
                queue.flush()
            passed = passed or res
            if passed:
                break
        return passed

    def all_entry_signal(self):
        #print('all entry signal', [queue_item['neuron'].has_signal() for queue_item in self.neuron_dict.values()])
        return self.neuron_dict and all([queue_item['neuron'].has_signal() for queue_item in self.neuron_dict.values()])

    def flush_queues(self):
        for queue_item in self.neuron_dict.values():
            queue_item['neuron'].flush()

    def get_que_by_category(self, category):
        for q_id, queue_item in self.neuron_dict.items():
            if category == queue_item['neuron'].signal_type:
                return queue_item['neuron']
