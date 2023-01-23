from research.core_strategies.t_core_strategy import BaseStrategy

class PipeStrategy(BaseStrategy):
    def __init__(self,insight_book, **kwargs):
        BaseStrategy.__init__(self, insight_book, **kwargs)
        self.signal_pipeline = None

    def register_signal(self, signal):
        self.signal_pipeline.register_signal(signal)
        if (signal['category'], signal['indicator']) in self.exit_signal_queues:
            self.exit_signal_queues[(signal['category'], signal['indicator'])].receive_signal(signal)

    def evaluate_entry_signals(self):
        return self.signal_pipeline.evaluate_entry_signals()

    def all_entry_signal(self):
        return self.signal_pipeline.all_entry_signal()

    def flush_queues(self):
        self.signal_pipeline.flush_queues()

