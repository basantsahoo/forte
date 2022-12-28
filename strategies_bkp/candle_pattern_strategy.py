import numpy as np
from strategies.bs_strat import BaseStrategy
from helper.utils import get_exit_order_type

class CandlePatternStrategy(BaseStrategy):
    def __init__(self, aggregator, pattern, order_type, exit_time, period, record_metric=True,):
        BaseStrategy.__init__(self, aggregator.insight_book)
        self.id = pattern + "_" + str(period) + "_" + order_type + "_" + str(exit_time)
        #print(self.id)
        self.pattern = pattern
        self.order_type = order_type
        self.aggregator = aggregator
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric

    def evaluate(self):
        self.close_existing_positions()
        pattern_df = self.aggregator.get_pattern_df(self.period)
        #print(pattern_df)
        if pattern_df is not None:
            if self.order_type == 'BUY':
                patterm_match_idx = np.where([pattern_df[self.pattern] > 0])[1]
            elif self.order_type == 'SELL':
                patterm_match_idx = np.where([pattern_df[self.pattern] < 0])[1]
            if len(patterm_match_idx) > 0 and len(self.insight_book.market_data.items()) < 375-self.exit_time:
                if patterm_match_idx[-1] != self.last_match:
                    self.last_match = patterm_match_idx[-1]
                    #print('going to trigger')
                    self.trigger_entry(self.order_type)

    def close_existing_positions(self):
        last_candle = self.insight_book.last_tick
        for order in self.existing_orders:
            if last_candle['timestamp'] - order[1] >= self.exit_time*60:
                self.trigger_exit(order[0])




