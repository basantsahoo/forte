import numpy as np
import math
from research.strategies import BaseStrategy


class OpeningDirection(BaseStrategy):
    def __init__(self, sym, trade_day):
        BaseStrategy.__init__(self, sym, trade_day)
        self.entry_triggers = []
        self.exit_triggers = []
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005
        self.opportunity_exists = False
        self.first_appear_time = None
        self.direction_calculated = False

    def profile_input(self, market_profile):
        #print(market_profile)
        self.market_profile = market_profile

    def calculate_direction(self):
        if len(self.market_data) >= 15:
            direction_data = self.market_data[0:min(len(self.market_data),60)]
            #print(len(direction_data))
            chunks_5 = [direction_data[i:i + 5] for i in range(0, len(direction_data), 5)]
            chunks_5 = [x for x in chunks_5 if len(x) == 5]
            chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]

            chunks_15 = [direction_data[i:i + 15] for i in range(0, len(direction_data), 15)]
            chunks_15 = [x for x in chunks_15 if len(x) == 15]
            chunks_15_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_15]
            #print(chunks_15_ohlc)
            candle_size_trends = []
            candle_direction_trends = []
            overlap_trends = []
            return_trends = []
            for i in range(len(chunks_5_ohlc)):
                candle = chunks_5_ohlc[i]
                #print(candle)
                open = candle[0]
                high = candle[1]
                low = candle[2]
                close = candle[3]
                body = abs(close - open)
                length = high - low
                tail = length-body
                mid = 0.5* (high + low)
                ut = high - max(close, open)
                lt = min(close, open)-low
                if body >= 0.7 * length:
                    if close > open:
                        candle_size_trends.append(1)
                    else:
                        candle_size_trends.append(-1)
                elif body >= 0.3 * length:
                    if ut > 2 * lt:
                        if close < open:
                            candle_size_trends.append(-1)
                        else:
                            candle_size_trends.append(0)
                    elif lt > 2 * ut:
                        if open < close:
                            candle_size_trends.append(1)
                        else:
                            candle_size_trends.append(0)
                    else:
                        candle_size_trends.append(0)
                elif ut > 2.5 * lt:
                    candle_size_trends.append(-1)
                elif lt > 2.5 * ut:
                    candle_size_trends.append(1)
                else:
                    candle_size_trends.append(0)
                if i > 0:
                    prev_candle = chunks_5_ohlc[i-1]
                    prev_mid = 0.5*(prev_candle[1] + prev_candle[2])
                    dir = 0
                    if mid > (1 + 0.0009) * prev_mid:
                        dir = 1
                    elif mid < (1 - 0.0009) * prev_mid:
                        dir = -1
                    candle_direction_trends.append(dir)
                    curr_range = list(range(int(math.floor(low)),int(math.ceil(high))+1,1))
                    prev_range = list(range(int(math.floor(prev_candle[2])), int(math.ceil(prev_candle[1])) + 1, 1))
                    overlap = list(set(curr_range) & set(prev_range))
                    overlap_pct = len(overlap)/len(prev_range)
                    if overlap_pct < 0.5:
                        overlap_trends.append(dir)
                    else:
                        overlap_trends.append(0)
                    if close < prev_candle[3]:
                        return_trends.append(-1)
                    else:
                        return_trends.append(1)
            """
            print(candle_size_trends)
            print(candle_direction_trends)
            print(overlap_trends)
            print(return_trends)
            """
            #trend = 0.25 * (np.sign(sum(candle_size_trends)) + np.sign(sum(candle_direction_trends)) + np.sign(sum(overlap_trends)) + np.sign(sum(return_trends)))
            trend = 0.25 * (sum(candle_size_trends) + sum(candle_direction_trends) + sum(overlap_trends) + sum(return_trends))/len(chunks_5_ohlc)
            #print(trend)

        if len(self.market_data) >= 60:
            self.direction_calculated = True
            print(candle_size_trends)
            print(candle_direction_trends)
            print(overlap_trends)
            print(return_trends)

            print('trend of ',self.symbol, ' is')
            print(round(trend,2))
    def signal(self):
        if not self.direction_calculated:
            self.calculate_direction()
        #print('signal')
        """
        if self.market_profile is not None and self.running:
            #print('processing signal in strategy')
            yesterday = self.yesterday
            ib_low = self.market_profile['initial_balance_acc'][0]
            ib_high = self.market_profile['initial_balance_acc'][1]
            t_high = self.market_profile['high']
            t_low = self.market_profile['low']
            y_val = yesterday[7]
            y_vah = yesterday[8]

            if not self.opportunity_exists:
                for criteria in self.entry_triggers:
                    trigger_entry = True
                    for condition in criteria:
                        trigger_entry = trigger_entry and eval(condition)
                    if trigger_entry:
                        if t_low >= ib_low*0.999:
                            self.opportunity_exists = True
                        else:
                            self.deactivated()

            if not len(self.existing_orders) and self.remaining_orders and self.opportunity_exists and self.ltp < ib_low:
                if self.first_appear_time is None:
                    self.first_appear_time = self.last_time
                else:
                    time_lapsed =  self.last_time - self.first_appear_time
                    if time_lapsed >= 5*60:
                        self.trigger_entry()
            elif len(self.existing_orders):
                for criteria in self.exit_triggers:
                    #print(criteria)
                    trigger_exit = True
                    for condition in criteria:
                        trigger_exit = trigger_exit and eval(condition)
                    if trigger_exit:
                        self.trigger_exit()
                        self.trade_close_time = self.last_time
                        self.trade_close_price = self.ltp
                        break
        """
    def trigger_entry(self):
        self.remaining_orders -= 1
        self.trigger_id += 1
        self.trade_open_time = self.last_time
        self.trade_open_price = self.ltp
        self.pm.strategy_signal(self.symbol, self.id,self.last_time, self.trigger_id, 'SHORT')
        self.existing_orders.append(self.trigger_id)

    def trigger_exit(self):
        self.trade_close_time = self.last_time
        self.trade_close_price = self.ltp
        self.pm.strategy_signal(self.symbol, self.id,self.last_time, self.trigger_id, 'LONG')
        self.existing_orders.remove(self.trigger_id)


