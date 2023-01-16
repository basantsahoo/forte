from helper.utils import locate_point
class SignalQueue:
    def __init__(self, strategy, cat):
        self.category = cat
        self.queue = []
        self.last_signal_time = None
        self.strategy = strategy
        """
        if 'CANDLE' in self.category[0] or 'PATTERN' in self.category[0]:
            self.queue = []
        """
    def receive_signal(self, signal):
        #print(self.category)
        if self.category[0] in ['STATE'] or self.category[1] in ['INDICATOR_TREND']:
            self.queue = [signal] # Always refresh
        else:
            if signal['signal_time'] != self.last_signal_time:
                self.queue.append(signal)
        self.last_signal_time = signal['signal_time']
        #print(self.category, len(self.queue))

    def get_signal(self, pos=-1):
        return self.queue[pos]

    def has_signal(self):
        return len(self.queue) > 0

    def flush(self):
        if 'CANDLE' in self.category[0] or 'PRICE_ACTION' in self.category[0]:
            self.queue = []

    def remove_last(self):
        if 'CANDLE' in self.category[0] or 'PRICE_ACTION' in self.category[0]:
            del self.queue[-1]

    def has_signal(self):
        return bool(self.queue)

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
        #return pattern_match_prices[ref_point] + factor * height
        return {'dist': height, 'ref' : pattern_match_prices[ref_point]}

    def eval_criteria(self, criteria, curr_ts):
        #print(criteria)
        pattern = self.queue[criteria[0]]
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
        res['strength'] = pattern['strength']
        return res
