from helper.utils import get_option_strike
class Instrument:
    def __init__(self,  market_book, asset,  kind, strike, expiry, money_ness, level):
        self.market_book = market_book
        self.kind = kind
        self.expiry = expiry
        self.strike = strike
        self.asset = asset
        self.money_ness = money_ness
        self.level = level
        if not self.is_spot():
            self.instr_code = str(strike) + "_" + kind
            self.full_code = asset + "_" + str(strike) + "_" + kind
        else:
            self.instr_code = kind
            self.full_code = asset

    def is_spot(self):
        return self.kind.upper() == 'SPOT'

    def is_option(self):
        return self.kind.upper() in ['CE', 'PE']

    def is_call(self):
        return self.kind.upper() in ['CE']

    def is_put(self):
        return self.kind.upper() in ['PE']

    def is_future(self):
        return self.kind.upper() == 'FUT'

    def life(self, last_tick_timestamp):
        return last_tick_timestamp-self.expiry

    @staticmethod
    def to_strike_kind(instr_code):
        if instr_code.upper() in ['SPOT', 'FUT']:
            inst_strike = 0
            kind = instr_code
        else:
            inst_strike = int(instr_code[:-3])
            kind = instr_code[-2::]
        return inst_strike, kind

    @classmethod
    def from_config(cls, market_book, config):
        asset = config['asset']
        kind = config['kind']
        expiry = config.get('expiry', '')
        money_ness = config.get('money_ness', '')
        level = config.get('level', 0)
        if kind.upper() != 'SPOT':
            asset_book = market_book.get_asset_book(asset)
            last_tick = asset_book.get_last_tick('SPOT')
            ltp = last_tick['close']
            strike = get_option_strike(ltp, money_ness, level, kind)
            instr_code = str(strike) + "_" + kind
            last_candle = asset_book.get_last_tick(instr_code)
            if not last_candle:
                print('last_candle not found for', instr_code)
                instr_code = asset_book.get_closest_instrument(instr_code)
                last_candle = asset_book.get_last_tick(instr_code)
                print('Now instr is ', instr_code)
        else:
            instr_code = kind
        strike, kind = Instrument.to_strike_kind(instr_code)
        return cls(market_book, asset, kind, strike, expiry, money_ness, level)

    @classmethod
    def from_store(cls, market_book, config):
        print('instrument from store config')
        asset = config['asset']
        kind = config['kind']
        expiry = config.get('expiry', '')
        strike = config.get('strike', 0)
        money_ness = config.get('money_ness', '')
        level = config.get('level', 0)
        return cls(market_book, asset, kind, strike, expiry, money_ness, level)

    def get_last_tick(self):
        asset_book = self.market_book.get_asset_book(self.asset)
        last_candle = asset_book.get_last_tick(self.instr_code)
        return last_candle

    def from_json(self, config):
        return self.__init__(**config)

    def to_json(self):
        jsn = None
        return jsn

    def to_dict(self):
        dct = {}
        for field in ['kind', 'expiry', 'strike', 'asset','money_ness', 'level', 'instr_code', 'full_code']:
            dct[field] = getattr(self, field)
        return dct

    def get_delta(self):
        itm_delta_levels = [0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 0.98, 1]
        otm_delta_levels = [0.4, 0.35, 0.3, 0.25, 0.2, 0.1, 0.02, 0.01]
        delta = 0
        if self.is_spot() or self.is_future():
            delta = 1
        elif self.is_option():
            direction_factor = 1 if self.is_call() else -1
            if self.money_ness == 'ATM':
                delta = 0.5
            elif self.money_ness == 'ITM':
                delta = itm_delta_levels[self.level-1] if self.level<= len(itm_delta_levels) else itm_delta_levels[-1]
            elif self.money_ness == 'OTM':
                delta = otm_delta_levels[self.level-1] if self.level<= len(otm_delta_levels) else otm_delta_levels[-1]
            delta = direction_factor * delta
        return delta