from strat_machine.trade_master.leg import Leg
from helper.utils import get_broker_order_type, get_exit_order_type

class LegGroup:
    def __init__(self, trade, lg_index, leg_group_info):
        self.lg_id = leg_group_info['lg_id']
        self.lg_index = lg_index
        self.asset = leg_group_info['asset']
        self.trade = trade
        self.completed = False
        #self.leg_group_info = leg_group_info
        self.target = abs(self.trade.leg_group_exits['targets'][self.lg_id])
        self.stop_loss = -1 * abs(self.trade.leg_group_exits['stop_losses'][self.lg_id])
        self.spot_high_stop_loss = -1 * abs(self.trade.leg_group_exits['spot_high_stop_losses'][self.lg_id])
        self.spot_low_stop_loss = -1 * (self.trade.leg_group_exits['spot_low_stop_losses'][self.lg_id])
        self.spot_high_target = abs(self.trade.leg_group_exits['spot_high_targets'][self.lg_id])
        self.spot_low_target = abs(self.trade.leg_group_exits['spot_low_targets'][self.lg_id])
        self.carry_forward_days = self.trade.carry_forward_days
        self.legs = {}
        self.trigger_time = leg_group_info.get('trigger_time', None)
        self.exit_time = leg_group_info.get('exit_time', None)

        self.force_exit_time = leg_group_info.get('force_exit_time', None)
        if self.force_exit_time is None:
            self.force_exit_time = self.set_force_exit_ts(leg_group_info.get('force_exit_ts', None))
        self.delta = leg_group_info.get('delta', 0)  # >0 means we are long <0 means we are sort
        self.duration = min(self.trade.durations[lg_index - 1], self.trade.trade_set.trade_manager.market_book.get_time_to_close() - 2) if not self.carry_forward_days else 90000000

    def set_force_exit_ts(self, force_exit_ts):
        if force_exit_ts is None:
            return None
        else:
            if force_exit_ts[0] == 'weekly_expiry_day':
                asset_book = self.trade.trade_set.trade_manager.market_book.get_asset_book(self.asset)
                return asset_book.get_expiry_day_time(force_exit_ts[1])

    @classmethod
    def from_config(cls, trade, lg_index, leg_group_info):
        obj = cls(trade, lg_index, leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_config(obj, leg_id, leg_info)
        if obj.trigger_time is None:
            #obj.trigger_time = obj.legs[list(obj.legs.keys())[0]].trigger_time
            obj.delta = obj.calculate_delta()
        return obj

    @classmethod
    def from_store(cls, trade, leg_group_info):
        obj = cls(trade, leg_group_info['lg_index'], leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_store(obj, **leg_info)
        return obj


    def get_entry_orders(self):
        entry_orders = {}
        entry_orders['lg_id'] = self.lg_id
        entry_orders['legs'] = []
        for leg in self.legs.values():
            entry_orders['legs'].append(leg.to_dict())
        for order in entry_orders['legs']:
            order['lg_id'] = self.lg_id
        entry_orders['legs'] = sorted(entry_orders['legs'], key=lambda d: d['order_type'])
        self.trigger_time = self.legs[list(self.legs.keys())[0]].trigger_time
        return entry_orders

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
        self.trade.exit_orders.append(exit_orders)


    def complete(self):
        all_legs_complete = True
        for leg in self.legs.values():
            all_legs_complete = all_legs_complete and leg.exit_type is not None
        return all_legs_complete

    def to_dict(self):
        dct = {}
        for field in ['lg_index', 'lg_id', 'asset', 'trigger_time', 'delta']:
            dct[field] = getattr(self, field)
        dct['legs'] = {k:v.to_dict() for k,v in self.legs.items()}
        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['lg_id', 'duration', 'delta']:
            dct[field] = getattr(self, field)
        for field in ['exit_time']:
            dct['lg_' + field] = getattr(self, field)
        return dct

    def calculate_pnl(self):
        lg_pnl = []
        lg_capital = []
        for leg_id, leg in self.legs.items():
            ltp = leg.instrument.get_last_tick()['close']
            side = get_broker_order_type(leg.order_type)
            exit_order_type = get_exit_order_type(side)
            un_realized_pnl = exit_order_type * abs(leg.quantity) * (leg.entry_price - ltp)
            capital = abs(leg.quantity) * leg.entry_price
            lg_pnl.append(un_realized_pnl)
            lg_capital.append(capital)
        pnl_ratio = sum(lg_pnl)/sum(lg_capital)
        return pnl_ratio

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
        pnl = self.calculate_pnl()
        if last_spot_candle['timestamp'] >= max_run_time:
            self.trigger_exit(exit_type='TC')
        elif self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit(exit_type='TSFE')
        elif self.target and pnl > self.target:
            self.trigger_exit(exit_type='IT')
        elif self.stop_loss and pnl < self.stop_loss:
            self.trigger_exit(exit_type='IS')

    def close_on_spot_tg_sl(self):
        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick(self.asset, 'SPOT')
        if self.delta > 0:
            if self.spot_high_target and last_spot_candle['close'] >= self.spot_high_target:
                self.trigger_exit(exit_type='ST')
            elif self.spot_low_stop_loss and last_spot_candle['close'] < self.spot_low_stop_loss:
                self.trigger_exit(exit_type='SS')
        elif self.delta < 0:
            if self.spot_low_target and last_spot_candle['close'] <= (1 + self.spot_low_target):
                self.trigger_exit(exit_type='ST')
                # print(last_candle, trigger_details['target'])
            elif self.spot_high_stop_loss and last_spot_candle['close'] > self.spot_high_stop_loss:
                self.trigger_exit(exit_type='SS')

    def calculate_target(self, instr, target_level_list):

        levels = []
        last_candle = self.strategy.get_last_tick(instr)
        close_point = last_candle['close']

        for target_level in target_level_list:

            if isinstance(target_level, (int, float)):
                target = close_point * (1 + target_level)
                levels.append(target)
            else:
                #print('calculate_target+++++++++++++++++++++++++', target_level)
                #print(target_level[0])
                mapped_fn = target_level['mapped_fn']
                kwargs = target_level.get('kwargs', {})
                rs = 0
                if target_level['category'] == 'signal_queue':
                    #queue = self.strategy.entry_signal_pipeline.get_que_by_category(target_level['mapped_object'])#self.entry_signal_queues[target_level['mapped_object']]
                    queue = self.strategy.entry_signal_pipeline.get_neuron_by_id(target_level['mapped_object'])
                    # print('queue.'+ mapped_fn + "()")
                    rs = eval('queue.' + mapped_fn)(**kwargs)
                    print('inside target fn +++++++++', rs)
                elif target_level['category'] == 'global':
                    obj = target_level['mapped_object']
                    fn_string = 'self.' + (obj + '.' if obj else '') + mapped_fn  # + '()'
                    # print(fn_string)
                    rs = eval(fn_string)(**kwargs)
                if rs:
                    levels.append(rs)
        return levels