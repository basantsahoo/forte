from helper.utils import locate_point


def get_queue(strategy, category, flush_hist=True):
    if category[0] in ['STATE']:
        return StateSignalQueue(strategy, category, flush_hist)
    elif category[1] in ['INDICATOR_TREND']:
        return TrendSignalQueue(strategy, category, flush_hist)
    elif category in [('OPTION', 'PRICE_DROP')]:
        return OptionPriceDropQueue(strategy, category, flush_hist)
    elif 'PRICE_ACTION' in category[0]:
        return PriceActionQueue(strategy, category, flush_hist)
    elif 'CANDLE' in category[0]:
        return CandleSignalQueue(strategy, category, flush_hist)
    elif 'TECHNICAL' in category[0]:
        return TechnicalSignalQueue(strategy, category, flush_hist)
    else:
        raise Exception("Signal Queue is not defined")


class SignalQueue:
    def __init__(self, strategy, cat, flush_hist=True):
        self.category = cat
        self.queue = []
        self.last_signal_time = None
        self.strategy = strategy
        self.dependent_on_queues = []
        self.pending_evaluation = False
        self.flush_hist = flush_hist

    def receive_signal(self, signal):
        return False
        #print(self.category, len(self.queue))

    def get_signal(self, pos=-1):
        return self.queue[pos]

    def flush(self):
        if self.flush_hist:
            self.queue = []

    def remove_last(self):
        del self.queue[-1]

    def has_signal(self):
        return bool(self.queue)

    def get_pattern_height(self, pos=-1):
        return 0

    def add_dependency(self, queue):
        self.dependent_on_queues.append(queue)

    def eval_entry_criteria(self, test_criteria, curr_ts):
        if not test_criteria:
            return True
        #print(criteria)
        try:
            pattern = self.queue[test_criteria[0]]
        except:
            return False
        #print(pattern)
        strength = pattern['strength']
        signal = pattern.get('signal', "")
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(test_criteria[0])

        test = test_criteria[1] + test_criteria[2] + repr(test_criteria[3])
        """
        print(self.category)
        print(test)
        print(strength)
        """
        res = eval(test)
        self.pending_evaluation = False
        return res

    def eval_exit_criteria(self, criteria, curr_ts):
        #print('eval_exit_criteria', criteria)
        if not criteria:
            return True
        #print(criteria)
        try:
            pattern = self.queue[criteria[0]]
        except:
            return False  # Different from entry

        #print(pattern)
        signal = pattern['signal']
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(criteria[0])

        test = criteria[1] + criteria[2] + repr(criteria[3])
        res = eval(test)
        return res

    def get_atrributes(self, pos=-1):
        res = {}
        pattern = self.queue[pos]
        if pattern['info'].get('price_list', None) is not None:
            res['pattern_price'] = pattern['info']['price_list']
        if pattern['info'].get('time_list', None) is not None:
            res['pattern_time'] = pattern['info']['time_list']
        if pattern['info'].get('time', None) is not None:
            res['pattern_time'] = pattern['info']['time']
        if pattern['info'].get('candle', None) is not None:
            res['pattern_price'] = pattern['info']['candle']
        if pattern['info'].get('time_list', None) is not None:
            res['pattern_time'] = pattern['info']['time_list']

        if 'strike' in pattern:
            res['strike'] = pattern['strike']
        if 'kind' in pattern:
            res['kind'] = pattern['kind']
        if 'money_ness' in pattern:
            res['money_ness'] = pattern['money_ness']

        if res.get('pattern_price', None):
            pattern_df = self.strategy.insight_book.get_inflex_pattern_df().dfstock_3
            pattern_location = locate_point(pattern_df, max(res['pattern_price']))
            res['pattern_location'] = pattern_location
        if pattern['info'].get('price_list', None) is not None:
            res['pattern_height'] = self.get_pattern_height()
        res['strength'] = pattern['strength']
        return res


class PriceActionQueue(SignalQueue):
    def receive_signal(self, signal):
        new_signal = False
        if signal['signal_time'] != self.last_signal_time:
            self.queue.append(signal)
            new_signal = True
            self.pending_evaluation = True
        self.last_signal_time = signal['signal_time']
        return new_signal

    def get_pattern_height(self, pos=-1):
        #print('execute+++++++get_pattern_height')
        pattern = self.queue[pos]
        #print(pattern)
        pattern_match_prices = pattern['info']['price_list'] if ('INDICATOR_' in pattern['indicator'] and 'TREND' not in pattern['indicator']) else [0, 0, 0, 0]
        #print(pattern_match_prices)
        highest_high_point = max(pattern_match_prices[1], pattern_match_prices[3])
        lowest_high_point = min(pattern_match_prices[1], pattern_match_prices[3])
        neck_point = pattern_match_prices[2]
        pattern_height = lowest_high_point - neck_point
        return pattern_height

    # Should solve for all patterns. we should check
    def get_pattern_target(self, pos=-1, ref_point= -1, factor=1):
        height = self.get_pattern_height(pos)
        pattern = self.queue[pos]
        pattern_match_prices = pattern['info']['price_list'] if ('INDICATOR_' in pattern['indicator'] and 'TREND' not in pattern['indicator']) else [0, 0, 0, 0]
        return pattern_match_prices[ref_point] + factor * height
        #return {'dist': height, 'ref' : pattern_match_prices[ref_point]}


class OptionPriceDropQueue(SignalQueue):
    def receive_signal(self, signal):
        self.queue.append(signal)
        self.last_signal_time = signal['signal_time']
        self.pending_evaluation = True
        return True


class TrendSignalQueue(SignalQueue):
    def receive_signal(self, signal):
        self.queue = [signal]
        self.last_signal_time = signal['signal_time']
        self.pending_evaluation = True
        return True


class StateSignalQueue(SignalQueue):
    def receive_signal(self, signal):
        self.queue = [signal]
        self.last_signal_time = signal['signal_time']
        self.pending_evaluation = True
        return True

    def flush(self):
        pass

    def remove_last(self):
        pass


class CandleSignalQueue(SignalQueue):
    def receive_signal(self, signal):
        new_signal = False
        if signal['signal_time'] != self.last_signal_time:
            self.queue.append(signal)
            new_signal = True
            self.pending_evaluation = True
        self.last_signal_time = signal['signal_time']
        return new_signal


class TechnicalSignalQueue(SignalQueue):
    def receive_signal(self, signal):
        self.queue = [signal]
        self.last_signal_time = signal['signal_time']
        self.pending_evaluation = True
        return True

    def has_signal(self):
        return bool(self.queue) and self.pending_evaluation


