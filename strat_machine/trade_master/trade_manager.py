from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from strat_machine.trade_master.common import _asdict
from helper.utils import inst_is_option, get_market_view
from strat_machine.trade_master.trade_set import TradeSet
import itertools
from helper.utils import get_option_strike
import copy


class TradeManager:

    @classmethod
    def from_config(cls, market_book, strategy, **kwargs):
        args = get_trade_manager_args(**kwargs)
        """
        if persist_dir is None:
            docstore = docstore or SimpleDocumentStore()
            index_store = index_store or SimpleIndexStore()
            vector_store = vector_store or SimpleVectorStore()
            graph_store = graph_store or SimpleGraphStore()
        """
        return cls(market_book=market_book, strategy=strategy, **args)

    def to_dict(self, encode_json=False):
        return _asdict(self, encode_json=encode_json)

    def __init__(self,
                 market_book=None,
                 strategy=None,
                 asset=None,
                 durations=[10],
                 exit_at=None,
                 carry_forward_days=[0],
                 triggers_per_signal=1,
                 spot_high_targets=[],  # [0.002,0.003, 0.004, 0.005],
                 spot_high_stop_losses=[],  # [-0.001, -0.002, -0.002, -0.002],
                 spot_low_targets=[],  # [-0.002, -0.003, -0.004, -0.005],
                 spot_low_stop_losses=[],  # [0.001, 0.002, 0.002, 0.002],
                 spot_high_target_levels=[],
                 spot_high_stop_loss_levels=[],
                 spot_low_target_levels=[],
                 spot_low_stop_loss_levels=[],
                 trade_targets=[],  # [0.002,0.003, 0.004, 0.005],
                 trade_stop_losses=[],  # [-0.001,-0.002, -0.002,-0.002]
                 leg_group_exits={},
                 trade_info={},
                 force_exit_ts=None,
                 trade_controllers=[],
                 risk_limits=0
                 ):
        # print('entry_signal_queues====',entry_signal_queues)
        self.strategy = strategy
        self.asset = asset
        self.durations = durations
        self.exit_at = exit_at
        self.triggers_per_signal = min(4, triggers_per_signal)  # Dont go past 4
        self.spot_high_targets = [abs(x) if isinstance(x, (int, float)) else x for x in spot_high_targets]
        self.spot_high_stop_losses = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in
                                      spot_high_stop_losses]
        self.spot_low_targets = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in spot_low_targets]
        self.spot_low_stop_losses = [abs(x) if isinstance(x, (int, float)) else x for x in spot_low_stop_losses]
        self.spot_high_target_levels = spot_high_target_levels
        self.spot_high_stop_loss_levels = spot_high_stop_loss_levels
        self.spot_low_target_levels = spot_low_target_levels
        self.spot_low_stop_loss_levels = spot_low_stop_loss_levels
        self.carry_forward_days = carry_forward_days
        side = 1  # get_broker_order_type(self.order_type)
        self.trade_targets = [side * abs(x) for x in trade_targets]
        self.trade_stop_losses = [-1 * side * abs(x) for x in trade_stop_losses]
        self.leg_group_exits = leg_group_exits
        self.force_exit_ts = force_exit_ts
        self.trade_controllers = trade_controllers
        self.risk_limits = risk_limits
        self.tradable_signals = {}
        self.asset_book = market_book.get_asset_book(self.asset) if market_book is not None else None
        self.market_book = market_book
        self.restore_variables = {}
        self.registered_signal = None
        self.trade_info = trade_info
        self.signal_count = 0

    def initiate_signal_trades(self):
        print('TradeManager initiate_signal_trades+++++++++++++++++')
        sig_key = self.market_book.trade_day + "_" + str(self.signal_count + 1)
        self.signal_count += 1
        self.tradable_signals[sig_key] = TradeSet.from_config(self, sig_key)
        return sig_key

    def trigger_entry(self, sig_key):
        print('TradeManager trigger_entry +++++++++++++++++')
        trade_set = self.tradable_signals[sig_key]
        all_orders = trade_set.get_entry_orders()
        self.strategy.trigger_entry(sig_key, all_orders)

    def monitor_existing_positions(self):
        for trade_set_id, trade_set in self.tradable_signals.items():
            trade_set.monitor_existing_positions()

    def close_on_exit_signal(self):
        for trade_set_id, trade_set in self.tradable_signals.items():
            if not trade_set.complete():
                trade_set.close_on_exit_signal()

    def get_last_tick(self, asset, instr='SPOT'):
        asset_book = self.market_book.get_asset_book(asset)
        if inst_is_option(instr):
            last_candle = asset_book.option_matrix.get_last_tick(instr)
        else:
            last_candle = asset_book.spot_book.spot_processor.last_tick
        return last_candle

    def get_closest_instrument(self, asset, instr='SPOT'):
        if inst_is_option(instr):
            asset_book = self.market_book.get_asset_book(asset)
            instr = asset_book.get_closest_instrument(instr)
        else:
            instr = instr
        return instr

    def register_signal(self, signal):
        if signal.key() == tuple(self.strategy.register_signal_category):
            if signal.key_levels:
                for key, val in signal.key_levels.items():
                    print(key, val)
                    self.restore_variables[key] = getattr(self, key)
                    setattr(self, key, val)
                    print(getattr(self, key))
                print('spot_stop_loss_levels+++++++++', self.spot_short_stop_loss_levels)

    def process_post_entry(self):
        restore_variables_cp = self.restore_variables.copy()
        for key, val in restore_variables_cp.items():
            setattr(self, key, val)
            del self.restore_variables[key]

