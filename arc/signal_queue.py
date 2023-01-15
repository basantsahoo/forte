class SignalQueue:
    def __init__(self, cat):
        self.category = cat
        self.queue = []
        self.last_signal_time = None
        """
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0]:
            self.queue = []
        """
    def receive_signal(self, signal):
        print(self.category[0])
        if self.category[0] in ['STATE', 'TREND']:
            self.queue = [signal] # Always refresh
        else:
            if signal['signal_time'] != self.last_signal_time:
                self.queue.append(signal)
        self.last_signal_time = signal['signal_time']
        print('self.queue++++++++++++++', self.queue)
    def get_last_signal(self):
        return self.queue[-1]

    def has_signal(self):
        return len(self.queue) > 0

    def flush_queue(self):
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0] or 'TREND' in self.category[0]:
            self.queue = []

    def remove_last(self):
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0] or 'TREND' in self.category[0]:
            del self.queue[-1]
