
import numpy as np
from strategies_bkp.bs_strat import BaseStrategy
from helper.utils import get_exit_order_type

class SMACrossBuy(BaseStrategy):
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None, record_metric=True, short_sma=5, long_sma=10):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = 'SMA_CROSS_BUY'
        self.short_sma = short_sma
        self.long_sma = long_sma
        self.entry_triggers = [['self.th_time_lapsed_since_mkt_open(5)', 'self.candle_type_5min("test")']]
        self.exit_triggers = [['self.th_time_lapsed_since_trade_begin(15)'], ['self.target_achieved(0.01)'], ['self.stoploss(0.005)']]
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005
        self.record_metric = record_metric
        self.params_repo = {}

    def evaluate(self):
        s_ma = self.insight_book.get_sma(self.short_sma)
        l_ma = self.insight_book.get_sma(self.long_sma)
        #print(s_ma, l_ma)

        if (s_ma < l_ma) and len(self.existing_orders) == 0:
            self.trigger_entry('SELL')
        elif (s_ma > l_ma) and len(self.existing_orders) > 0:
            self.trigger_exit()



