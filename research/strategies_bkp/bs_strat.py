import helper.utils as helper_utils


class BaseStrategy:
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None):
        self.id = 0
        self.insight_book = insight_book
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.activated = True
        self.price_pattern = None
        self.trade_open_time = 0
        self.trade_close_time = 0
        self.trade_open_price = 0
        self.trade_close_price = 0
        self.entry_triggers = []
        self.exit_triggers = []
        self.existing_orders = []
        self.quantity = 1
        self.enabled_instruments = ['FUT', 'OPT']
        self.max_capital = 0.1
        self.trigger_id = 0
        self.executed_orders = 0
        self.max_orders = 1
        self.target = 0.01
        self.sl = 0.005
        self.target_ach = False
        self.sl_triggered = False
        self.time_triggered = False
        self.force_exit = False
        self.record_metric = False
        self.is_aggregator = False
        self.params_repo = {}
        self.strategy_params = {}

    def trigger_force_exit_all(self):
        self.force_exit = True
        self.trigger_exit()

    def trigger_exit(self):
        pass

    """Deactivate when not required to run in a particular day"""
    def deactivate(self):
        self.activated = False
        self.insight_book.remove_strategy(self)

    def th_time_lapsed_since_mkt_open(self, min):
        time_lapsed = self.last_time - self.insight_book.ib_periods[0]
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
        pivot_pts = list(self.insight_book.pivots.values())
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

    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.insight_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def check_support(self, candle):
        support_ind = 0
        for support in self.insight_book.supports_to_watch:
            support_range = [support-5, support+5]
            candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
            ol = helper_utils.get_overlap(support_range, candle_range)
            if ol > 0:
                support_ind = 2 if support % 100 == 0 else 1
                break
        return support_ind

    def check_resistance(self, candle):
        resistance_ind = 0
        for resistance in self.insight_book.resistances_to_watch:
            resistance_range = [resistance-5, resistance+5]
            candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
            ol = helper_utils.get_overlap(resistance_range, candle_range)
            if ol > 0:
                resistance_ind = 2 if resistance % 100 == 0 else 1
                break
        return resistance_ind

    def check_level(self, candle, level):
        ind = 0
        level_rng = [level - 10, level + 10]
        candle_range = [min(candle['open'], candle['close']), max(candle['open'], candle['close'])]
        ol = helper_utils.get_overlap(level_rng, candle_range)
        if ol > 0:
            ind = 1
        return ind



    def get_market_params(self):
        mkt_parms = self.insight_book.market_insights
        mkt_parms['open_type'] = self.insight_book.open_type
        mkt_parms['tpo'] = self.insight_book.curr_tpo
        mkt_parms['first_hour_trend'] = round(self.insight_book.intraday_trend.first_hour_trend,2)
        mkt_parms['whole_day_trend'] = round(self.insight_book.intraday_trend.whole_day_trend,2)
        mkt_parms['five_min_trend'] = round(self.insight_book.intraday_trend.five_min_trend,2)
        mkt_parms['fifteen_min_trend'] = round(self.insight_book.intraday_trend.fifteen_min_trend,2)
        mkt_parms['five_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.five_min_ex_first_hr_trend,2)
        mkt_parms['fifteen_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.fifteen_min_ex_first_hr_trend,2)
        mkt_parms['hurst_exp_15'] = round(self.insight_book.intraday_trend.hurst_exp_15,2)
        mkt_parms['hurst_exp_5'] = round(self.insight_book.intraday_trend.hurst_exp_5,2)
        mkt_parms['ret_trend'] = round(self.insight_book.intraday_trend.ret_trend,2)
        mkt_parms['candles_in_range'] = round(self.insight_book.intraday_trend.candles_in_range,2)

        last_candle = self.insight_book.last_tick
        next_level = round(last_candle['close'] / 100,0) * 100
        mkt_parms['dist_frm_level'] = last_candle['close']-next_level
        mkt_parms['resistance_ind'] = self.check_resistance(last_candle)
        mkt_parms['support_ind'] = self.check_support(last_candle)
        yday_profile = {k: v for k, v in self.insight_book.yday_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p','poc_price')}
        #print(self.insight_book.weekly_pivots)
        for (lvl, price) in yday_profile.items():
            mkt_parms['y_' + lvl] = self.check_level(last_candle, price)
        weekly_profile = {k: v for k, v in self.insight_book.weekly_pivots.items() if k not in ('open', 'close')}
        for (lvl, price) in weekly_profile.items():
            mkt_parms['w_' + lvl] = self.check_level(last_candle, price)
        if self.strategy_params:
            mkt_parms = {**mkt_parms, **self.strategy_params}
            #self.strategy_params = {} #we may need to reset it please check?
        return mkt_parms

    def trigger_entry(self, order_type, qty=1, targets=[], stop_loss=None):
        #print(self.insight_book.last_tick['timestamp'], self.insight_book.get_sma(self.short_sma), self.insight_book.get_sma(self.long_sma))
        req_id = self.trigger_id + 1
        if self.record_metric:
            self.params_repo[req_id] = self.get_market_params()
            #print( self.params_repo[req_id])
        resposne = self.insight_book.pm.strategy_entry_signal(self.insight_book.ticker, self.id, self.trigger_id + 1, order_type, qty)
        if resposne:
            self.executed_orders += 1
            self.trigger_id = req_id
            self.trade_open_time = self.insight_book.last_tick['timestamp']
            self.trade_open_price = self.insight_book.last_tick['close']
            self.existing_orders.append([self.trigger_id, self.insight_book.last_tick['timestamp'], self.insight_book.last_tick['close'], order_type, qty, targets, stop_loss])

    def trigger_exit(self, trigger_id=None):
        #print(self.insight_book.last_tick['timestamp'], self.insight_book.get_sma(self.short_sma), self.insight_book.get_sma(self.long_sma))
        trigger_id = self.trigger_id if trigger_id is None else trigger_id
        #print('trigger_exit', trigger_id)
        response = self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, trigger_id)
        if response:
            self.trade_close_time = self.insight_book.last_tick['timestamp']
            self.trade_close_price = self.insight_book.last_tick['close']
            for trig in self.existing_orders:
                if trig[0] == trigger_id:
                    self.existing_orders.remove(trig)

    def get_lowest_candle(self):
        lowest_candle = None
        for (ts,candle) in reversed(self.insight_book.market_data.items()):
            #print(candle)
            if candle['low'] == self.insight_book.range['low']:
                lowest_candle = candle
                break
        return lowest_candle

    def trigger_exit_at_low(self, trigger_id=None):
        trigger_id = self.trigger_id if trigger_id is None else trigger_id
        lowest_candle = self.get_lowest_candle()
        #print(self.insight_book.last_tick['timestamp'], self.insight_book.get_sma(self.short_sma), self.insight_book.get_sma(self.long_sma))
        response = self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, self.trigger_id, lowest_candle)
        if response:
            self.trade_close_time = lowest_candle['timestamp']
            self.trade_close_price = lowest_candle['close']
            for trig in self.existing_orders:
                if trig[0] == trigger_id:
                    self.existing_orders.remove(trig)
