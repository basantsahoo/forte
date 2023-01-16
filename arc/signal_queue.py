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
        #print(self.category[0])
        if self.category[0] in ['STATE', 'TREND']:
            self.queue = [signal] # Always refresh
        else:
            if signal['signal_time'] != self.last_signal_time:
                self.queue.append(signal)
        self.last_signal_time = signal['signal_time']
        #print('self.queue++++++++++++++', self.queue)

    def get_signal(self, pos=-1):
        return self.queue[pos]

    def has_signal(self):
        return len(self.queue) > 0

    def flush_queue(self):
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0] or 'TREND' in self.category[0]:
            self.queue = []

    def remove_last(self):
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0] or 'TREND' in self.category[0]:
            del self.queue[-1]

    def has_signal(self):
        return bool(self.queue)

    def eval_criteria(self, criteria, curr_ts):
        #print(criteria)
        pattern = self.queue[criteria[0]]
        #print(pattern)
        signal = pattern['signal']
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        pattern_match_prices = pattern['price_list'] if 'PATTERN' in pattern['category'] else [0, 0, 0, 0]
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = lowest_high_point - neck_point

        test = criteria[1] + criteria[2] + repr(criteria[3])
        res = eval(test)
        return res