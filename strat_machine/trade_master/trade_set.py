from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from helper.utils import inst_is_option, get_market_view
import itertools
from helper.utils import get_option_strike
import copy
from strat_machine.trade_master.instrument import Instrument
from strat_machine.trade_master.common import _asdict

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
        self.trade_manager.strategy.trigger_exit(self.id, self.exit_orders)
        self.exit_orders = []
        if self.complete() and manage_risk:
            self.trade_manager.strategy.manage_risk()

    def monitor_existing_positions(self):
        for trade_id, trade in self.trades.items():
            if not trade.complete():
                trade.monitor_existing_positions()

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
        self.exit_time = self.trade_set.trade_manager.exit_time[trd_idx-1]
        self.carry_forward_days = self.trade_set.trade_manager.carry_forward_days[trd_idx-1]
        self.target = self.trade_set.trade_manager.trade_targets[trd_idx-1]
        self.stop_loss = self.trade_set.trade_manager.trade_stop_losses[trd_idx-1]
        self.spot_high_stop_loss = self.trade_set.trade_manager.spot_high_stop_losses[trd_idx-1]
        self.spot_low_stop_loss = self.trade_set.trade_manager.spot_low_stop_losses[trd_idx-1]
        self.spot_high_target = self.trade_set.trade_manager.spot_high_targets[trd_idx-1]
        self.spot_low_target = self.trade_set.trade_manager.spot_low_targets[trd_idx-1]
        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            self.leg_group_exits[key] = val[trd_idx-1]
        self.leg_groups = {}
        self.exit_orders = []


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

    def trigger_exit(self, exit_type):
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.trigger_exit(exit_type)
        exit_orders = {}
        exit_orders['trade_seq'] = self.trd_idx
        exit_orders['leg_groups'] = self.exit_orders
        self.exit_orders = []
        self.trade_set.exit_orders.append(exit_orders)

    def monitor_existing_positions(self):
        pass
        """
        self.close_on_instr_tg_sl_tm()
        self.close_on_spot_tg_sl()
        """


class LegGroup:
    def __init__(self, trade, lg_index, leg_group_info):
        self.lg_id = leg_group_info['lg_id']
        self.lg_index = lg_index
        self.asset = leg_group_info['asset']
        self.market_view = leg_group_info.get('market_view', 'LONG')
        self.trade = trade
        self.pnl = 0
        self.completed = False
        #self.leg_group_info = leg_group_info
        self.target = self.trade.leg_group_exits['targets'][self.lg_id]
        self.stop_loss = self.trade.leg_group_exits['stop_losses'][self.lg_id]
        self.spot_high_stop_loss = self.trade.leg_group_exits['spot_high_stop_losses'][self.lg_id]
        self.spot_low_stop_loss = self.trade.leg_group_exits['spot_low_stop_losses'][self.lg_id]
        self.spot_high_target = self.trade.leg_group_exits['spot_high_targets'][self.lg_id]
        self.spot_low_target = self.trade.leg_group_exits['spot_low_targets'][self.lg_id]
        self.legs = {}


    @classmethod
    def from_config(cls, trade, lg_index, leg_group_info):
        obj = cls(trade, lg_index, leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_config(obj, leg_id, leg_info)
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
        self.trade.exit_orders.append(exit_orders)


    def complete(self):
        all_legs_complete = True
        for leg in self.legs.values():
            all_legs_complete = all_legs_complete and leg.exit_type is not None
        return all_legs_complete

    def to_dict(self):
        dct = {}
        for field in ['lg_index', 'lg_id', 'asset']:
            dct[field] = getattr(self, field)
        dct['legs'] = {k:v.to_dict() for k,v in self.legs.items()}
        return dct


class Leg:
    @classmethod
    def from_config(cls, leg_group, leg_id, leg_info):
        leg_info['instr_to_trade']['asset'] = leg_group.asset
        instr = Instrument.from_config(leg_group.trade.trade_set.trade_manager.market_book, leg_info['instr_to_trade'])
        last_candle = instr.get_last_tick()
        last_spot_candle = leg_group.trade.trade_set.trade_manager.get_last_tick(instr.asset, 'SPOT')
        entry_price = last_candle['close']
        exit_price = None
        spot_entry_price = last_spot_candle['close']
        spot_exit_price = None
        trigger_time = last_spot_candle['timestamp']
        quantity = leg_info['quantity']
        order_type = leg_info['order_type']
        return cls(leg_group, leg_id, instr, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time)

    def __init__(self, leg_group, leg_id, instrument, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time):
        self.leg_group = leg_group
        self.leg_id = leg_id
        self.instrument = instrument
        self.order_type = order_type
        self.quantity = quantity
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.spot_entry_price = spot_entry_price
        self.spot_exit_price = spot_exit_price
        self.trigger_time = trigger_time
        self.exit_type = None
        print('self.strategy.force_exit_ts++++++++++++++++++', self.leg_group.trade.trade_set.trade_manager.force_exit_ts)
        #trade_info['max_run_time'] = trade_info['trigger_time'] + trade_info['duration'] * 60 if self.strategy.force_exit_ts is None else min(trade_info['trigger_time'] + trade_info['duration'] * 60, self.strategy.force_exit_ts + 60)
    @classmethod
    def from_store(cls, leg_group, **kwargs):
        kwargs['instrument'] = Instrument.from_store(leg_group.trade.trade_set.trade_manager.market_book, kwargs['instrument'])
        return cls(leg_group,  **kwargs)

    def to_dict(self):
        dct = {}
        for field in ['leg_id', 'order_type', 'quantity', 'entry_price', 'exit_price', 'spot_entry_price', 'spot_exit_price', 'trigger_time']:
            dct[field] = getattr(self, field)
        dct['instrument'] = self.instrument.to_dict()
        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['order_type', 'quantity', 'entry_price', 'exit_price', 'spot_entry_price', 'spot_exit_price', 'trigger_time']:
            dct[field] = getattr(self, field)
        dct['instrument'] = self.instrument.instr_code
        dct['asset'] = self.instrument.asset
        return dct

    def trigger_exit(self, exit_type=None):
        last_candle = self.instrument.get_last_tick()
        last_spot_candle = self.leg_group.trade.trade_set.trade_manager.get_last_tick(self.instrument.asset, 'SPOT')
        self.exit_type = exit_type
        self.exit_price = last_candle['close']
        self.spot_exit_price = last_spot_candle['close']
