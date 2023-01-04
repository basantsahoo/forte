import numpy as np
from db.db_engine import get_db_engine
from datetime import datetime
from scipy import stats
from research.strategies_bkp.bs_strat import BaseStrategy

class RangeBreakDownStrategy(BaseStrategy):
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None, record_metric=True, short_sma=5, long_sma=10):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = 'RNG_BRK_DWN'
        self.trade_opp = False
        self.trade_opp_time = 0
        self.trade_open = False
        self.trade_close = False
        self.trade_price = 0
        self.trade_time = 0
        self.ref_b4_trade_opn = None
        self.record_metric = record_metric
        self.params_repo = {}


    def evaluate(self):
        # Entry related
        if self.insight_book.curr_tpo is not None and self.insight_book.curr_tpo >= 9 and not self.trade_opp :#and fifteen_min_trend <= 0.2:
            if self.insight_book.range['low'] == self.insight_book.last_tick['low']:
                self.trade_opp = True
                self.trade_opp_time = self.insight_book.last_tick['timestamp']
                last_5_min_data = list(self.insight_book.market_data.items())[-5:]
                last_5_min_high = max([x[1]['high'] for x in last_5_min_data])
                self.ref_b4_trade_opn = last_5_min_high

        if self.trade_opp and not self.trade_open:
            last_candle = next(reversed(self.insight_book.market_data.items()))[1]
            if (last_candle['timestamp'] - self.trade_opp_time) >= 5*60:
                last_5_min_data = list(self.insight_book.market_data.items())[-5:]
                last_5_min_close = [x[1]['close'] for x in last_5_min_data]
                if max(last_5_min_close) < self.ref_b4_trade_opn:
                    self.trade_open = True
                    self.trade_time = datetime.fromtimestamp(last_candle['timestamp'])
                    self.trade_price = last_candle['close']
                    self.trigger_entry('SELL')
        # Exit related
        self.close_trade()

    def close_trade(self):
        if self.trade_open and not self.trade_close:
            last_candle = next(reversed(self.insight_book.market_data.items()))[1]
            if last_candle['low'] < (self.trade_price - 60):
                self.trade_close = True
                self.trigger_exit()

            if last_candle['high'] > (self.trade_price + 30):
                self.trade_close = True
                self.trigger_exit()



