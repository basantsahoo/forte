class StrategyManager:
    def __init__(self, market_book=None, record_metric=False):
        self.strategies = {}
        self.record_metric = record_metric
        self.run_aggregator = False
        self.market_book = market_book
        self.process_signal_switch = True

    def add_strategy(self, strategy_class, strategy_kwarg={}):
        print('StrategyManager add_strategy=============', strategy_class)
        strategy = strategy_class(self.market_book, **strategy_kwarg)
        if strategy.id not in self.strategies.keys():
            if strategy.is_aggregator:
                self.run_aggregator = True
            strategy.record_metric = self.record_metric
            self.strategies[strategy.id] = strategy
        else:
            raise Exception('Duplicate Strategy id found')

    def remove_strategy(self, strategy_to_remove):
        print('remove_strategy')
        del self.strategies[strategy_to_remove.id]

    def set_up_strategies(self):
        for strategy in self.strategies.values():
            strategy.set_up()

    def get_deployed_strategy_from_id(self, strat_id):
        print('get_deployed_strategy_from_id++++++++++++++++++', strat_id)
        strategy_signal_generator = None
        for strategy in self.strategies.values():
            print(strategy.id)
            if strategy.is_aggregator:
                strategy_signal_generator = strategy.get_signal_generator_from_id(strat_id)
            elif strategy.id == strat_id:
                    strategy_signal_generator = strategy
            if strategy_signal_generator is not None:
                break
            print(strategy_signal_generator)
        return strategy_signal_generator
    """
    def get_strategies_by_symbol(self, symbol):
        return [strategy for strategy in self.strategies if strategy.asset_book.asset == symbol]
    """
    def on_minute_data_pre(self, asset):
        if self.process_signal_switch:
            #strategies = self.get_strategies_by_symbol(asset)
            for strategy in self.strategies.values():
                strategy.on_minute_data_pre()

    def process_custom_signal(self):
        if self.process_signal_switch:
            for strategy in self.strategies.values():
                strategy.process_custom_signal()

    def on_minute_data_post(self, asset):
        if self.process_signal_switch:
            #strategies = self.get_strategies_by_symbol(asset)
            for strategy in self.strategies.values():
                #strategy.on_minute_data_pre()
                strategy.on_minute_data_post()

    def market_close_for_day(self):
        for strategy in self.strategies.values():
            strategy.market_close_for_day()

    def register_signal(self, signal):
        if self.process_signal_switch:
            for strategy in self.strategies.values():
                strategy.register_signal(signal)

