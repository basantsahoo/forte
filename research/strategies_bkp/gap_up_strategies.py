import numpy as np
from market.strategies.base_strategy import BaseStrategy


class GapUpSell(BaseStrategy):
    def __init__(self, sym, trade_day):
        BaseStrategy.__init__(self, sym, trade_day)
        self.entry_triggers = [['self.th_time_lapsed_since_mkt_open(5)', 'self.candle_type_5min("test")']]
        self.exit_triggers = [['self.th_time_lapsed_since_trade_begin(15)'], ['self.target_achieved(0.01)'], ['self.stoploss(0.005)']]
        self.remaining_orders = 1
        self.target = 0.01
        self.sl = 0.005

    def signal(self):
        if self.market_profile is not None and self.running:
            #print('processing signal in strategy')
            t_open = self.market_profile['open']
            t_high = self.market_profile['high']
            t_low = self.market_profile['low']
            yesterday = self.yesterday
            y_open = yesterday[1]
            y_high = yesterday[2]
            y_low = yesterday[3]
            y_close = yesterday[4]
            y_val = yesterday[7]
            y_vah = yesterday[8]
            y_ibl = yesterday[9]
            y_ibh = yesterday[10]
            y_hal = yesterday[11]
            y_ht = yesterday[12]
            y_lt = yesterday[13]

            y_poc_price = yesterday[14]
            y_ext_low = yesterday[15]
            y_ext_high = yesterday[16]
            y_le_f = yesterday[17]
            y_he_f = yesterday[18]

            below_poc = self.market_profile['below_poc']
            above_poc = self.market_profile['above_poc']
            t_ibl = self.market_profile['initial_balance'][0]
            t_ibh = self.market_profile['initial_balance'][1]
            ext_low = self.market_profile['extremes']['ext_low']
            ext_high = self.market_profile['extremes']['ext_high']

            le_f = self.market_profile['extremes'].get('le_f', None)
            he_f = self.market_profile['extremes'].get('he_f', None)
            sp_f = self.market_profile['extremes'].get('sp_f', None)

            tmp_y_va = list(range(int(np.floor(y_val)), int(np.ceil(y_vah)) + 1))
            tmp_t_ib = list(range(int(np.floor(t_ibl)), int(np.ceil(t_ibh)) + 1))
            over_lap = list(set(tmp_y_va) & set(tmp_t_ib))
            over_lap_pct = len(over_lap)/len(tmp_y_va)

            t_open_gap = ((t_open - y_high) if t_open > y_high else (t_open - y_low) if t_open < y_low else 0) / y_close
            #print(t_open_gap)
            #print('processing signal in strategy 1')
            if t_open_gap <= 0:
                self.deactivated()
            elif not len(self.existing_orders) and self.remaining_orders:
                for criteria in self.entry_triggers:
                    #print(criteria)
                    trigger_entry = True
                    for condition in criteria:
                        trigger_entry = trigger_entry and eval(condition)
                    if trigger_entry:
                        self.trigger_entry()
                        break

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


