from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from helper.utils import inst_is_option, get_market_view
import itertools
from helper.utils import get_option_strike
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

    def register_signal(self, signal):
        for controller in self.controller_list:
            if signal.key() == controller.signal_type:
                #print('signal', signal)
                controller.receive_signal(signal)


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
        self.target = targets[min(trd_idx - 1, len(targets) - 1)] if targets else None
        self.stop_loss = stop_losses[min(trd_idx - 1, len(stop_losses) - 1)] if stop_losses else None
        self.spot_high_stop_loss = spot_high_stop_losses[min(trd_idx - 1, len(spot_high_stop_losses) - 1)] if spot_high_stop_losses else None
        self.spot_low_stop_loss = spot_low_stop_losses[min(trd_idx - 1, len(spot_low_stop_losses) - 1)] if spot_low_stop_losses else None
        self.spot_high_target = spot_high_targets[min(trd_idx - 1, len(spot_high_targets) - 1)] if spot_high_targets else None
        self.spot_low_target = spot_low_targets[min(trd_idx - 1, len(spot_low_targets) - 1)] if spot_low_targets else None
        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            self.leg_group_exits[key] = val[trd_idx-1]
        self.leg_groups = {}
        self.exit_orders = []
        self.trigger_time = None
        self.exit_time = None


    @classmethod
    def from_config(cls, trade_set, trd_idx):
        obj = cls(trade_set, trd_idx)
        leg_groups = copy.deepcopy(trade_set.trade_manager.trade_info["leg_groups"])
        #print(leg_groups)
        for lg_index, leg_group_info in enumerate(leg_groups):
            obj.leg_groups[leg_group_info['lg_id']] = LegGroup.from_config(obj, lg_index, leg_group_info)
        return obj

    @classmethod
    def from_store(cls, trade_set, trade_info):
        obj = cls(trade_set, trade_info['trd_idx'])
        for leg_group_info in trade_info["leg_groups"]:
            obj.leg_groups[leg_group_info['lg_id']] = LegGroup.from_store(obj, leg_group_info)
        return obj

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
        return entry_orders

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
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.close_on_instr_tg_sl_tm()
            if not leg_group.complete():
                leg_group.close_on_spot_tg_sl()
        self.process_exit_orders()



