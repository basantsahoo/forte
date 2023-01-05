from research.strategies.core_strategy import BaseStrategy
from research.strategies.strat_mixin import PatternMetricRecordMixin
from helper.utils import pattern_param_match, get_broker_order_type, get_overlap
from statistics import mean
import math
from db.market_data import get_candle_body_size

class OpeningBearishTrendStrategy(BaseStrategy, PatternMetricRecordMixin):
    def __init__(self, insight_book, pattern="DUMMY", order_type="BUY", exit_time=10, period=5, trend=None, min_tpo=1, max_tpo=1, record_metric=True, triggers_per_signal=1, target=0.002, stop_loss=0.001):
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
        self.candle_stats = []

    def get_trades(self, idx=1, curr_price=None,):
        side = get_broker_order_type(self.order_type)
        last_candle = self.insight_book.last_tick
        close_point = last_candle['close']
        if idx == 1:
            return {'seq': idx, 'target': close_point * (1 + side * 0.001), 'stop_loss': close_point * (1 - side * 0.001), 'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': 0, 'trigger_time':last_candle['timestamp']}
        elif idx == 2:
            return {'seq': idx, 'target': close_point * (1 + side * 0.003), 'stop_loss': close_point * (1 - side * 0.0015), 'duration': self.exit_time + 10, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': 0, 'trigger_time':last_candle['timestamp']}

    def add_tradable_signal(self, matched_pattern):
        sig_key = self.add_new_signal()
        self.tradable_signals[sig_key]['pattern'] = matched_pattern
        self.tradable_signals[sig_key]['max_triggers'] = 1
        return sig_key

    def suitable_market_condition(self,matched_pattern):
        enough_time = self.insight_book.get_time_to_close() > self.exit_time
        suitable_tpo = (self.max_tpo >= self.insight_book.curr_tpo) and (self.min_tpo <= self.insight_book.curr_tpo)
        return enough_time and suitable_tpo #and len(self.insight_book.market_data.items()) <= 15

    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_trades(trd_idx) for trd_idx in range(next_trigger, next_trigger + self.triggers_per_signal)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type, sig_key, triggers)

    def set_up(self):
        self.candle_stats = get_candle_body_size(self.insight_book.ticker, self.insight_book.trade_day)

    def get_candle_trend(self,chunks_ohlc):
        candle_size_trends = []
        candle_direction_trends = []
        overlap_trends = []
        return_trends = []
        for i in range(len(chunks_ohlc)):
            candle = chunks_ohlc[i]
            # print(candle)
            open = candle[0]
            high = candle[1]
            low = candle[2]
            close = candle[3]
            body = abs(close - open)
            length = high - low
            tail = length - body
            mid = 0.5 * (high + low)
            ut = high - max(close, open)
            lt = min(close, open) - low
            print(self.candle_stats)
            print(length)
            # exclude candles below 30th percentile
            if length < self.candle_stats[0]:
                pass
            # less than 50th percentile keep only large candle bodies
            elif length < self.candle_stats[1]:
                if body >= 0.8 * length:
                    if close > open:
                        candle_size_trends.append(0.5)
                    else:
                        candle_size_trends.append(-0.5)
            # less than 70th percentile apply weights
            elif length < self.candle_stats[2]:
                if body >= 0.8 * length:
                    if close > open:
                        candle_size_trends.append(0.7)
                    else:
                        candle_size_trends.append(-0.7)
                elif body >= 0.3 * length:
                    if ut > 2 * lt:
                        if close < open:
                            candle_size_trends.append(-0.7/2)
                    elif lt > 2 * ut:
                        if open < close:
                            candle_size_trends.append(0.7/2)
                elif ut > 2.5 * lt:
                    candle_size_trends.append(-0.7)
                elif lt > 2.5 * ut:
                    candle_size_trends.append(0.7)
            # > 70th percentile
            else:
                print('above 70th percentile')
                print(candle)
                print(length, body, ut, lt)
                if body >= 0.8 * length:
                    if close > open:
                        candle_size_trends.append(1)
                    else:
                        candle_size_trends.append(-1)
                elif body >= 0.3 * length:
                    if ut > 2 * lt:
                        if close < open:
                            candle_size_trends.append(-1/2)
                    elif lt > 2 * ut:
                        if open < close:
                            candle_size_trends.append(1/2)
                elif ut > 2.5 * lt:
                    candle_size_trends.append(-1)
                elif lt > 2.5 * ut:
                    candle_size_trends.append(1)
            if i > 0:
                prev_candle = chunks_ohlc[i - 1]
                prev_mid = 0.5 * (prev_candle[1] + prev_candle[2])
                dir = 0
                if mid > (1 + 0.0009) * prev_mid:
                    dir = 0.3
                elif mid < (1 - 0.0009) * prev_mid:
                    dir = -0.3
                candle_direction_trends.append(dir)
                curr_range = list(range(int(math.floor(low)), int(math.ceil(high)) + 1, 1))
                prev_range = list(range(int(math.floor(prev_candle[2])), int(math.ceil(prev_candle[1])) + 1, 1))
                overlap = list(set(curr_range) & set(prev_range))
                overlap_pct = len(overlap) / len(prev_range)
                if overlap_pct < 0.5:
                    overlap_trends.append(dir)
                else:
                    overlap_trends.append(0)
        avg_candle_size_trend = mean(candle_size_trends) if len(candle_size_trends) > 0 else 0
        avg_candle_direction_trend = mean(candle_direction_trends) if len(candle_direction_trends) > 0 else 0
        avg_overlap_trend = mean(overlap_trends) if len(overlap_trends) > 0 else 0
        return [avg_candle_size_trend, avg_candle_direction_trend, avg_overlap_trend]

    def calculate_measures(self):
        price_list = list(self.insight_book.market_data.values())
        if len(price_list) < 2:
            return
        chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
        chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]
        self.five_min_trend = self.get_candle_trend(chunks_5_ohlc)[0]

    def process_pattern_signal(self, matched_pattern):
        self.calculate_measures()
        #print('process patter signal in strategy')
        print('minutes past 22222===', len(list(self.insight_book.market_data.keys())))
        #print('trend calculated =====', 'five_min_trend' in self.insight_book.market_insights)
        if 'five_min_trend' not in self.insight_book.market_insights or not self.allowed_trades:
            return
        five_min_trend = self.five_min_trend
        print('five_min_trend', five_min_trend)
        if five_min_trend >= 0:
            return
        #print('process_pattern_signal+++++++++++')
        # looking for overlap in time
        last_match_ol = 0 if self.last_match is None else int(five_min_trend >= self.last_match)
        #print(last_match_ol)
        """
        determine whether a new signal
        """
        if not last_match_ol and self.suitable_market_condition(None):
            self.last_match = five_min_trend
            # print('received new pattern++++', matched_pattern)
            """
            Control when a signal is considered for trade
            """
            last_tick = self.insight_book.last_tick
            if self.record_metric:
                self.strategy_params['pattern_time'] = last_tick['timestamp']
                self.strategy_params['pattern_price'] = [last_tick['close']]
                self.strategy_params['pattern_location'] = self.five_min_trend
            sig_key = self.add_tradable_signal(five_min_trend)
            self.initiate_signal_trades(sig_key)

    def evaluate(self):
        self.process_pattern_signal(None)
        self.process_incomplete_signals()
        self.monitor_existing_positions()

