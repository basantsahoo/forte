from trade_master.instrument import Instrument
class Leg:
    @classmethod
    def from_config(cls, leg_group, leg_id, leg_info):
        leg_info['instr_to_trade']['asset'] = leg_group.asset
        use_predicted_high_level = leg_info['instr_to_trade'].get('use_predicted_high_level', False)
        use_predicted_low_level = leg_info['instr_to_trade'].get('use_predicted_low_level', False)
        near_to_price = leg_group.trade.trade_set.trade_manager.predicted_high_level if use_predicted_high_level else leg_group.trade.trade_set.trade_manager.predicted_low_level if use_predicted_low_level else None
        leg_info['instr_to_trade']['near_to_price'] = near_to_price
        instr = Instrument.from_config(leg_group.trade.trade_set.trade_manager.market_book, leg_info['instr_to_trade'])
        last_candle = instr.get_last_tick()
        last_spot_candle = leg_group.trade.trade_set.trade_manager.get_last_tick(instr.asset, 'SPOT')
        entry_price = last_candle['close']
        exit_price = None
        spot_entry_price = last_spot_candle['close']
        spot_exit_price = None
        trigger_time = last_spot_candle['timestamp']
        quantity = leg_info['quantity']
        order_type = leg_info['order_type']
        return cls(leg_group, leg_id, instr, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time)

    def __init__(self, leg_group, leg_id, instrument, order_type, quantity, entry_price, exit_price, spot_entry_price, spot_exit_price, trigger_time, exit_type=None, exit_time=None):
        self.leg_group = leg_group
        self.leg_id = leg_id
        self.instrument = instrument
        self.order_type = order_type
        self.quantity = quantity
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.spot_entry_price = spot_entry_price
        self.spot_exit_price = spot_exit_price
        self.trigger_time = trigger_time
        self.exit_type = exit_type
        self.exit_time = exit_time
        #print('self.leg_group.force_exit_ts++++++++++++++++++', self.leg_group.force_exit_time)
    @classmethod
    def from_store(cls, leg_group, **kwargs):
        kwargs['instrument'] = Instrument.from_store(leg_group.trade.trade_set.trade_manager.market_book, kwargs['instrument'])
        return cls(leg_group,  **kwargs)

    def to_dict(self):
        dct = {}
        for field in ['leg_id', 'order_type', 'quantity', 'entry_price', 'exit_price', 'exit_type', 'spot_entry_price', 'spot_exit_price', 'trigger_time', 'exit_time']:
            dct[field] = getattr(self, field)
        dct['instrument'] = self.instrument.to_dict()
        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['order_type', 'quantity', 'spot_entry_price', 'spot_exit_price', 'exit_type']:
            dct[field] = getattr(self, field)
        dct['instrument'] = self.instrument.instr_code
        dct['asset'] = self.instrument.asset
        return dct

    def trigger_exit(self, exit_type=None):
        last_candle = self.instrument.get_last_tick()
        last_spot_candle = self.leg_group.trade.trade_set.trade_manager.get_last_tick(self.instrument.asset, 'SPOT')
        self.exit_type = exit_type
        self.exit_price = last_candle['close']
        self.exit_time = last_candle['timestamp']
        self.spot_exit_price = last_spot_candle['close']