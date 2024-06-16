from trade_master.leg import Leg
from helper.utils import get_broker_order_type, get_exit_order_type

class LegGroup:
    def __init__(self, trade, lg_id, lg_index, leg_group_info):
        #print('lg_index =====', lg_index)
        #print('leg_group_info =====', leg_group_info)
        self.lg_class = leg_group_info['lg_class']
        self.lg_index = lg_index
        self.lg_id = lg_id
        self.prior_lg_id = None
        self.asset = leg_group_info['asset']
        self.trade = trade
        self.completed = False
        #self.leg_group_info = leg_group_info
        self.target = abs(self.trade.leg_group_exits['targets'][self.lg_class])
        self.stop_loss = -1 * abs(self.trade.leg_group_exits['stop_losses'][self.lg_class])
        self.spot_high_stop_loss = abs(self.trade.leg_group_exits['spot_high_stop_losses'][self.lg_class]) if self.trade.leg_group_exits['spot_high_stop_losses'] else float('inf')
        self.spot_low_stop_loss = -1 * abs(self.trade.leg_group_exits['spot_low_stop_losses'][self.lg_class]) if self.trade.leg_group_exits['spot_low_stop_losses'] else float('-inf')
        self.spot_high_target = abs(self.trade.leg_group_exits['spot_high_targets'][self.lg_class]) if self.trade.leg_group_exits['spot_high_targets'] else float('inf')
        self.spot_low_target = -1 * abs(self.trade.leg_group_exits['spot_low_targets'][self.lg_class]) if self.trade.leg_group_exits['spot_low_targets'] else float('-inf')
        self.spot_slide_up = abs(self.trade.leg_group_exits['spot_slide_ups'][self.lg_class]) if self.trade.leg_group_exits['spot_slide_ups'] else float('inf')
        self.spot_slide_down = -1 * abs(self.trade.leg_group_exits['spot_slide_downs'][self.lg_class]) if self.trade.leg_group_exits['spot_slide_downs'] else float('-inf')
        self.carry_forward_days = self.trade.carry_forward_days
        self.legs = {}
        self.trigger_time = leg_group_info.get('trigger_time', None)
        self.exit_time = leg_group_info.get('exit_time', None)
        self.spot_entry_price = leg_group_info.get('spot_entry_price', None)
        self.spot_exit_price = leg_group_info.get('spot_exit_price', None)

        self.force_exit_time = leg_group_info.get('force_exit_time', None)
        if self.force_exit_time is None:
            self.force_exit_time = self.trade.trade_set.trade_manager.market_book.get_force_exit_ts(leg_group_info.get('force_exit_ts', None))
        self.delta = leg_group_info.get('delta', 0)  # >0 means we are long <0 means we are sort
        self.market_view = leg_group_info.get('market_view', None)
        self.duration = leg_group_info.get('duration', None)
        print('LegGroup duration===', self.duration)
        if self.duration is None:
            self.duration = min(self.trade.durations[lg_index], self.trade.trade_set.trade_manager.market_book.get_time_to_close() - 2) if not self.carry_forward_days else self.trade.trade_set.trade_manager.market_book.get_time_to_close() - 13 + 1440 * self.carry_forward_days


        print('self.trade.durations[lg_index]===', self.trade.durations[lg_index])
        print('self.carry_forward_days===', self.carry_forward_days)
        print('self.trade.trade_set.trade_manager.market_book.get_time_to_close() - 13 + 1440 * self.carry_forward_days===', self.trade.trade_set.trade_manager.market_book.get_time_to_close() - 13 + 1440 * self.carry_forward_days)

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
        self.spot_entry_price = self.legs[list(self.legs.keys())[0]].spot_entry_price
        self.trade.entry_orders.append(entry_orders)

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
            all_legs_complete = all_legs_complete and leg.exit_type is not None
        return all_legs_complete

    def to_dict(self):
        dct = {}
        for field in ['lg_index', 'lg_id', 'prior_lg_id', 'lg_class', 'asset', 'trigger_time', 'duration', 'delta', 'exit_time', 'spot_entry_price', 'spot_exit_price', 'force_exit_time']:
            dct[field] = getattr(self, field)
        dct['legs'] = {k:v.to_dict() for k,v in self.legs.items()}
        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['lg_id', 'prior_lg_id', 'lg_class', 'duration', 'delta']:
            dct[field] = getattr(self, field)
        for field in ['exit_time']:
            dct['lg_' + field] = getattr(self, field)
        return dct

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

    def close_on_instr_tg_sl_tm(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        max_run_time = self.trigger_time + self.duration * 60 if self.force_exit_time is None else min(self.trigger_time + self.duration * 60, self.force_exit_time + 60)
        print("leggroup max_run_time =", max_run_time)
        capital, pnl, pnl_pct = self.calculate_pnl()
        if last_spot_candle['timestamp'] >= max_run_time:
            self.trigger_exit(exit_type='TC')
        elif self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit(exit_type='TSFE')
        elif self.target and pnl_pct > self.target:
            self.trigger_exit(exit_type='IT')
        elif self.stop_loss and pnl_pct < self.stop_loss:
            self.trigger_exit(exit_type='IS')

    def close_on_spot_tg_sl(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        if self.delta > 0:
            if self.spot_high_target and last_spot_candle['close'] >= self.spot_entry_price * (1 + self.spot_high_target):
                self.trigger_exit(exit_type='ST')
            elif self.spot_low_stop_loss and last_spot_candle['close'] < self.spot_entry_price * (1 + self.spot_low_stop_loss):
                self.trigger_exit(exit_type='SS')
        elif self.delta < 0:
            """
            print('in here +++++++++++++++')
            print('last_spot_candle[close] +++++++++++++++', last_spot_candle['close'])
            print('spot_low_target[close] +++++++++++++++', self.spot_entry_price * (1 + self.spot_low_target))
            print('spot_low_target', self.spot_low_target)
            """
            if self.spot_low_target and last_spot_candle['close'] <= self.spot_entry_price * (1 + self.spot_low_target):
                self.trigger_exit(exit_type='ST')
                # print(last_candle, trigger_details['target'])
            elif self.spot_high_stop_loss and last_spot_candle['close'] > self.spot_entry_price * (1 + self.spot_high_stop_loss):
                self.trigger_exit(exit_type='SS')

    def check_slide_status(self):
        print('check_slide_status++++++++++++++++++++++++++++')
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        if last_spot_candle['close'] >= self.spot_entry_price + self.spot_slide_up:
            print('here 1 ++++++++++++++++++++++++++++')
            self.trigger_exit(exit_type='SLDUP')
            self.trade.slide_leg_group(self.lg_id, self.lg_index)
        elif last_spot_candle['close'] <= self.spot_entry_price + self.spot_slide_down:
            print('spot slide to lower end')
            self.trigger_exit(exit_type='SLDDOWN')
            print('trigger exit complete +++++++++')
            self.trade.slide_leg_group(self.lg_id, self.lg_index)

