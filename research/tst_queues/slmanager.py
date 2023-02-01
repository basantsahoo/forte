class SLManager:
    def __init__(self, neuron, watcher_id, watcher_info, threshold):
        self.entry_price = 0
        self.pnl = 0
        self.signal_type = 'CANDLE'
        self.neuron = neuron
        self.id = watcher_id
        self.signal_type = watcher_info['signal_type']
        self.min_activation_strength = watcher_info['min_activation_strength']
        self.life_span = watcher_info['life_span']
        self.threshold = threshold
        self.threshold_type = 'high'
        self.activation_forward_channels = []
        self.active = False
        self.signals = []
        self.code = 'watcher_update_signal'
        self.creation_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']

    def receive_signal(self, signal):
        self.pre_log()
        self.signals.append(signal)
        self.check_position()

    def check_position(self):
        return True
    def life_span_complete(self):
        last_tick_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        return last_tick_time - self.creation_time > self.life_span * 60
