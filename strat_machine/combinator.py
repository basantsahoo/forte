from strat_machine.strategies.candle_pattern_strategy import CandlePatternStrategy
from strat_machine.strategies.double_top_strategy import DoubleTopStrategy

import talib
candle_names = talib.get_function_groups()['Pattern Recognition']


class StrategyCombinator:
    def __init__(self,
                 strategy_manager=None,
                 id=None,
                 combinations=[],
                 force_exit_time=None,
                 target=None,
                 stop_loss=None,
                 trade_duration = None
                 ):
        self.id = id
        self.strategy_manager = strategy_manager
        self.combinations = combinations
        self.strategies = {}
        self.force_exit_time = force_exit_time
        self.target = self.format_to_value(target)
        self.stop_loss = -1 * self.format_to_value(stop_loss)
        self.trade_duration = self.format_to_value(trade_duration)
        for strategy_id in combinations:
            strategy = self.strategy_manager.get_deployed_strategy_from_id(strategy_id)
            if strategy is not None:
                self.strategies[strategy_id] = strategy

    def set_up(self):
        trade_manager = list(self.strategies.values())[0].trade_manager
        self.force_exit_time = trade_manager.market_book.get_force_exit_ts(self.force_exit_time)

    def format_to_value(self, val):
        if isinstance(val, (int, float)):
            return abs(val)
        else:
            return float('inf')

    def on_minute_data_pre(self):
        #print('on_minute_data_pre+++++++++++++++++++++++++')
        self.monitor_existing_positions()

    def calculate_pnl(self):
        capital_list = []
        pnl_list = []
        for strategy_id, strategy in self.strategies.items():
            capital, pnl, pnl_pct = strategy.trade_manager.calculate_pnl()
            capital_list.append(capital)
            pnl_list.append(pnl)
        pnl_ratio = sum(pnl_list)/sum(capital_list)
        return sum(capital_list), sum(pnl_list), pnl_ratio

    def trigger_exit(self):
        for strategy_id, strategy in self.strategies.items():
            strategy.trade_manager.close_on_exit_signal()

    def monitor_existing_positions(self):
        trade_manager = list(self.strategies.values())[0].trade_manager
        asset = trade_manager.asset
        last_spot_candle = trade_manager.get_last_tick(asset, 'SPOT')
        if self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit()
        elif trade_manager.tradable_signals:
            capital, pnl, pnl_pct = self.calculate_pnl()
            trade_set = trade_manager.tradable_signals.values()[0]
            trade = trade_set.trades.values()[0]
            max_run_time = trade.trigger_time + self.trade_duration * 60 if self.force_exit_time is None else min(
                trade.trigger_time + self.trade_duration * 60, self.force_exit_time + 60)
            if last_spot_candle['timestamp'] >= max_run_time:
                self.trigger_exit()
            elif self.target and pnl_pct > self.target:
                self.trigger_exit()
            elif self.stop_loss and pnl_pct < self.stop_loss:
                self.trigger_exit()
