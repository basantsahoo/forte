class Instrument:
    def __init__(self,  market_book, asset, money_ness, level, kind, expiry):
        self.market_book = market_book
        self.money_ness = money_ness
        self.level = level
        self.kind = kind
        self.expiry = expiry
        self.strike = 0
        self.asset = asset

    def is_spot(self):
        return self.kind.to_upper() == 'SPOT'

    def is_option(self):
        return self.kind.to_upper() in ['CE', 'PE']

    def is_future(self):
        return self.kind.to_upper() == 'FUT'

    def life(self, last_tick_timestamp):
        return last_tick_timestamp-self.expiry

    def from_config(self, market_book, config):
        return self.__init__(market_book = market_book, **config)

    def from_json(self, config):
        return self.__init__(**config)

    def to_json(self):
        jsn = None
        return jsn

