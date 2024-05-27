from strat_machine.core_strategies.signal_setup import get_trade_manager_args

class TradeManager:
    def __init__(self, market_book, id, **kwargs):
        args = get_trade_manager_args(**kwargs)
        self.initialize(market_book=market_book, id=id, **args)

    def initialize(self,
                 market_book=None,
                 id=None,
                 asset=None,
                 exit_time=[10],
                 exit_at=None,
                 carry_forward_days=0,
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
                 cover=0,
                 register_signal_category=None,
                 trade_controllers=[],
                 entry_switch={},
                 risk_limits=[],
                 trade_cut_off_time=60,
                 force_exit_ts=None,
                 trade_set_info={}
                 ):
        # print('entry_signal_queues====',entry_signal_queues)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(min(exit_time)) if id is None else id
        self.symbol = symbol
        self.order_type = order_type
        self.spot_instruments = spot_instruments if spot_instruments else []
        self.derivative_instruments = derivative_instruments if derivative_instruments else []
        self.exit_time = exit_time
        self.exit_at = exit_at
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal)  # Dont go past 4
        self.max_signal = max_signal
        # self.entry_criteria = entry_criteria
        self.signal_filters = signal_filters
        self.exit_criteria_list = exit_criteria_list
        self.spot_long_targets = [abs(x) if isinstance(x, (int, float)) else x for x in spot_long_targets]
        self.spot_long_stop_losses = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in
                                      spot_long_stop_losses]
        self.spot_short_targets = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in spot_short_targets]
        self.spot_short_stop_losses = [abs(x) if isinstance(x, (int, float)) else x for x in spot_short_stop_losses]
        self.spot_long_target_levels = spot_long_target_levels
        self.spot_long_stop_loss_levels = spot_long_stop_loss_levels
        self.spot_short_target_levels = spot_short_target_levels
        self.spot_short_stop_loss_levels = spot_short_stop_loss_levels

        side = get_broker_order_type(self.order_type)
        self.instr_targets = [side * abs(x) for x in instr_targets]
        self.instr_stop_losses = [-1 * side * abs(x) for x in instr_stop_losses]
        self.instr_to_trade = instr_to_trade
        self.register_signal_category = register_signal_category
        self.weekdays_allowed = weekdays_allowed
        self.activated = True
        self.is_aggregator = False
        self.params_repo = {}
        self.signal_params = {}  # self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.tradable_signals = {}
        self.minimum_quantity = 1
        self.trade_controllers = trade_controllers
        self.risk_limits = risk_limits
        self.trade_cut_off_time = trade_cut_off_time
        self.carry_forward_days = carry_forward_days
        self.force_exit_ts = force_exit_ts
        self.cover = cover  # 200 if self.derivative_instruments and self.order_type == 'SELL' else 0
        self.trade_set_info = trade_set_info
        print(trade_set_info)
        if (len(trade_set_info['spot_high_targets']) < self.triggers_per_signal) and (
                len(trade_set_info['spot_low_targets']) < self.triggers_per_signal) and (
                len(trade_set_info['trade_targets']) < self.triggers_per_signal):
            raise Exception("Triggers and targets of unequal size")
        # print('Add entry queue')
        self.entry_signal_pipeline = QNetwork(self, entry_signal_queues, entry_switch)
        # print('Add exit queue', exit_criteria_list)
        self.exit_signal_pipeline = QNetwork(self, exit_criteria_list)
        self.asset_book = market_book.get_asset_book(
            self.trade_set_info['asset']) if market_book is not None else None
        self.restore_variables = {}
        self.trade_manager = TradeManager(trade_set_info)
        # print('self.entry_signal_queues+++++++++++', self.entry_signal_pipeline)
        # print('self.exit_signal_queues+++++++++++', self.exit_signal_pipeline)
        """
        self.spot_targets = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.spot_stop_loss = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.instr_targets = [0.1, 0.2, 0.3, 0.4]
        self.instr_stop_loss = [-0.1, -0.2, -0.3, -0.4]
        """
        # self.prepare_targets()
        self.strategy_cache = Cache(cache_dir + 'strategy_cache')

    def initiate_signal_trades(self):
        print('initiate_signal_trades+++++++++++++++++')
        #print(self.spot_instruments)
        print(self.derivative_instruments)
        all_inst = self.spot_instruments + self.derivative_instruments
        for trade_inst in all_inst:
            print(trade_inst)
            trd_key = self.add_tradable_signal(trade_inst)
            curr_trade = self.tradable_signals[trd_key]
            curr_trade.trigger_entry()
            # legs = curr_trade.get_trade_legs()
            # Filter out triggers which doesn't contain data as a result of not enough time
            # triggers = [leg for leg in legs if leg]
            # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
            # self.trigger_entry(trade_inst, self.order_type, trd_key, legs)
        self.entry_signal_pipeline.flush_queues()
        self.process_post_entry()
