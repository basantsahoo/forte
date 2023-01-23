from helper.utils import get_broker_order_type
from research.core_strategies.core_option_strategy import BaseOptionStrategy
from research.strategies.strat_mixin import PatternMetricRecordMixin


class OptionSellStrategy(BaseOptionStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, id="OPTION_SELL", pattern="OPTION_PRICE_DROP", order_type="SELL", exit_time=60, min_tpo=1, max_tpo=13,  max_signal = 10000000, target_pct=[0.5,0.5, 0.5, 0.5], stop_loss_pct=[0.2,0.2, 0.2,0.2], criteria=[]):
        print('OptionSellStrategy init')
        print('self.pattern' , pattern)
        BaseOptionStrategy.__init__(self, insight_book, id=id, pattern=pattern, order_type=order_type, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct, criteria=criteria)
        self.id = pattern + "_" + order_type + "_" + str(exit_time) if id is None else id
        #print(self.id)
        #self.record_metric = False
        self.last_match = None

    def get_trades(self, pattern_info, idx=1, neck_point=0):
        instrument = pattern_info['instrument']
        last_candle = self.insight_book.option_processor.get_last_tick(instrument)
        close_point = last_candle['close']
        side = get_broker_order_type(self.order_type)
        neck_point = 0
        return {'seq': idx, 'instrument': instrument, 'cover': 200, 'target': close_point * (1 + side * self.target_pct[idx-1]), 'stop_loss':close_point * (1 - side * self.stop_loss_pct[idx-1]),'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':pattern_info['time']}

    def evaluate_signal(self, matched_pattern):
        print('process_pattern_signal option sell+++++++++++', matched_pattern)
        last_match_ol = 0
        signal_passed = False
        """
        Control when a signal is considered for trade
        """
        #print("self.suitable_market_condition======", self.suitable_market_condition(matched_pattern))
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern
            print('in evaluate_signal,', self.record_metric)
            matched_pattern['candle'] = [0,0,0,0]
            self.record_params(matched_pattern)
            signal_passed = True
        #print('signal_passed====', signal_passed)
        return signal_passed
