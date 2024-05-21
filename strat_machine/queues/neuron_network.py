from strat_machine.queues.neurons import Neuron
from collections import OrderedDict
from strat_machine.queues.switches import get_switch


class QNetwork:
    def __init__(self, strategy, signal_neurons_info, switch_info={}):
        self.neuron_dict = OrderedDict()
        self.strategy = strategy
        self.signal_neurons_info = signal_neurons_info
        self.switch_info = switch_info
        self.switch = None
        for signal_neuron_item in signal_neurons_info:
            self.add_neuron(signal_neuron_item)
        if switch_info:
            self.switch = get_switch(self, switch_info)
            for subscription in switch_info['que_subscriptions']:
                from_id = subscription[0]
                th_type = subscription[1]
                fn = subscription[2]
                back_neuron = self.neuron_dict[from_id]['neuron']
                comm_fn = eval("self.switch." + fn)
                back_neuron.threshold_forward_channels.append({"th_type": th_type, "comm_fn" : comm_fn})

    def get_neuron_info_from_id(self, n_id):
        for signal_neuron in self.signal_neurons_info:
            if signal_neuron['neuron_info']['id'] == n_id:
                return signal_neuron


    def create_if_not_exists(self, signal_neuron_item):
        if signal_neuron_item['neuron_info']['id'] not in self.neuron_dict:
            self.neuron_dict[signal_neuron_item['neuron_info']['id']] = {
                'neuron': Neuron(
                    manager=self,
                    **signal_neuron_item['neuron_info']
                ),
                'apply_pre_filter': signal_neuron_item['apply_pre_filter']
            }

    def create_backward_link(self, from_id, to_id, link_type="signal"):
        curr_neuron = self.neuron_dict[from_id]['neuron']
        if to_id not in self.neuron_dict:
            tmp_neuron_info = self.get_neuron_info_from_id(to_id)
            self.create_if_not_exists(tmp_neuron_info)
        linked_neuron = self.neuron_dict[to_id]['neuron']
        if link_type == "signal":
            linked_neuron.signal_forward_channels.append(curr_neuron.receive_signal)
        elif link_type == "activation":
            linked_neuron.activation_forward_channels.append(curr_neuron.receive_activation_communication)
        elif link_type == "reversal":
            linked_neuron.reset_on_new_signal_channels.append(curr_neuron.receive_reset_communication)
        elif link_type == "high_threshold":
            linked_neuron.signal_forward_channels.append(curr_neuron.receive_high_threshold)
        elif link_type == "low_threshold":
            linked_neuron.signal_forward_channels.append(curr_neuron.receive_low_threshold)

    def add_neuron(self, signal_neuron_item):
        self.create_if_not_exists(signal_neuron_item)
        for back_neuron_id in signal_neuron_item['neuron_info']['reversal_subscriptions']:
            self.create_backward_link(signal_neuron_item['neuron_info']['id'], back_neuron_id, "reversal")
        for back_neuron_id in signal_neuron_item['neuron_info']['activation_subscriptions']:
            self.create_backward_link(signal_neuron_item['neuron_info']['id'], back_neuron_id, "activation")
        for back_neuron_id in signal_neuron_item['neuron_info']['signal_subscriptions']:
            self.create_backward_link(signal_neuron_item['neuron_info']['id'], back_neuron_id, "signal")
        for back_neuron_id in signal_neuron_item['neuron_info']['high_threshold_subscriptions']:
            self.create_backward_link(signal_neuron_item['neuron_info']['id'], back_neuron_id, "high_threshold")
        for back_neuron_id in signal_neuron_item['neuron_info']['low_threshold_subscriptions']:
            self.create_backward_link(signal_neuron_item['neuron_info']['id'], back_neuron_id, "low_threshold")

    def register_signal(self, signal):
        for q_id, queue_item in self.neuron_dict.items():
            #print('neuron network register_signal+++++++++', queue_item['neuron'].id)
            for watcher in queue_item['neuron'].watcher_list:
                if signal.key() == watcher.signal_type:
                    watcher.receive_signal(signal)
            #print(queue_item['neuron'].signal_type)
            queue_item['neuron'].test()
            if signal.key() == queue_item['neuron'].signal_type:
                if signal.category in ['STATE']:
                    proceed = True
                else:
                    proceed = not queue_item['apply_pre_filter'] or (queue_item['apply_pre_filter'] and self.strategy.pre_signal_filter(signal))
                if proceed:
                    queue_item['neuron'].receive_signal(signal)

    # Entry signal is and
    def evaluate_entry_signals(self):
        #print('neuron network evaluate_entry_signals+++++++++')
        passed = True
        for q_id, queue_item in self.neuron_dict.items():
            queue = queue_item['neuron']
            res = queue.eval_entry_criteria()
            print('trade eval status of neuron==== id===', q_id, "status====", res)
            passed = res and passed
            if not passed:
                break
        if passed:
            switch_val = True
            if self.switch:
                switch_val = self.switch.evaluate()
                if switch_val:
                    signal = self.switch.get_signal()
                    if signal:
                        last_spot_tick = self.strategy.get_last_tick('SPOT')
                        signal.signal_time = last_spot_tick['timestamp']
                        signal.notice_time = last_spot_tick['timestamp']
                        self.strategy.asset_book.pattern_signal(signal)
            if not switch_val:
                self.flush_queues()
            return switch_val
        else:
            return False


    # Exit signal is or
    def evaluate_exit_signals(self):
        #print('neuron network evaluate_exit_signals+++++++++')
        passed = False
        for queue_item in self.neuron_dict.values():
            queue = queue_item['neuron']
            res = queue.has_signal() and queue.eval_exit_criteria()
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
        if self.switch:
            self.switch.flush()

    def get_que_by_category(self, category):
        for q_id, queue_item in self.neuron_dict.items():
            if category == queue_item['neuron'].signal_type:
                return queue_item['neuron']

    def get_neuron_by_id(self, n_id):
        queue_item = self.neuron_dict[n_id]
        return queue_item['neuron']

    def check_validity(self):
        for neuron_item in self.neuron_dict.values():
            neuron_item['neuron'].check_validity()
