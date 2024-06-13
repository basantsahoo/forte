from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from helper.utils import inst_is_option, get_market_view
import itertools
from helper.utils import get_option_strike
from strat_machine.trade_master.controllers import get_controller
import copy

from strat_machine.trade_master.leg_group import LegGroup

class TradeSet:
    def __init__(self, trade_manager, ts_id):
        self.id = ts_id
        self.trade_manager = trade_manager
        self.trades = {}
        self.custom_features = {}
        self.exit_orders = []
        self.completed = False
        self.controller_list = []

    @classmethod
    def from_config(cls, trade_manager, ts_id):
        obj = cls(trade_manager, ts_id)
        trades = [Trade.from_config(obj, trd_idx) for trd_idx in range(1, 1 + obj.trade_manager.triggers_per_signal)]
        for trade in trades:
            obj.trades[trade.trd_idx] = trade
        return obj

    @classmethod
    def from_store(cls, trade_manager, ts_id, trade_set_info):
        obj = cls(trade_manager, ts_id)
        trades = [Trade.from_store(obj, trade_info) for trade_info in trade_set_info]
        for trade in trades:
            obj.trades[trade.trd_idx] = trade
        return obj

    def get_entry_orders(self):
        entry_orders = []
        for trade_idx, trade in self.trades.items():
            all_orders = trade.get_entry_orders()
            entry_orders.append(all_orders)
        return entry_orders


    def complete(self):
        trade_set_complete = True
        for trade in self.trades.values():
            trade_set_complete = trade_set_complete and trade.complete()
        self.completed = trade_set_complete
        return trade_set_complete

    def close_on_exit_signal(self):
        if not self.complete():
            self.trigger_exit(exit_type='EC')
            check_complete_test = self.complete()

    def trigger_exit(self, exit_type, manage_risk=True):
        for trade_id, trade in self.trades.items():
            if not trade.complete():
                trade.trigger_exit(exit_type)
        self.process_exit_orders(manage_risk)

    def monitor_existing_positions(self, manage_risk=True):
        for trade_id, trade in self.trades.items():
            if not trade.complete():
                trade.monitor_existing_positions()
        self.process_exit_orders(manage_risk)

    def process_exit_orders(self, manage_risk=True):
        if self.exit_orders:
            self.trade_manager.strategy.trigger_exit(self.id, self.exit_orders)
            self.exit_orders = []
            if self.complete() and manage_risk:
                self.trade_manager.strategy.manage_risk()

    # This is for trade controllers
    def register_signal(self, signal):
        for trade_id, trade in self.trades.items():
            trade.register_signal(signal)


    def force_close(self):
        self.trigger_exit(exit_type='FC', manage_risk=False)


class Trade:
    def __init__(self, trade_set, trd_idx):
        self.trd_idx = trd_idx
        self.trade_set = trade_set
        self.pnl = 0
        durations = self.trade_set.trade_manager.durations
        carry_forward_days = self.trade_set.trade_manager.carry_forward_days
        targets = self.trade_set.trade_manager.trade_targets
        stop_losses = self.trade_set.trade_manager.trade_stop_losses
        spot_high_stop_losses = self.trade_set.trade_manager.spot_high_stop_losses
        spot_low_stop_losses = self.trade_set.trade_manager.spot_low_stop_losses
        spot_high_targets = self.trade_set.trade_manager.spot_high_targets
        spot_low_targets = self.trade_set.trade_manager.spot_low_targets
        self.durations = durations[min(trd_idx - 1, len(durations) - 1)] if durations else None
        self.carry_forward_days = carry_forward_days[min(trd_idx - 1, len(carry_forward_days) - 1)] if carry_forward_days else None
        self.target = abs(targets[min(trd_idx - 1, len(targets) - 1)]) if targets else None
        self.stop_loss = -1 * abs(stop_losses[min(trd_idx - 1, len(stop_losses) - 1)]) if stop_losses else None
        self.spot_high_stop_loss = abs(self.calculate_target(spot_high_stop_losses[min(trd_idx - 1, len(spot_high_stop_losses) - 1)])) if spot_high_stop_losses else float('inf')
        self.spot_low_stop_loss = -1 * abs(self.calculate_target(spot_low_stop_losses[min(trd_idx - 1, len(spot_low_stop_losses) - 1)])) if spot_low_stop_losses else float('-inf')
        self.spot_high_target = abs(self.calculate_target(spot_high_targets[min(trd_idx - 1, len(spot_high_targets) - 1)])) if spot_high_targets else float('inf')
        self.spot_low_target = -1 * abs(self.calculate_target(spot_low_targets[min(trd_idx - 1, len(spot_low_targets) - 1)])) if spot_low_targets else float('-inf')

        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            if val:
                self.leg_group_exits[key] = val[trd_idx-1]
            else:
                self.leg_group_exits[key] = []
        self.leg_groups = {}
        self.exit_orders = []
        self.trigger_time = None
        self.exit_time = None
        self.spot_stop_loss_rolling = None
        self.force_exit_time = trade_set.trade_manager.trade_info.get('force_exit_time', None)
        if self.force_exit_time is None:
            self.force_exit_time = self.trade_set.trade_manager.market_book.get_force_exit_ts(trade_set.trade_manager.trade_info.get('force_exit_ts', None))
        self.trade_duration = None
        self.spot_entry_price = None

        self.controller_list = []
        self.con_seq = 0


    @classmethod
    def from_config(cls, trade_set, trd_idx):
        obj = cls(trade_set, trd_idx)
        leg_groups = copy.deepcopy(trade_set.trade_manager.trade_info["leg_groups"])
        #print(leg_groups)
        for lg_index, leg_group_info in enumerate(leg_groups):
            obj.leg_groups[leg_group_info['lg_id']] = LegGroup.from_config(obj, lg_index, leg_group_info)
        obj.other_init()
        return obj

    @classmethod
    def from_store(cls, trade_set, trade_info):
        obj = cls(trade_set, trade_info['trd_idx'])
        for leg_group_info in trade_info["leg_groups"]:
            obj.leg_groups[leg_group_info['lg_id']] = LegGroup.from_store(obj, leg_group_info)
        obj.other_init()
        return obj

    def other_init(self):
        self.trade_duration = max([leg_group.duration for leg_group in self.leg_groups.values()])
        self.spot_entry_price = self.leg_groups[list(self.leg_groups.keys())[0]].spot_entry_price

    def set_controllers(self):
        if self.trade_set.trade_manager.strategy.trade_controllers:
            total_controllers = len(self.trade_set.trade_manager.strategy.trade_controllers)
            controller_info = self.trade_set.trade_manager.strategy.trade_controllers[min(self.trd_idx - 1, total_controllers - 1)]
            controller_id = self.con_seq
            self.con_seq += 1
            controller = get_controller(repr(self.trd_idx) + "_" + repr(controller_id), self.trd_idx, self.spot_entry_price,
                                        self.spot_stop_loss_rolling, self.calculate_delta(), controller_info)
            controller.activation_forward_channels.append(self.receive_communication)
            self.controller_list.append(controller)



    def get_entry_orders(self):
        entry_orders = {}
        entry_orders['trade_seq'] = self.trd_idx
        entry_orders['leg_groups'] = []
        for leg_group in self.leg_groups.values():
            #print(leg_group.get_entry_orders())
            orders = leg_group.get_entry_orders()
            for order in orders['legs']:
                order['trade_seq'] = self.trd_idx
            entry_orders['leg_groups'].append(orders)
        self.trigger_time = self.leg_groups[list(self.leg_groups.keys())[0]].trigger_time
        self.spot_entry_price = self.leg_groups[list(self.leg_groups.keys())[0]].spot_entry_price

        spot_high_target_levels = self.trade_set.trade_manager.spot_high_target_levels
        spot_high_stop_loss_levels = self.trade_set.trade_manager.spot_high_stop_loss_levels
        spot_low_target_levels = self.trade_set.trade_manager.spot_low_target_levels
        spot_low_stop_loss_levels = self.trade_set.trade_manager.spot_low_stop_loss_levels

        spot_high_target_level = spot_high_target_levels[min(self.trd_idx - 1, len(spot_high_target_levels) - 1)] if spot_low_target_levels else float('inf')
        spot_high_stop_loss_level = spot_high_stop_loss_levels[min(self.trd_idx - 1, len(spot_high_stop_loss_levels) - 1)] if spot_high_stop_loss_levels else float('inf')
        spot_low_target_level = spot_low_target_levels[min(self.trd_idx - 1, len(spot_low_target_levels) - 1)] if spot_low_target_levels else float('-inf')
        spot_low_stop_loss_level = spot_low_stop_loss_levels[min(self.trd_idx - 1, len(spot_low_stop_loss_levels) - 1)] if spot_low_stop_loss_levels else float('-inf')

        self.spot_high_target = round(min(self.spot_high_target, spot_high_target_level/self.spot_entry_price-1), 4) #if isinstance(self.spot_high_target, (int, float)) else self.calculate_target(self.spot_high_target)
        self.spot_high_stop_loss = round(min(self.spot_high_stop_loss, spot_high_stop_loss_level / self.spot_entry_price - 1), 4) #if isinstance(self.spot_high_stop_loss, (int, float)) else self.calculate_target(self.spot_high_stop_loss)
        self.spot_low_target = round(min(self.spot_low_target, spot_low_target_level / self.spot_entry_price - 1), 4) #if isinstance(self.spot_low_target, (int, float)) else self.calculate_target(self.spot_low_target)
        self.spot_low_stop_loss = round(min(self.spot_low_stop_loss, spot_low_stop_loss_level / self.spot_entry_price - 1), 4) #if isinstance(self.spot_low_stop_loss, (int, float)) else self.calculate_target(self.spot_low_stop_loss)
        delta = self.calculate_delta()
        self.spot_stop_loss_rolling = self.spot_low_stop_loss if delta > 0 else self.spot_high_stop_loss
        self.set_controllers()

        return entry_orders

    def calculate_target(self, target_level):
        print('calculate_target+++++++++++++++++++++++++', target_level)
        mapped_fn = target_level['mapped_fn']
        kwargs = target_level.get('kwargs', {})
        rs = None
        if isinstance(target_level, (int, float)):
            rs = target_level
        elif target_level['category'] == 'signal_queue':
            queue = self.trade_set.trade_manager.strategy.entry_signal_pipeline.get_neuron_by_id(target_level['mapped_object'])
            # print('queue.'+ mapped_fn + "()")
            rs = eval('queue.' + mapped_fn)(**kwargs)
            print('inside target fn +++++++++', rs)
        elif target_level['category'] == 'global':
            obj = target_level['mapped_object']
            fn_string = 'self.' + (obj + '.' if obj else '') + mapped_fn  # + '()'
            # print(fn_string)
            rs = eval(fn_string)(**kwargs)
        return rs

    def complete(self):
        all_leg_groups_complete = True
        for leg_group in self.leg_groups.values():
            all_leg_groups_complete = all_leg_groups_complete and leg_group.complete()
        return all_leg_groups_complete

    def to_dict(self):
        dct = {}

        for field in ['trd_idx']:
            dct[field] = getattr(self, field)

        dct['leg_groups'] = [leg_group.to_dict() for leg_group in self.leg_groups.values()]

        return dct

    def process_exit_orders(self):
        if self.exit_orders:
            exit_orders = dict()
            exit_orders['trade_seq'] = self.trd_idx
            exit_orders['leg_groups'] = self.exit_orders
            self.exit_orders = []
            self.trade_set.exit_orders.append(exit_orders)
            all_leg_group_exits = [lg.exit_time for lg in self.leg_groups.values()]
            self.exit_time = None if None in all_leg_group_exits else max(all_leg_group_exits)

    def trigger_exit(self, exit_type):
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.trigger_exit(exit_type)
        self.process_exit_orders()

    def monitor_existing_positions(self):
        self.close_on_trade_tg_sl_tm()
        self.close_on_spot_tg_sl()
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.close_on_instr_tg_sl_tm()
            if not leg_group.complete():
                leg_group.close_on_spot_tg_sl()
        self.process_exit_orders()

    def calculate_pnl(self):
        capital_list = []
        pnl_list = []
        for leg_group_id, leg_group in self.leg_groups.items():
            capital, pnl, pnl_pct = leg_group.calculate_pnl()
            capital_list.append(capital)
            pnl_list.append(pnl)
        pnl_ratio = sum(pnl_list)/sum(capital_list)
        return sum(capital_list), sum(pnl_list), pnl_ratio

    def calculate_delta(self):
        trade_delta = []
        for leg_group_id, leg_group in self.leg_groups.items():
            delta = leg_group.delta
            trade_delta.append(delta)
        return sum(trade_delta)

    def close_on_trade_tg_sl_tm(self):
        capital, pnl, pnl_pct = self.calculate_pnl()
        print('trade p&l==========', pnl_pct)
        asset = list(self.leg_groups.values())[0].asset
        last_spot_candle = self.trade_set.trade_manager.get_last_tick(asset, 'SPOT')
        max_run_time = self.trigger_time + self.trade_duration * 60 if self.force_exit_time is None else min(
            self.trigger_time + self.trade_duration * 60, self.force_exit_time + 60)
        if last_spot_candle['timestamp'] >= max_run_time:
            self.trigger_exit(exit_type='TRD_TC')
        elif self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit(exit_type='TRD_TSFE')
        elif self.target and pnl_pct > self.target:
            self.trigger_exit(exit_type='TRD_TT')
        elif self.stop_loss and pnl_pct < self.stop_loss:
            self.trigger_exit(exit_type='TRD_TS')

    def close_on_spot_tg_sl(self):
        asset = list(self.leg_groups.values())[0].asset
        last_spot_candle = self.trade_set.trade_manager.get_last_tick(asset, 'SPOT')
        delta = self.calculate_delta()
        if delta > 0:
            if self.spot_high_target and last_spot_candle['close'] >= self.spot_entry_price * (1 + self.spot_high_target):
                self.trigger_exit(exit_type='TRD_ST')
            elif self.spot_low_stop_loss and last_spot_candle['close'] < self.spot_entry_price * (1 + self.spot_low_stop_loss):
                self.trigger_exit(exit_type='TRD_SS')
            elif self.spot_stop_loss_rolling and last_spot_candle['close'] < self.spot_stop_loss_rolling:
                self.trigger_exit(exit_type='TRD_SRS')

        elif delta < 0:
            if self.spot_low_target and last_spot_candle['close'] <= self.spot_entry_price * (1 + self.spot_low_target):
                self.trigger_exit(exit_type='TRD_ST')
                # print(last_candle, trigger_details['target'])
            elif self.spot_high_stop_loss and last_spot_candle['close'] > self.spot_entry_price * (1 + self.spot_high_stop_loss):
                self.trigger_exit(exit_type='TRD_SS')
            elif self.spot_stop_loss_rolling and last_spot_candle['close'] > self.spot_stop_loss_rolling:
                self.trigger_exit(exit_type='TRD_SRS')

    # This is for trade controllers
    def register_signal(self, signal):
        for controller in self.controller_list:
            """
            print('controller++++++++++++++++++++++++++++++++++++++++++++++')
            print(signal.key())
            print(tuple(controller.signal_type))
            """
            if signal.key() == tuple(controller.signal_type):
                #print('signal', signal)
                controller.receive_signal(signal)


    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'revise_stop_loss':
            if self.trd_idx == info['target_trade']:
                self.spot_stop_loss_rolling = info['new_threshold']
                print("Trade set", self.trade_set.id, "new stop loss for trade ", info['target_trade'], 'is ', self.spot_stop_loss_rolling)

    def communication_log(self, info):
        #last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        print('Trade id==', repr(self.trd_idx), "COM  LOG", 'From Controller id==', info['n_id'], "sent code==", info['code'], "==")
