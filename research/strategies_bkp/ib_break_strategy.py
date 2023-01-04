import numpy as np
from market.strategies.base_strategy import BaseStrategy


class IBBreakDownStrategy(BaseStrategy):
    def __init__(self, sym, trade_day):
        BaseStrategy.__init__(self, sym, trade_day)
        self.entry_triggers = [['self.th_time_lapsed_since_mkt_open(240)']]
        self.exit_triggers = [['self.th_time_lapsed_since_trade_begin(15)'], ['self.stoploss(0.003)'], ['self.target_achieved(0.01)']]
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005
        self.opportunity_exists = False
        self.first_appear_time = None

    def signal(self):
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


