from research.strategies.cheap_option_buy import CheapOptionBuy
from helper.utils import get_broker_order_type

class ThursdayOptionSell(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_SELL_THURS", order_type="SELL", exit_time=60, min_tpo=1, max_tpo=13,  max_signal = 10, target_pct=[0.5,10, 0.5, 10], stop_loss_pct=[0.1,0.9999, 0.1,0.9999]):
        CheapOptionBuy.__init__(self, insight_book, id=id, order_type=order_type, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.last_match = None
        self.weekdays_allowed = ['Thursday']
        self.criteria = [
        ]
        print('ThursdayOptionSell init')

    def get_trades(self, pattern_info, idx=1, neck_point=0):
        instrument = pattern_info['instrument']
        last_candle = self.insight_book.option_processor.get_last_tick(instrument)
        close_point = last_candle['close']
        side = get_broker_order_type(self.order_type)
        neck_point = 0
        return {'seq': idx, 'instrument': instrument, 'cover': 300, 'target': close_point * (1 + side * self.target_pct[idx-1]), 'stop_loss':close_point * (1 - side * self.stop_loss_pct[idx-1]),'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':pattern_info['time']}

    def evaluate_signal(self, matched_pattern):
        print('process_pattern_signal wednesday+++++++++++', matched_pattern)
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
