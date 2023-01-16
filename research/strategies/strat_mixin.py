class PatternMetricRecordMixin:
    def __init__(self, record_metric):
        self.record_metric = record_metric

    def record_params(self):
        #print('inside record_params', matched_pattern)
        #print(self.insight_book.activity_log.locate_price_region())
        if self.record_metric:
            price_region = self.insight_book.activity_log.locate_price_region()
            for key, val in price_region.items():
                self.signal_params['pat_' + key] = val
            for pattern_queue in self.entry_signal_queues.values():
                pattern_attr = pattern_queue.get_atrributes()
                self.signal_params = {**self.signal_params, **pattern_attr}

class OptionMetricRecordMixin:
    def __init__(self, record_metric):
        self.record_metric = record_metric

    def record_params(self, matched_pattern):
        if self.record_metric:
            self.signal_params['pattern_time'] = [matched_pattern['time']]
            self.signal_params['pattern_price'] = [matched_pattern['candle']]
            self.signal_params['strength'] = matched_pattern['strength']

