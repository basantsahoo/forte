from strat_machine.combinator import StrategyCombinator
class StrategyManager:
    def __init__(self, market_book=None, record_metric=False):
        self.strategies = {}
        self.combinators = {}
        self.record_metric = record_metric
        self.run_aggregator = False
        self.market_book = market_book
        self.process_signal_switch = True

    def add_strategy(self, strategy_class, strategy_kwarg={}):
        #print('StrategyManager add_strategy=============', strategy_class)
        strategy = strategy_class(self.market_book, **strategy_kwarg)
        if strategy.id not in self.strategies.keys():
            if strategy.is_aggregator:
                self.run_aggregator = True
            strategy.record_metric = self.record_metric
            self.strategies[strategy.id] = strategy
        else:
            raise Exception('Duplicate Strategy id found')

    def clean_up_strategies(self):
        for strategy_id in list(self.strategies.keys()):
            strategy = self.strategies[strategy_id]
            if strategy.trade_manager is None:
                del self.strategies[strategy_id]

    def clean_up_combinators(self):
        for combinator_id in list(self.combinators.keys()):
            combinator = self.combinators[combinator_id]
            if len(combinator.combinations) != len(list(combinator.strategies.keys())):
                for strategy in combinator.strategies.values():
                    strategy.trade_manager = None
                del self.combinators[combinator_id]

    def add_combinator(self, combinator_kwars={}):
        print('StrategyManager add_combinator=============')
        combinator = StrategyCombinator(self, **combinator_kwars)
        if combinator.id not in self.combinators.keys():
            self.combinators[combinator.id] = combinator
        else:
            raise Exception('Duplicate combinator id found')

    def remove_strategy(self, strategy_to_remove):
        print('remove_strategy')
        del self.strategies[strategy_to_remove.id]

    def remove_combinator(self, combinator_to_remove):
        print('remove combinator')
        del self.combinators[combinator_to_remove.id]

    def set_up_strategies(self):
        for strategy in self.strategies.values():
            strategy.set_up()
        for combinator in self.combinators.values():
            combinator.set_up()

    def get_deployed_strategy_from_id(self, strat_id):
        #print('get_deployed_strategy_from_id++++++++++++++++++', strat_id)
        strategy_signal_generator = None
        for strategy in self.strategies.values():
            #print(strategy.id)
            if strategy.is_aggregator:
                strategy_signal_generator = strategy.get_signal_generator_from_id(strat_id)
            elif strategy.id == strat_id:
                    strategy_signal_generator = strategy
            if strategy_signal_generator is not None:
                break
            #print(strategy_signal_generator)
        return strategy_signal_generator

    def get_deployed_combinator_from_id(self, combinator_id):
        #print('get_deployed_strategy_from_id++++++++++++++++++', strat_id)
        combinator_obj = None
        for combinator in self.combinators.values():
            #print(strategy.id)
            if combinator.id == combinator_id:
                    combinator_obj = combinator
            if combinator_obj is not None:
                break
            #print(strategy_signal_generator)
        return combinator_obj

    """
    def get_strategies_by_symbol(self, symbol):
        return [strategy for strategy in self.strategies if strategy.asset_book.asset == symbol]
    """
    def on_minute_data_pre(self, asset):
        if self.process_signal_switch:
            #strategies = self.get_strategies_by_symbol(asset)
            for strategy in self.strategies.values():
                if strategy.asset == asset:
                    strategy.on_minute_data_pre()
            for combinator in self.combinators.values():
                combinator.on_minute_data_pre()

    def process_custom_signal(self):
        if self.process_signal_switch:
            for strategy in self.strategies.values():
                strategy.process_custom_signal()

    def on_minute_data_post(self, asset):
        if self.process_signal_switch:
            #strategies = self.get_strategies_by_symbol(asset)
            for strategy in self.strategies.values():
                if strategy.asset == asset:
                    #strategy.on_minute_data_pre()
                    strategy.on_minute_data_post()

    def on_option_tick(self, asset, tick_time):
        if self.process_signal_switch:
            #print('strategy manager on_option_tick')
            #strategies = self.get_strategies_by_symbol(asset)
            for strategy in self.strategies.values():
                if strategy.asset == asset:
                    #strategy.on_minute_data_pre()
                    strategy.on_tick_data(tick_time)

    def market_close_for_day(self):
        for strategy in self.strategies.values():
            strategy.market_close_for_day()

    def register_signal(self, signal):
        if self.process_signal_switch:
            for strategy in self.strategies.values():
                strategy.register_signal(signal)

