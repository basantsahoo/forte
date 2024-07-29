from trade_master.leg import Leg
from helper.utils import get_broker_order_type, get_exit_order_type
from trade_master.trade_config import exit_minutes_before_close_1, exit_minutes_before_close_2


class LegGroup:
    def __init__(self, trade, lg_id, lg_index, leg_group_info):
        #print('lg_index =====', lg_index)
        #print('leg_group_info =====', leg_group_info)
        self.lg_class = leg_group_info['lg_class']
        self.lg_index = lg_index
        self.lg_id = lg_id
        self.prior_lg_id = leg_group_info.get('prior_lg_id', None)
        self.primary_leg = leg_group_info.get('prior_lg_id', True)
        self.active = leg_group_info.get('active', True)
        self.asset = leg_group_info['asset']
        self.trade = trade
        #self.leg_group_info = leg_group_info
        self.target = abs(self.trade.leg_group_exits['targets'].get(self.lg_class, float('inf')))
        self.stop_loss = -1 * abs(self.trade.leg_group_exits['stop_losses'].get(self.lg_class, float('inf')))
        self.spot_high_stop_loss = abs(self.trade.leg_group_exits['spot_high_stop_losses'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_high_stop_losses'] else float('inf')
        self.spot_low_stop_loss = -1 * abs(self.trade.leg_group_exits['spot_low_stop_losses'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_low_stop_losses'] else float('-inf')
        self.spot_high_target = abs(self.trade.leg_group_exits['spot_high_targets'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_high_targets'] else float('inf')
        self.spot_low_target = -1 * abs(self.trade.leg_group_exits['spot_low_targets'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_low_targets'] else float('-inf')
        self.spot_slide_up = abs(self.trade.leg_group_exits['spot_slide_ups'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_slide_ups'] else float('inf')
        self.spot_slide_down = -1 * abs(self.trade.leg_group_exits['spot_slide_downs'].get(self.lg_class, float('inf'))) if self.trade.leg_group_exits['spot_slide_downs'] else float('-inf')
        self.carry_forward_days = self.trade.carry_forward_days
        self.legs = {}
        self.trigger_time = leg_group_info.get('trigger_time', None)
        self.exit_time = leg_group_info.get('exit_time', None)
        self.spot_entry_price = leg_group_info.get('spot_entry_price', None)
        self.spot_benchmark_price = leg_group_info.get('spot_benchmark_price', None)
        self.spot_exit_price = leg_group_info.get('spot_exit_price', None)

        self.force_exit_time = leg_group_info.get('force_exit_time', None)
        self.re_entry_config = leg_group_info.get('re_entry_config', {})
        self.re_entry_count = leg_group_info.get('re_entry_count', 0)
        if self.force_exit_time is None:
            self.force_exit_time = self.trade.trade_set.trade_manager.market_book.get_force_exit_ts(leg_group_info.get('force_exit_ts', None))
            print('self.force_exit_time=======', self.force_exit_time)
        self.delta = leg_group_info.get('delta', 0)  # >0 means we are long <0 means we are sort
        self.market_view = leg_group_info.get('market_view', None)
        self.duration = leg_group_info.get('duration', None)
        self.max_life_timestamp = leg_group_info.get('max_life_timestamp', None)
        #print('LegGroup duration===', self.duration)
        self.calculate_duration()

    def calculate_duration(self):
        if self.duration is None:
            # On carry over day trade close market close 5 min before
            if not self.carry_forward_days:
                self.duration = min(self.trade.durations[self.lg_index], self.trade.trade_set.trade_manager.market_book.get_time_to_close() - exit_minutes_before_close_1)
            else:
                self.duration = self.trade.trade_set.trade_manager.market_book.get_time_to_close() - exit_minutes_before_close_2 + 1440 * self.carry_forward_days



    @classmethod
    def from_config(cls, trade, lg_id, lg_index, leg_group_info):
        obj = cls(trade, lg_id, lg_index, leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_config(obj, leg_id, leg_info)
        if obj.trigger_time is None:
            #obj.trigger_time = obj.legs[list(obj.legs.keys())[0]].trigger_time
            obj.delta = obj.calculate_delta()
            obj.infer_market_view()
        return obj

    @classmethod
    def from_store(cls, trade, leg_group_info):
        obj = cls(trade, leg_group_info['lg_id'], leg_group_info['lg_index'], leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_store(obj, **leg_info)
        return obj

    def to_dict(self):
        dct = {}
        for field in ['lg_index', 'lg_id', 'prior_lg_id', 'primary_leg', 'active', 'lg_class', 'asset', 'trigger_time', 'duration', 'delta', 'exit_time',
                      'spot_entry_price', 'spot_benchmark_price', 'spot_exit_price', 'force_exit_time', 'max_life_timestamp', 're_entry_config', 're_entry_count']:
            dct[field] = getattr(self, field)
        dct['legs'] = {k:v.to_dict() for k,v in self.legs.items()}
        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['lg_id', 'prior_lg_id', 'lg_class']:
            dct[field] = getattr(self, field)
        for field in ['duration', 'delta', 'trigger_time', 'exit_time']:
            dct['lg_' + field] = getattr(self, field)
        return dct


    def infer_market_view(self):
        if self.delta > 0:
            return 'LONG'
        elif self.delta < 0:
            return 'SHORT'



    def trigger_entry(self):
        entry_orders = {}
        entry_orders['lg_id'] = self.lg_id
        entry_orders['legs'] = []
        for leg in self.legs.values():
            entry_orders['legs'].append(leg.to_dict())
        for order in entry_orders['legs']:
            order['lg_id'] = self.lg_id
        entry_orders['legs'] = sorted(entry_orders['legs'], key=lambda d: d['order_type'])
        self.trigger_time = self.legs[list(self.legs.keys())[0]].trigger_time
        self.max_life_timestamp = self.trigger_time + self.duration * 60 if self.force_exit_time is None else min(
            self.trigger_time + self.duration * 60, self.force_exit_time + 60)
        self.spot_entry_price = self.legs[list(self.legs.keys())[0]].spot_entry_price
        self.spot_benchmark_price = self.legs[list(self.legs.keys())[0]].spot_entry_price
        self.trade.entry_orders.append(entry_orders)


    def check_re_entry(self):
        re_entry_ind = self.re_entry_count < self.re_entry_config.get('max_allowed', 0)
        if self.active and re_entry_ind and self.complete() and self.calculate_pnl()[1] > 0:
            print('leg group check_re_entry',self.trade.trd_idx, self.lg_id, self.prior_lg_id, self.complete(), self.active)
            print('self.re_entry_count====', self.re_entry_count)
            print('self.max_allowed====', self.re_entry_config.get('max_allowed', 0))
            print(self.calculate_pnl())
            last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
            pull_back_level = self.spot_entry_price + self.re_entry_config.get('pull_back', 0) if self.re_entry_config.get('pull_back_type', '') == 'step' else self.spot_benchmark_price + self.re_entry_config.get('pull_back', 0)
            #pull_back_level = self.spot_exit_price - self.re_entry_config.get('pull_back', 0)
            if self.delta >= 0:
                if last_spot_candle['close'] <= pull_back_level:
                    print('trigger reentry===', 'self.primary_leg=', self.primary_leg, 're_entry_ind==', re_entry_ind,
                          "complete===", self.complete())
                    self.re_entry_count += 1
                    self.trade.re_enter_leg_group(self.lg_id, self.lg_index)
            if self.delta < 0:
                if last_spot_candle['close'] >= pull_back_level:
                    print('trigger reentry===', 'self.primary_leg=', self.primary_leg,'re_entry_ind==', re_entry_ind, "complete===", self.complete())
                    self.re_entry_count += 1
                    self.trade.re_enter_leg_group(self.lg_id, self.lg_index)


    def trigger_exit(self, exit_type=None):
        exit_orders = {}
        exit_orders['lg_id'] = self.lg_id
        exit_orders['legs'] = []
        for leg in self.legs.values():
            leg.trigger_exit(exit_type)
            exit_orders['legs'].append(leg.to_dict())
        for order in exit_orders['legs']:
            order['lg_id'] = self.lg_id
        exit_orders['legs'] = sorted(exit_orders['legs'], key=lambda d: d['order_type'], reverse=True)
        self.exit_time = self.legs[list(self.legs.keys())[0]].exit_time
        self.spot_exit_price = self.legs[list(self.legs.keys())[0]].spot_exit_price
        self.trade.exit_orders.append(exit_orders)


    def complete(self):
        all_legs_complete = True
        for leg in self.legs.values():
            #print("leg complete===", self.lg_id, leg.leg_id, leg.exit_type)
            all_legs_complete = all_legs_complete and leg.exit_type is not None
        return all_legs_complete

    def to_carry_forward(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        time_ind = last_spot_candle['timestamp'] < self.max_life_timestamp
        re_entry_ind = self.re_entry_count < self.re_entry_config.get('max_allowed', 0)
        return (self.active and time_ind and re_entry_ind) or not self.complete()



    def calculate_pnl(self):
        lg_pnl = []
        lg_capital = []
        for leg_id, leg in self.legs.items():
            ltp = leg.instrument.get_last_tick()['close'] if leg.exit_price is None else leg.exit_price
            side = get_broker_order_type(leg.order_type)
            exit_order_type = get_exit_order_type(side)
            un_realized_pnl = exit_order_type * abs(leg.quantity) * (leg.entry_price - ltp)
            capital = abs(leg.quantity) * leg.entry_price
            lg_pnl.append(un_realized_pnl)
            lg_capital.append(capital)
        pnl_ratio = sum(lg_pnl)/sum(lg_capital)
        return sum(lg_capital), sum(lg_pnl), pnl_ratio

    def calculate_delta(self):
        lg_delta = []
        for leg_id, leg in self.legs.items():
            delta = leg.instrument.get_delta()
            side = get_broker_order_type(leg.order_type)
            total_delta = side * abs(leg.quantity) * delta
            lg_delta.append(total_delta)
        return sum(lg_delta)

    def close_on_instr_sl_tm(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        #max_run_time = self.trigger_time + self.duration * 60 if self.force_exit_time is None else min(self.trigger_time + self.duration * 60, self.force_exit_time + 60)
        #print("leggroup max_run_time =", max_run_time)
        capital, pnl, pnl_pct = self.calculate_pnl()
        if self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit(exit_type='TSFE')
        elif last_spot_candle['timestamp'] >= self.max_life_timestamp:
            self.trigger_exit(exit_type='TC')
        elif self.stop_loss and pnl_pct < self.stop_loss:
            self.trigger_exit(exit_type='IS')

    def close_on_instr_tg(self):
        capital, pnl, pnl_pct = self.calculate_pnl()
        print('leg group pnl =====', self.lg_id, "pnl====", capital, pnl, pnl_pct)
        if self.target and pnl_pct > self.target:
            self.trigger_exit(exit_type='IT')

    def close_on_spot_tg_sl(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        if self.delta > 0:
            if self.spot_high_target and last_spot_candle['close'] >= self.spot_benchmark_price * (1 + self.spot_high_target):
                self.trigger_exit(exit_type='ST')
            elif self.spot_low_stop_loss and last_spot_candle['close'] < self.spot_benchmark_price * (1 + self.spot_low_stop_loss):
                self.trigger_exit(exit_type='SS')
        elif self.delta < 0:
            if self.spot_low_target and last_spot_candle['close'] <= self.spot_benchmark_price * (1 + self.spot_low_target):
                self.trigger_exit(exit_type='ST')
                # print(last_candle, trigger_details['target'])
            elif self.spot_high_stop_loss and last_spot_candle['close'] > self.spot_benchmark_price * (1 + self.spot_high_stop_loss):
                self.trigger_exit(exit_type='SS')

    def check_slide_status(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        if last_spot_candle['close'] >= self.spot_entry_price + self.spot_slide_up:
            #print('here 1 ++++++++++++++++++++++++++++')
            self.trigger_exit(exit_type='SLDUP')
            self.trade.slide_leg_group(self.lg_id, self.lg_index)
        elif last_spot_candle['close'] <= self.spot_entry_price + self.spot_slide_down:
            #print('spot slide to lower end')
            self.trigger_exit(exit_type='SLDDOWN')
            #print('trigger exit complete +++++++++')
            self.trade.slide_leg_group(self.lg_id, self.lg_index)

