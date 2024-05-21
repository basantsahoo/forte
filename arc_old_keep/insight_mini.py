# Transitions
from arc_old_keep.common_fn import CommonFN


class InsightBook(CommonFN):

    def pattern_signal_to_remove(self, pattern, pattern_match_idx):
        #print('pattern_signal mini+++++++ 1', pattern, pattern_match_idx['strength'])
        if pattern == 'TREND':
            #print('TREND+++++', pattern, pattern_match_idx)
            self.market_insights = {**self.market_insights, **pattern_match_idx['trend']}
            for wave in pattern_match_idx['all_waves']:
                self.intraday_waves[wave['wave_end_time']] = wave
        for strategy in self.strategies:
            strategy.process_signal(pattern, pattern_match_idx)
            """
            if strategy.is_aggregator:
                strategy.process_signal(pattern, pattern_match_idx)
            elif strategy.price_pattern == pattern:
                strategy.process_signal(pattern_match_idx)
            """

        if self.pm.data_interface is not None:
            self.pm.data_interface.notify_pattern_signal(self.ticker, pattern, pattern_match_idx)
