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

    @classmethod
    def from_config(cls, trade_manager, ts_id):
        obj = cls(trade_manager, ts_id)
        trades = [Trade.from_config(obj, trd_idx) for trd_idx in range(1, 1 + obj.trade_manager.triggers_per_signal)]
        for trade in trades:
            obj.trades[trade.trd_idx] = trade
        return obj

    @classmethod
    def from_store(cls, trade_manager, ts_id):
        obj = cls(trade_manager, ts_id)
        trades = [Trade(obj, trd_idx) for trd_idx in range(1, 1 + obj.trade_manager.triggers_per_signal)]
        for trade in trades:
            obj.trades[trade.trd_idx] = trade
        return obj

    def get_entry_orders(self):
        entry_orders = []
        for trade_idx, trade in self.trades.items():
            all_orders = trade.get_entry_orders()
            entry_orders.append(all_orders)
        return entry_orders


class Trade:
    def __init__(self, trade_set, trd_idx):
        self.trd_idx = trd_idx
        self.trade_set = trade_set
        self.pnl = 0
        self.exit_time = self.trade_set.trade_manager.exit_time[trd_idx]
        self.carry_forward_days = self.trade_set.trade_manager.carry_forward_days[trd_idx]
        self.target = self.trade_set.trade_manager.trade_targets[trd_idx]
        self.stop_loss = self.trade_set.trade_manager.trade_stop_losses[trd_idx]
        self.spot_high_stop_loss = self.trade_set.trade_manager.spot_high_stop_losses[trd_idx]
        self.spot_low_stop_loss = self.trade_set.trade_manager.spot_low_stop_losses[trd_idx]
        self.spot_high_target = self.trade_set.trade_manager.spot_high_targets[trd_idx]
        self.spot_low_target = self.trade_set.trade_manager.spot_low_targets[trd_idx]
        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            self.leg_group_exits[key] = val[trd_idx]
        self.leg_groups = {}

    @classmethod
    def from_config(cls, trade_set, trd_idx):
        obj = cls(trade_set, trd_idx)
        leg_groups = copy.deepcopy(trade_set.trade_manager.trade_info["leg_groups"])
        #print(leg_groups)
        for leg_group_info in leg_groups:
            obj.leg_groups[leg_group_info['id']] = LegGroup.from_config(obj, leg_group_info)
        return obj

    @classmethod
    def from_store(cls, trade_set, trd_idx):
        obj = cls(trade_set, trd_idx)
        leg_groups = copy.deepcopy(trade_set.trade_manager.trade_info["leg_groups"])
        #print(leg_groups)
        for leg_group_info in leg_groups:
            obj.leg_groups[leg_group_info['id']] = LegGroup(obj, leg_group_info)
        return obj

    def get_entry_orders(self):
        entry_orders = {}
        entry_orders['trade_seq'] = self.trd_idx
        entry_orders['orders'] = []
        for leg_group in self.leg_groups.values():
            #print(leg_group.get_entry_orders())
            orders = leg_group.get_entry_orders()
            for order in orders['orders']:
                order['trade_seq'] = self.trd_idx
            entry_orders['orders'].append(orders)

        return entry_orders

    def close_on_exit_signal(self):
        for leg_seq, leg_details in self.legs.items():
            if leg_details['exit_type'] is None:  # Still active
                # self.strategy.trigger_exit(self.id, leg_seq, exit_type='EC')
                self.trigger_exit(leg_seq, exit_type='EC')

    def trigger_exit(self, leg_seq, exit_type=None, manage_risk=True):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.legs[leg_seq]['quantity']
        instrument = self.legs[leg_seq]['instrument']
        #updated_symbol = self.strategy.insight_book.ticker + "_" + instrument if self.strategy.inst_is_option(instrument) else self.strategy.insight_book.ticker
        signal_info = {'symbol': instrument, 'signal_id': self.id,
                       'leg_seq': leg_seq,
                       'qty': quantity}
        last_candle = self.strategy.get_last_tick(instrument)
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        self.legs[leg_seq]['exit_type'] = exit_type
        self.legs[leg_seq]['exit_price'] = last_candle['close']
        self.legs[leg_seq]['spot_exit_price'] = last_spot_candle['close']
        self.strategy.trigger_exit(signal_info)
        self.remove_controller(leg_seq)
        if self.trade_complete() and manage_risk:
            self.strategy.manage_risk()


class LegGroup:
    def __init__(self, trade, leg_group_info):
        self.id = leg_group_info['id']
        self.trade = trade
        self.pnl = 0
        self.completed = False
        self.leg_group_info = leg_group_info
        self.target = self.trade.leg_group_exits['targets'][self.id]
        self.stop_loss = self.trade.leg_group_exits['stop_losses'][self.id]
        self.spot_high_stop_loss = self.trade.leg_group_exits['spot_high_stop_losses'][self.id]
        self.spot_low_stop_loss = self.trade.leg_group_exits['spot_low_stop_losses'][self.id]
        self.spot_high_target = self.trade.leg_group_exits['spot_high_targets'][self.id]
        self.spot_low_target = self.trade.leg_group_exits['spot_low_targets'][self.id]
        self.legs = {}

    @classmethod
    def from_config(cls, trade, leg_group_info):
        obj = cls(trade, leg_group_info)
        for leg_id, leg_info in leg_group_info["legs"].items():
            obj.legs[leg_id] = Leg.from_config(trade, int(leg_id), leg_info)
        return obj

    def get_entry_orders(self):
        entry_orders = {}
        entry_orders['leg_group_id'] = self.id
        entry_orders['orders'] = []
        for leg in self.legs.values():
            entry_orders['orders'].append(leg.to_dict())
        for order in entry_orders['orders']:
            order['leg_group_id'] = self.id
        entry_orders['orders'] = sorted(entry_orders['orders'], key=lambda d: d['order_type'])
        return entry_orders

class Leg:
    @classmethod
    def from_config(cls, trade, idx, leg_info):
        instr = Instrument.from_config(trade.trade_set.trade_manager.market_book, leg_info['instr_to_trade'])
        last_candle = instr.get_last_tick()
        last_spot_candle = trade.trade_set.trade_manager.get_last_tick(leg_info['instr_to_trade']['asset'], 'SPOT')
        entry_price = last_candle['close']
        exit_price = None
        spot_entry_price = last_spot_candle['close']
        spot_exit_price = None
        trigger_time = last_spot_candle['timestamp']
        quantity = leg_info['quantity']
        order_type = leg_info['order_type']
        return cls(trade, idx, instr, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time)

    def __init__(self, trade, idx, instrument, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time):
        self.trade = trade
        self.idx = idx
        self.instrument = instrument
        self.order_type = order_type
        self.quantity = quantity
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.spot_entry_price = spot_entry_price
        self.spot_exit_price = spot_exit_price
        self.trigger_time = trigger_time
        print('self.strategy.force_exit_ts++++++++++++++++++', self.trade.trade_set.trade_manager.force_exit_ts)

    @classmethod
    def from_store(cls, trade, idx, **kwargs):
        return cls(trade, idx, **kwargs)

    def to_dict(self):
        dct = {}
        for field in ['idx', 'order_type', 'quantity', 'entry_price', 'exit_price', 'spot_entry_price', 'spot_exit_price', 'trigger_time']:
            dct[field] = getattr(self, field)
        dct['instrument'] = self.instrument.to_dict()
        return dct
