from research.queues.neurons import get_queue
from research.strategies.signal_setup import get_signal_key, get_target_fn
from collections import OrderedDict


class QNetwork:
    def __init__(self, strategy, signal_neurons_info):
        self.neuron_dict = OrderedDict()
        self.strategy = strategy
        self.signal_neurons_info = signal_neurons_info
        for signal_neuron in signal_neurons_info:
            self.add_neuron(signal_neuron)

    def get_neuron_info_from_id(self, n_id):
        for signal_neuron in self.signal_neurons_info:
            if signal_neuron['id'] == n_id:
                return signal_neuron

    def create_if_not_exists(self, neuron):
        if neuron['id'] not in self.neuron_dict:
            q_signal_key = get_signal_key(neuron['signal_type'])
            self.neuron_dict[neuron['id']] = {
                'neuron': get_queue(
                    neuron_type=neuron['q_type'],
                    strategy=self.strategy,
                    neuron_id=neuron['id'],
                    signal_type=q_signal_key,
                    min_strength=neuron['min_strength'],
                    trade_eval=neuron['trade_eval'],
                    signal_subscriptions=neuron['signal_subscriptions'],
                    activation_subscriptions=neuron['activation_subscriptions'],
                    validity_period=neuron.get('validity_period', None),
                    flush_hist=neuron['flush_hist'],
                    register_instr=neuron['register_instr']),
                'register_instr': neuron['register_instr']}

    def create_backward_link(self, from_id, to_id):
        curr_neuron = self.neuron_dict[from_id]['neuron']
        if to_id not in self.neuron_dict:
            tmp_neuron_info = self.get_neuron_info_from_id(to_id)
            self.create_if_not_exists(tmp_neuron_info)
        linked_neuron = self.neuron_dict[to_id]['neuron']
        linked_neuron.signal_subscriptions.append(curr_neuron.receive_communication)

    def add_neuron(self, neuron):
        self.create_if_not_exists(neuron)
        for back_neuron_id in neuron['signal_subscriptions']:
            self.create_backward_link(neuron['id'], back_neuron_id)
        for back_neuron_id in neuron['activation_subscriptions']:
            self.create_backward_link(neuron['id'], back_neuron_id)

    def register_signal(self, signal):
        for q_id, queue_item in self.neuron_dict.items():
            if (signal['category'], signal['indicator']) == queue_item['queue'].signal_type:
                if signal['category'] in ['STATE']:
                    proceed = True
                else:
                    proceed = not queue_item['apply_pre_filter'] or (queue_item['apply_pre_filter'] and self.strategy.pre_signal_filter(signal))
                if proceed:
                    queue_item['neuron'].receive_signal(signal)

    def register_signal_2(self, signal):
        if signal['category'] in ['STATE']:
            proceed = True
        else:
            proceed = self.strategy.pre_signal_filter(signal)
        if proceed:
            for q_id, queue_item in self.queue_dict.items():
                if (signal['category'], signal['indicator']) == queue_item['queue'].category:
                    dependent_on_queues = [self.queue_dict[q_id]['queue'] for q_id in queue_item['dependent_on']]
                    dependency_check = not dependent_on_queues or (dependent_on_queues and all([queue.has_signal() for queue in dependent_on_queues]))
                    if dependency_check:
                        new_signal = queue_item['queue'].receive_signal(signal)
                        if new_signal:
                            for forward_item in queue_item['forward_to']:
                                forward_to_queue = self.queue_dict[forward_item[0]]
                                forward_to_fn = forward_item[1]
                                eval('forward_to_queue.forward_to_fn')()
                    if queue_item['queue'].active and queue_item['register_instr']:
                        self.strategy.register_instrument(signal)

    # Entry signal is and
    def evaluate_entry_signals(self):
        passed = True
        for queue_item in self.queue_dict.values():
            queue = queue_item['queue']
            eval_criteria = queue_item['eval_criteria']
            last_spot_candle = self.strategy.insight_book.spot_processor.last_tick
            res = queue.eval_entry_criteria(eval_criteria, last_spot_candle['timestamp'])
            passed = res and passed
            if not passed:
                break
        return passed

    # Exit signal is or
    def evaluate_exit_signals(self):
        passed = False
        for queue_item in self.queue_dict.values():
            queue = queue_item['queue']
            eval_criteria = queue_item['eval_criteria']
            last_spot_candle = self.strategy.insight_book.spot_processor.last_tick
            res = queue.eval_exit_criteria(eval_criteria, last_spot_candle['timestamp'])
            if res:
                queue.flush()
            passed = passed or res
            if passed:
                break
        return passed

    def all_entry_signal(self):
        return self.queue_dict and all([queue_item['queue'].has_signal() for queue_item in self.queue_dict.values()])

    def flush_queues(self):
        for queue_item in self.queue_dict.values():
            queue_item['queue'].flush()

    def get_que_by_category(self, category):
        for q_id, queue_item in self.queue_dict.items():
            if category == queue_item['queue'].category:
                return queue_item['queue']
