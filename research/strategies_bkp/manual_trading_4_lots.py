import numpy as np
from research.strategies import BaseStrategy
from datetime import datetime

class ManualTrading4Lots(BaseStrategy):
    def __init__(self, sym, trade_day, side):
        BaseStrategy.__init__(self, sym, trade_day)
        print('Manual strategy created')
        self.id = 1
        self.side = side
        self.entry_triggers = []
        self.exit_triggers = {'C1': ['self.pivot_target(1)'], 'C2':['self.pivot_target(2)'], 'C3':['self.th_time_lapsed_since_trade_begin(15)'], 'C4':['self.th_time_lapsed_since_trade_begin(60)', 'self.pivot_target(3)']}
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005
        self.opportunity_exists = False
        self.first_appear_time = None
        self.positions = 0
        self.trade_taken = False
        self.size = 4
        if side in ['BUY', 'LONG']:
            self.reverse_side = 'SELL'
        else:
            self.reverse_side = 'BUY'


    def price_input(self, input_price):
        #print(input_price)
        self.market_data.append(input_price)
        self.last_time = input_price['timestamp']
        self.ltp = input_price['close']
        if not self.start_time:
            self.start_time = input_price['timestamp']
            #print(self.start_time)
        #print(self.last_time)
        self.entry_signal()
        self.exit_signal()

    def entry_signal(self):
        if not self.trade_taken:
            print('Manual strategy entry')
            self.pm.strategy_signal( self.id,'EN', self.symbol,'MARKET', self.side, self.ltp, self.size, datetime.fromtimestamp(self.last_time).strftime("%Y-%m-%d %H:%M:%S"))
            self.trade_taken = True
            self.positions += self.size
            self.trade_open_price = self.ltp
            self.trade_open_time = self.last_time
            self.trade_taken = True

    def exit_signal(self):
        if self.positions > 0:
            for key, criteria in self.exit_triggers.items():
                #print(criteria)
                trigger_exit = False
                for condition in criteria:
                    trigger_exit = trigger_exit or eval(condition)
                if trigger_exit:
                    print('Manual strategy exit triggered++++', key)
                    self.positions -= 1
                    self.pm.strategy_signal(self.id, key, self.symbol, 'MARKET', self.reverse_side, self.ltp, 1, datetime.fromtimestamp(self.last_time).strftime("%Y-%m-%d %H:%M:%S"))
                    del self.exit_triggers[key]
                    break
        if self.positions > 0:
            if self.stoploss(self.sl):
                self.pm.strategy_signal(self.id, 'SL', self.symbol, 'MARKET', self.reverse_side, self.ltp, self.positions, datetime.fromtimestamp(self.last_time).strftime("%Y-%m-%d %H:%M:%S"))
                self.positions -=self.positions #close all pos




