from research.queues.signal_queue import get_queue
from research.strategies.signal_setup import get_signal_key, get_target_fn


class QNetwork:
    def __init__(self, strategy, signal_queues):
        self.queue_dict = {}
        self.strategy = strategy
        for signal_queue in signal_queues:
            self.add_queue(signal_queue)

    def add_queue(self, q_entry):
        if q_entry['id'] not in self.queue_dict:
            q_signal_key = get_signal_key(q_entry['signal_type'])
            self.queue_dict[q_entry['id']] = {'queue': get_queue(self.strategy, q_signal_key, q_entry['flush_hist']), 'eval_criteria': q_entry['eval_criteria'], 'dependent_on': q_entry['dependent_on']}

    def register_signal(self, signal):
        if signal['category'] in ['STATE']:
            proceed = True
        else:
            proceed = self.strategy.evaluate_signal_filter(signal)
        if proceed:
            for q_id, queue_item in self.queue_dict.items():
                if (signal['category'], signal['indicator']) == queue_item['queue'].category:
                    dependent_on_queues = [self.queue_dict[q_id]['queue'] for q_id in queue_item['dependent_on']]
                    dependency_check = not dependent_on_queues or (dependent_on_queues and all([queue.has_signal() for queue in dependent_on_queues]))
                    if dependency_check:
                        new_signal = queue_item['queue'].receive_signal(signal)
                        if new_signal:
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
