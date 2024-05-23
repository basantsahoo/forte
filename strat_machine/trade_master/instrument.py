class Instrument:
    def __init__(self, category, money_ness, level, kind, expiry):
        self.category = category
        self.money_ness = money_ness
        self.level = level
        self.kind = kind
        self.expiry = expiry
        self.strike = 0

    def is_spot(self):
        return self.category.to_upper() == 'SPOT'

    def is_option(self):
        return self.kind.to_upper() in ['CE', 'PE']

    def life(self, last_tick_timestamp):
        return last_tick_timestamp-self.expiry
