from trade_master.trade import Trade

class TradeSet:
    def __init__(self, trade_manager, ts_id):
        self.id = ts_id
        self.trade_manager = trade_manager
        self.trades = {}
        self.custom_features = {}
        self.exit_orders = []
        self.entry_orders = []
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
            #trade.set_controllers()
        return obj

    def trigger_entry(self):
        print('TradeSet trigger_entry +++++++++++++++++')
        for trade_id, trade in self.trades.items():
            trade.trigger_entry()
        self.process_entry_orders()

    def process_entry_orders(self):
        if self.entry_orders:
            self.trade_manager.strategy.trigger_entry(self.id, self.entry_orders)
            self.entry_orders = []


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

    def calculate_pnl(self):
        capital_list = []
        pnl_list = []
        for trade_id, trade in self.trades.items():
            capital, pnl, pnl_pct = trade.calculate_pnl()
            capital_list.append(capital)
            pnl_list.append(pnl)
        pnl_ratio = sum(pnl_list)/sum(capital_list)
        return sum(capital_list), sum(pnl_list), pnl_ratio

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

