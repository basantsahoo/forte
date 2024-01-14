from research.core_strategies.core_strategy import BaseStrategy
from research.strategies.signal_setup import get_startegy_args, get_signal_key
from helper.utils import get_option_strike


class DayBeforeExpiry(BaseStrategy):
    def __init__(self, market_book, **kwargs):
        print('DayBeforeExpiry+++++++++++++ init')
        args = get_startegy_args(**kwargs)
        #print(args)
        BaseStrategy.__init__(self, market_book=market_book, **args)


    def register_instrument(self, signal):
        print((signal.category, signal.indicator))
        print(get_signal_key('PCR_MINUS_1'))
        print(self.instr_to_trade)
        if (signal.category, signal.indicator) == get_signal_key(self.register_signal_category):
            self.derivative_instruments = []
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])
        print('register instr', self.derivative_instruments)
    def process_post_entry(self):
        self.derivative_instruments = []

