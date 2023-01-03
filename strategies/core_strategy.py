import numpy as np
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils

#Check 13 May last pattern again why it was not triggered
class BaseStrategy:
    def __init__(self, insight_book=None, order_type="BUY", min_tpo=None, max_tpo=None):
        self.id = None
        self.insight_book = insight_book
        self.order_type = order_type
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.activated = True
        self.price_pattern = None
        self.max_orders = 1
        self.force_exit = False
        self.record_metric = False
        self.is_aggregator = False
        self.params_repo = {}
        self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.tradable_signals ={}
        self.minimum_quantity = 1
        self.max_signals = 1

    def set_up(self):
        pass

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

    def th_time_lapsed_since_trade_begin(self, min, trade_open_time):
        time_lapsed = self.last_time - trade_open_time
        return time_lapsed > min * 60

    def candle_type_5min(self, type):
        return True

    def target_achieved(self, trade_open_price, th):
        return (1 - self.ltp/trade_open_price) >= th

    def stoploss(self, trade_open_price, th):
        return (1 - self.ltp/self.trade_open_price) <= -1 *abs(th)

    def pivot_target(self, trade_open_price, th):
        #print('pivot_target')
        pivot_pts = list(self.insight_book.pivots.values())
        #print(pivot_pts)

        if self.side in ['BUY', 'LONG']:
            #print('in buy')
            pivot_targets = [x for x in pivot_pts if x > trade_open_price]
            pivot_targets.sort()
            #print(pivot_targets)
            return self.ltp > pivot_targets[th] * (1-0.001)
        else:
            #print('in sell')
            pivot_targets = [x for x in pivot_pts if x < trade_open_price]
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
        """
        mkt_parms['first_hour_trend'] = round(self.insight_book.intraday_trend.first_hour_trend,2)
        mkt_parms['whole_day_trend'] = round(self.insight_book.intraday_trend.whole_day_trend,2)
        mkt_parms['five_min_trend'] = round(self.insight_book.intraday_trend.five_min_trend,2)
        mkt_parms['fifteen_min_trend'] = round(self.insight_book.intraday_trend.fifteen_min_trend,2)
        mkt_parms['five_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.five_min_ex_first_hr_trend,2)
        mkt_parms['fifteen_min_ex_first_hr_trend'] = round(self.insight_book.intraday_trend.fifteen_min_ex_first_hr_trend,2)
        mkt_parms['hurst_exp_15'] = round(self.insight_book.intraday_trend.hurst_exp_15,2)
        mkt_parms['hurst_exp_5'] = round(self.insight_book.intraday_trend.hurst_exp_5,2)
        mkt_parms['ret_trend'] = round(self.insight_book.intraday_trend.ret_trend,2)
        """
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
        t_2_profile = {k: v for k, v in self.insight_book.day_before_profile.items() if k in ('high', 'low', 'va_h_p', 'va_l_p','poc_price')}
        #print(self.insight_book.weekly_pivots)
        for (lvl, price) in t_2_profile.items():
            mkt_parms['t_2_' + lvl] = self.check_level(last_candle, price)

        weekly_profile = {k: v for k, v in self.insight_book.weekly_pivots.items() if k not in ('open', 'close')}
        for (lvl, price) in weekly_profile.items():
            mkt_parms['w_' + lvl] = self.check_level(last_candle, price)
        if self.insight_book.activity_log.activity:
            mkt_parms = {**mkt_parms, **self.insight_book.activity_log.activity}
        if self.strategy_params:
            mkt_parms = {**mkt_parms, **self.strategy_params}
            #self.strategy_params = {} #we may need to reset it please check?
        return mkt_parms


    def get_lowest_candle(self):
        lowest_candle = None
        for (ts,candle) in reversed(self.insight_book.market_data.items()):
            #print(candle)
            if candle['low'] == self.insight_book.range['low']:
                lowest_candle = candle
                break
        return lowest_candle


    def trigger_entry(self, order_type, sig_key, triggers):
        #print(triggers)
        for trigger in triggers:
            if self.record_metric:
                self.params_repo[(sig_key, trigger['seq'])] = self.get_market_params()  # We are interested in signal features, trade features being stored separately
        signal_info = {'symbol': self.insight_book.ticker, 'strategy_id': self.id, 'signal_id': sig_key, 'order_type': order_type, 'triggers': [{'seq': trigger['seq'], 'qty': trigger['quantity']} for trigger in triggers]}
        self.confirm_trigger(sig_key, triggers)
        self.insight_book.pm.strategy_entry_signal(signal_info)

    def trigger_exit(self, signal_id, trigger_id, exit_type=None):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.tradable_signals[signal_id]['triggers'][trigger_id]['quantity']
        last_candle = self.insight_book.last_tick
        signal_info = {'symbol': self.insight_book.ticker, 'strategy_id': self.id, 'signal_id': signal_id,
                       'trigger_id': trigger_id,
                       'qty': quantity}

        self.tradable_signals[signal_id]['triggers'][trigger_id]['closed'] = True
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_type'] = exit_type
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_price'] = last_candle['close']
        self.insight_book.pm.strategy_exit_signal(signal_info)

    def trigger_exit_at_low(self, signal_id, trigger_id):
        lowest_candle = self.get_lowest_candle()
        self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, signal_id, trigger_id, lowest_candle)

    def add_new_signal(self):
        #print('add_new_signal core++++')
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = {}
        self.tradable_signals[sig_key]['triggers'] = {}
        self.tradable_signals[sig_key]['targets'] = []
        self.tradable_signals[sig_key]['stop_losses'] = []
        self.tradable_signals[sig_key]['time_based_exists'] = []
        self.tradable_signals[sig_key]['max_triggers'] = 1
        self.tradable_signals[sig_key]['trade_completed'] = False
        return sig_key


    def add_tradable_signal(self):
        sig_key = self.add_new_signal()
        return sig_key

    def initiate_signal_trades(self, sig_key):
        pass

    def confirm_trigger(self, sig_key, triggers):
        curr_signal = self.tradable_signals[sig_key]
        for trigger in triggers:
            curr_signal['targets'].append(trigger['target'])
            curr_signal['stop_losses'].append(trigger['stop_loss'])
            curr_signal['time_based_exists'].append(trigger['duration'])
            curr_signal['triggers'][trigger['seq']] = trigger

    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_dt_trades(curr_signal['pattern']['price_list'], trd_idx) for trd_idx in range(next_trigger, next_trigger+1+1)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type,sig_key,triggers)


    def evaluate_signal(self, signal):
        return False

    def process_signal(self, signal):
        print('process_signal in core++++++++++++++++++++++++++', self.id, "tpo====", self.insight_book.curr_tpo, "minutes past===", len(self.insight_book.market_data.items()))
        signal_passed = self.evaluate_signal(signal) #len(self.tradable_signals.keys()) < self.max_signals+5  #
        if signal_passed:
            sig_key = self.add_tradable_signal(signal)
            self.initiate_signal_trades(sig_key)

    def process_incomplete_signals(self):
        pass

    def evaluate(self):
        self.process_incomplete_signals()
        self.monitor_existing_positions()

    def monitor_sell_positions(self):
        last_candle = self.insight_book.last_tick
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] < trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] >= trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_buy_positions(self):
        last_candle = self.insight_book.last_tick
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] >= trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] < trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_existing_positions(self):
        if self.order_type == 'BUY':
            self.monitor_buy_positions()
        elif self.order_type == 'SELL':
            self.monitor_sell_positions()

    def locate_point(self, df, threshold):
        above = len(np.array(df.index[df.Close > threshold]))
        below = len(np.array(df.index[df.Close <= threshold]))
        pct = (1 - above / (above + below)) * 100
        return pct
        # array of targets, stoploss and time - when one is triggered target and stoploss is removed and time is removed from last

    def get_trades(self, **kwargs):
        pass

    def add_tradable_signal(self, **kwargs):
        pass


