known_spot_instruments = ['SPOT']
market_view_dict = {'SPOT_BUY': 'LONG',
                    'SPOT_SELL': 'SHORT',
                    'CE_BUY': 'LONG',
                    'CE_SELL': 'SHORT',
                    'PE_BUY': 'SHORT',
                    'PE_SELL': 'LONG'}


class DummyStrategy:
    def __init__(self,
                 insight_book=None,
                 **kwargs
    ):
        self.id = 'DUMMY'
        self.insight_book = insight_book
        self.time_intervals = [30,60]
        self.signal = {'category': 'STRAT', 'indicator': 'EMA_BREAK_DOWN_5_ENTRY', 'strength': 1, 'signal_time': None, 'notice_time': None, 'info': {}}
        self.counter = 0
        self.is_aggregator = False

    def get_last_tick(self, instr='SPOT'):
        last_candle = self.insight_book.spot_processor.last_tick
        return last_candle


    def on_minute_data_pre(self):
        if self.counter in self.time_intervals:
            last_candle = self.get_last_tick()
            signal = self.signal.copy()
            signal['signal_time'] = last_candle['timestamp']
            signal['notice_time'] = last_candle['timestamp']
            signal['info'] = last_candle
            self.insight_book.pattern_signal(signal)
        self.counter += 1


    def register_signal(self, signal):
        pass

    def on_minute_data_post(self):
        pass

    def on_tick_data(self):
        pass

    def set_up(self):
        pass

    def process_custom_signal(self):
        pass
