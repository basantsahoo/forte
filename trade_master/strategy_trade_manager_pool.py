from trade_master.trade_manager import TradeManager


class StrategyTradeManagerPool:
    def __init__(self, market_book=None, strategy_manager=None):
        self.trade_managers = {}
        self.strategy_manager = strategy_manager
        self.market_book = market_book

    def add(self, trade_manager_info={}):
        #print('TradeManagerPool add_ trade manager=============', trade_manager_info)
        strategy = self.strategy_manager.get_deployed_strategy_from_id(trade_manager_info['strategy_id'])
        tm = TradeManager.from_config(self.market_book, strategy, **trade_manager_info)
        strategy.add_trade_manager(tm)
        self.trade_managers[trade_manager_info['strategy_id']] =  tm

    def set_up_strategies(self):
        for strategy in self.strategies.values():
            strategy.set_up()

    def get_tm_from_id(self, tm_id):
        return self.trade_managers[tm_id]
