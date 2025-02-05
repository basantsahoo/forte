from research.core_strategies.core_strategy import BaseStrategy
from research.strategies.strat_mixin import PatternMetricRecordMixin
from db.market_data import get_candle_body_size

# this is left inprogress
class OpeningT2POC(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, pattern="T2POC", order_type="BUY", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target=0.002, stop_loss=0.001):
        BaseStrategy.__init__(self, insight_book, order_type, min_tpo, max_tpo, target, stop_loss)
        self.id = pattern + "_" + str(period) + "_" + order_type + "_" + str(exit_time)
        self.price_pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend
        self.allowed_trades = 1
        self.triggers_per_signal = triggers_per_signal
        self.criteria = [
                        {'op': 'or', 'logical_test': 'self.insight_book.get_time_to_close() >= 369'}
        ]

    def set_up(self):
        self.candle_stats = get_candle_body_size(self.insight_book.ticker, self.insight_book.trade_day)

    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal_to_journal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['pattern_height'] = 0
        #self.tradable_signals[sig_key]['max_triggers'] = 1
        return sig_key


    def evaluate_signal(self):
        matched_pattern = dict()
        matched_pattern['time'] = self.insight_book.last_tick['timestamp']
        matched_pattern['candle'] = self.insight_book.last_tick
        matched_pattern['strength'] = 1

        last_match_ol = 0 if self.last_match is None else 1
        signal_passed = False
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = 1
            self.record_params(matched_pattern)
            signal_passed = True
        return signal_passed

    def evaluate(self):
        self.evaluate_signal()
        self.process_incomplete_signals()
        self.monitor_existing_positions()

