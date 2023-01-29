class SignalQueue:
    def __init__(self, q_type, size=1, unique_only=True, validity_period=60):
        self.type = q_type
        self.size = size
        self.signals = []
        self.validity_period = validity_period
        self.unique_only = unique_only
        self.last_signal_time = None

    def new_signal(self, signal):
        if self.unique_only and signal['signal_time'] == self.last_signal_time:
            return False
        else:
            if self.type == 'fixed':
                if len(self.signals) < self.size:
                    self.signals.append(signal)
                    self.last_signal_time = signal['signal_time']
                    return True
                else:
                    return False
            elif self.type == "stream":
                if len(self.signals) == self.size:
                    del self.signals[0]
                self.signals.append(signal)
                self.last_signal_time = signal['signal_time']
                return True

            else:
                raise Exception("Signal Queue is not defined")
                return False

    def check_validity(self, last_tick_time):
        last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        self.signals = [signal for signal in self.signals if last_tick_time - signal['signal_time'] < self.validity_period * 60]


    def get_signal(self, pos=-1):
        return self.signals[pos]


    def reset(self):
        self.signals = []
        self.last_signal_time = None