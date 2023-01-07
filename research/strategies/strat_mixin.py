class PatternMetricRecordMixin:
    def __init__(self, record_metric):
        self.record_metric = record_metric

    def record_params(self, matched_pattern):
        #print('inside record_params', matched_pattern)
        #print(self.insight_book.activity_log.locate_price_region())
        if self.record_metric:
            #pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
            #pattern_location = self.locate_point(pattern_df, matched_pattern['candle'][3])
            #last_wave = self.insight_book.get_prior_wave(matched_pattern['time'])
            self.signal_params['pattern_time'] = [matched_pattern['time']]
            self.signal_params['pattern_price'] = [matched_pattern['candle']]
            self.signal_params['strength'] = matched_pattern['strength']
            #self.signal_params['pattern_location'] = pattern_location
            price_region = self.insight_book.activity_log.locate_price_region()
            for key, val in price_region.items():
                self.signal_params['pat_' + key] = val

            """
            keys = ['total_energy_pyr', 'total_energy_ht', 'static_ratio', 'dynamic_ratio', 'd_en_ht', 's_en_ht',
                    'd_en_pyr', 's_en_pyr']
            for key in keys:
                self.signal_params['lw_' + key] = last_wave[key]
            """