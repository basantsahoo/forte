import numpy as np
from db.db_engine import get_db_engine


class BaseStrategy:
    def __init__(self, sym, trade_day):
        self.symbol = sym
        self.trade_day = trade_day
        self.id = 1
        self.pm = None
        self.market_data = []
        self.market_profile = None
        self.running = True
        self.yesterday = None
        self.ltp = 0
        self.last_time = 0
        self.start_time = 0
        self.trade_open_time = 0
        self.trade_close_time = 0
        self.trade_open_price = 0
        self.trade_close_price = 0
        self.entry_triggers = []
        self.exit_triggers = []
        self.existing_orders = []
        self.trigger_id = 0
        self.remaining_orders = 0
        self.target = 0.01
        self.sl = 0.005
        self.target_ach = False
        self.sl_triggered = False
        self.time_triggered = False
        self.force_exit = False
        self.engine = get_db_engine()
        self.initial_setup()


    def initial_setup(self):
        stmt = """select date,open,high,low,close,volume,poc_price,va_l_p,va_h_p,ib_l,ib_h, h_a_l, ht, lt,poc_price,ext_low,ext_high,le_f,he_f
                        from daily_profile
                        where symbol = '{0}' and date = 
                        (select  max(date) as yesterday from daily_profile where symbol = '{0}'  and date<  date('{1}'))"""
        print(stmt.format(self.symbol, self.trade_day))
        conn = self.engine.connect()
        rs = conn.execute(stmt.format(self.symbol, self.trade_day))
        self.yesterday = list(rs)[0]
        #print(self.yesterday)
        conn.close()

    def price_input(self, input_price):
        #print(input_price)
        self.market_data.append(input_price)
        self.last_time = input_price['timestamp']
        self.ltp = input_price['close']
        if not self.start_time:
            self.start_time = input_price['timestamp']
            #print(self.start_time)
        #print(self.last_time)
        self.signal()

    def profile_input(self, market_profile):
        #print(market_profile)
        self.market_profile = market_profile
        self.signal()

    def trigger_force_exit_all(self):
        self.force_exit = True
        self.trigger_exit()

    def deactivated(self):
        print('deactivate')
        self.running = False
        self.pm.remove_strategy(self)

    def th_time_lapsed_since_mkt_open(self, min):
        time_lapsed = self.last_time - self.start_time
        #print(time_lapsed)
        return time_lapsed > min * 60

    def th_time_lapsed_since_trade_begin(self, min):
        time_lapsed = self.last_time - self.trade_open_time
        self.time_triggered = time_lapsed > min * 60
        return self.time_triggered

    def candle_type_5min(self, type):
        return True

    def target_achieved(self, th):
        self.target_ach = (1 - self.ltp/self.trade_open_price) >= th
        return self.target_ach

    def stoploss(self, th):
        self.sl_triggered = (1 - self.ltp/self.trade_open_price) <= -1 *abs(th)
        return self.sl_triggered

    def pivot_target(self, th):
        #print('pivot_target')
        pivot_pts = list(self.pm.pivots.values())
        #print(pivot_pts)

        if self.side in ['BUY', 'LONG']:
            #print('in buy')
            pivot_targets = [x for x in pivot_pts if x > self.trade_open_price]
            pivot_targets.sort()
            #print(pivot_targets)
            return self.ltp > pivot_targets[th] * (1-0.001)
        else:
            #print('in sell')
            pivot_targets = [x for x in pivot_pts if x < self.trade_open_price]
            pivot_targets.sort()
            #print(pivot_targets)
            return self.ltp < pivot_targets[th] * (1 + 0.001)



