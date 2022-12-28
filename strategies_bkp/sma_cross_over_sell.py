
import numpy as np
from strategies.bs_strat import BaseStrategy
from helper.utils import get_exit_order_type

class SMACrossSell(BaseStrategy):
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None, short_sma=5, long_sma=10):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.short_sma = short_sma
        self.long_sma = long_sma
        self.entry_triggers = [['self.th_time_lapsed_since_mkt_open(5)', 'self.candle_type_5min("test")']]
        self.exit_triggers = [['self.th_time_lapsed_since_trade_begin(15)'], ['self.target_achieved(0.01)'], ['self.stoploss(0.005)']]
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005

    def evaluate(self):
        s_ma = self.insight_book.get_sma(self.short_sma)
        l_ma = self.insight_book.get_sma(self.long_sma)
        if (s_ma < l_ma) and len(self.existing_orders) == 0:
            self.trigger_entry('SELL')
        elif (s_ma < l_ma) and len(self.existing_orders) > 0:
            self.trigger_exit()

        fifteen_min_trend = abs(self.story_book.intraday_trend.fifteen_min_ex_first_hr_trend)
        if self.story_book.curr_print is not None and self.story_book.curr_print >= 9 and not self.trade_opp :#and fifteen_min_trend <= 0.2:
            if self.story_book.range['low'] == self.story_book.last_tick['low']:
                self.trade_opp = True
                self.trade_opp_time = self.story_book.last_tick['timestamp']
                last_5_min_data = list(self.story_book.market_data.items())[-5:]
                last_5_min_high = max([x[1]['high'] for x in last_5_min_data])
                self.ref_b4_trade_opn = last_5_min_high
                #price_bin_counts = list(np.sum(self.story_book.market_profile['print_matrix'], axis=0).A1)
                #self.distr_stats = [stats.skew(price_bin_counts), stats.kurtosis(price_bin_counts), self.story_book.intraday_trend.whole_day_trend]
                #self.distr_stats = [self.story_book.intraday_trend.first_hour_trend, self.story_book.intraday_trend.whole_day_trend, self.story_book.intraday_trend.five_min_trend, self.story_book.intraday_trend.fifteen_min_trend]

                self.distr_stats = [self.story_book.intraday_trend.five_min_ex_first_hr_trend,
                                    self.story_book.intraday_trend.fifteen_min_ex_first_hr_trend]
                self.story_book.intraday_trend.print_calc = True
                #self.hourly_five_trend = self.story_book.intraday_trend.hourly_5_min_candle_trend
                #self.hourly_fifteen_trend = self.story_book.intraday_trend.hourly_15_min_candle_trend
                print('Range trade low time', datetime.fromtimestamp(self.story_book.last_tick['timestamp']))

        if self.trade_opp and not self.trade_open:
            last_candle = next(reversed(self.story_book.market_data.items()))[1]
            if (last_candle['timestamp'] - self.trade_opp_time) >= 5*60:
                last_5_min_data = list(self.story_book.market_data.items())[-5:]
                last_5_min_close = [x[1]['close'] for x in last_5_min_data]
                if max(last_5_min_close) < self.ref_b4_trade_opn:
                    self.trade_open = True
                    print('Range trade open time', datetime.fromtimestamp(last_candle['timestamp']), last_candle['close'])
                    self.trade_time = datetime.fromtimestamp(last_candle['timestamp'])
                    self.trade_price = last_candle['close']
        self.close_trade()

    def close_trade(self):
        if self.trade_open and not self.trade_close:
            last_candle = next(reversed(self.story_book.market_data.items()))[1]
            if last_candle['low'] < (self.trade_price - 60):
                self.pnl = 60
                print('Range trade Target Close', datetime.fromtimestamp(last_candle['timestamp']), self.trade_time.strftime("%A"), last_candle['close'], 'target', self.pnl)
                self.trade_close = True
                print(self.distr_stats)
                #print(self.hourly_five_trend)
                #print(self.hourly_fifteen_trend)

            if last_candle['high'] > (self.trade_price + 30):
                self.pnl = -30
                self.trade_close = True
                print('Range trade Stoploss', datetime.fromtimestamp(last_candle['timestamp']), self.trade_time.strftime("%A"), last_candle['close'], 'stoploss', self.pnl)
                print(self.distr_stats)
                #print(self.hourly_five_trend)
                #print(self.hourly_fifteen_trend)

    def trigger_entry(self, order_type):
        self.executed_orders += 1
        self.trigger_id += 1
        self.trade_open_time = self.insight_book.last_tick['timestamp']
        self.trade_open_price = self.last_tick['close']
        self.pm.strategy_signal(self.insight_book.ticker, self.id, self.last_time, self.trigger_id, order_type)
        self.existing_orders.append(self.trigger_id)

    def trigger_exit(self):
        self.trade_close_time = self.insight_book.last_tick['timestamp']
        self.trade_close_price = self.last_tick['close']
        self.pm.strategy_signal(self.symbol, self.id, self.last_time, self.trigger_id)
        self.existing_orders.remove(self.trigger_id)


