from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from helper.utils import inst_is_option
from trade_master.trade_set import TradeSet
from servers.server_settings import cache_dir
from diskcache import Cache


class TradeManager:
    """
        self.trade_manager_info = trade_manager_info
        if (len(trade_manager_info['spot_high_targets']) < self.triggers_per_signal) and (len(trade_manager_info['spot_low_targets']) < self.triggers_per_signal) and (len(trade_manager_info['trade_targets']) < self.triggers_per_signal) and len(trade_manager_info['leg_group_exits']['targets']) < self.triggers_per_signal:
            raise Exception("Triggers and targets of unequal size")
    """
    def market_close_for_day(self):
        #print('trade manager market close for day')

        carry_trade_sets = {}
        params_repo = {}
        for (sig_key, trade_set) in self.tradable_signals.items():
            if trade_set.to_carry_forward():
                carry_trade_sets[trade_set.id] = []
                for trade in trade_set.trades.values():
                    if trade.to_carry_forward():
                        carry_trade_sets[trade_set.id].append(trade.to_dict())
                        params_repo[(sig_key, trade.trd_idx)] = self.params_repo[(sig_key, trade.trd_idx)]
        #print(carry_trade_sets)
        self.carry_over_trade_cache.set(self.strategy_id, carry_trade_sets)
        self.carry_over_trade_cache.set('params_repo_' + self.strategy_id, params_repo)
        #print('EOD ===== carry_trades for', self.strategy_id, "=========", self.carry_over_trade_cache.get(self.strategy_id, {}))

    def load_from_cache(self):
        carry_trades = self.carry_over_trade_cache.get(self.strategy_id, {})
        #print('carry_trades===', carry_trades)

        params_repo = self.carry_over_trade_cache.get('params_repo_' + self.strategy_id, {})
        self.load_carry_trades(carry_trades, params_repo)
        self.carry_over_trade_cache.delete(self.strategy_id)
        self.carry_over_trade_cache.delete('params_repo_' + self.strategy_id)


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

    def load_carry_trades(self, carry_trades, params_repo):
        for sig_key, trade_set_info in carry_trades.items():
            #print(sig_key, trade_set_info)
            #print(list(trade_set_info[0]['leg_groups'][0]['legs'].values())[0]['trigger_time'])
            if list(trade_set_info[0]['leg_groups'][0]['legs'].values())[0]['trigger_time'] < self.market_book.last_tick_timestamp:
                self.tradable_signals[sig_key] = TradeSet.from_store(self, sig_key, trade_set_info)
                for trade in self.tradable_signals[sig_key].trades.values():
                    self.params_repo[(sig_key, trade.trd_idx)] = params_repo[(sig_key, trade.trd_idx)]


    def __init__(self,
                 market_book=None,
                 strategy=None,
                 strategy_id=None,
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
                 predicted_high_level=None,
                 predicted_low_level=None,
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
        self.strategy_id = strategy_id
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
        self.predicted_high_level = predicted_high_level
        self.predicted_low_level = predicted_low_level
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
        #self.carry_over_trade_cache = Cache(cache_dir + 'carry_over_trade_cache')
        self.carry_over_trade_cache = Cache(cache_dir + "/P_" + str(self.market_book.process_id) + "/" + 'carry_over_trade_cache')
        self.params_repo = {}

    def initiate_signal_trades(self):
        print('TradeManager initiate_signal_trades+++++++++++++++++')
        #sig_key = self.market_book.trade_day + "_" + str(self.signal_count + 1)
        sig_key = self.strategy_id + "_" + self.asset + "_" + self.market_book.trade_day + "_" + str(self.signal_count + 1)
        self.signal_count += 1
        self.tradable_signals[sig_key] = TradeSet.from_config(self, sig_key)
        return sig_key

    def trigger_entry(self, sig_key):
        print('TradeManager trigger_entry +++++++++++++++++')
        trade_set = self.tradable_signals[sig_key]
        trade_set.trigger_entry()

    def monitor_existing_positions_close(self):
        for trade_set_id, trade_set in self.tradable_signals.items():
            trade_set.monitor_existing_positions_close()

    def monitor_existing_positions_target(self):
        #print('trade manager, monitor_existing_positions_target =============')
        for trade_set_id, trade_set in self.tradable_signals.items():
            trade_set.monitor_existing_positions_target()

    def trigger_re_entry(self):
        #print('trade manager, monitor_existing_positions_target =============')
        for trade_set_id, trade_set in self.tradable_signals.items():
            trade_set.trigger_re_entry()

    def close_on_exit_signal(self):
        for trade_set_id, trade_set in self.tradable_signals.items():
            if not trade_set.complete():
                trade_set.close_on_exit_signal()

    def calculate_pnl(self):
        capital_list = []
        pnl_list = []
        for trade_set_id, trade_set in self.tradable_signals.items():
            capital, pnl, pnl_pct = trade_set.calculate_pnl()
            capital_list.append(capital)
            pnl_list.append(pnl)
        pnl_ratio = sum(pnl_list)/sum(capital_list)
        return sum(capital_list), sum(pnl_list), pnl_ratio

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
        print('trade manager register_signal+++++++++++++++++++++++++++++++++')
        if signal.key() == tuple(self.strategy.register_signal_category):
            self.strategy.execute_trades = True
            if signal.key_levels:
                for key, val in signal.key_levels.items():
                    print(key, val)
                    self.restore_variables[key] = getattr(self, key)
                    setattr(self, key, val)
                    print(getattr(self, key))
                #print('spot_stop_loss_levels+++++++++', self.spot_short_stop_loss_levels)


    def process_post_entry(self):
        restore_variables_cp = self.restore_variables.copy()
        for key, val in restore_variables_cp.items():
            setattr(self, key, val)
            del self.restore_variables[key]

