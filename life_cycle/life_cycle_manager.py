from servers.server_settings import cache_dir
from diskcache import Cache


class LifeCycleManager:
    def __init__(self, symbol, mechanism="FIXED"):
        self.symbol = symbol
        self.mechanism = mechanism
        self.instruments = []
        self.combinations = []
        self.strategy_cache = Cache(cache_dir + 'strategy_cache')

    def add_instrument(self, instrument):
        self.instruments.append(instrument)

    def add_combinations(self, combination):
        self.combinations.append(combination)
