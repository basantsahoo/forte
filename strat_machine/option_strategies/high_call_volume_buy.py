from strat_machine.core_strategies.core_strategy import BaseStrategy
from strat_machine.strategies.signal_setup import get_startegy_args, get_signal_key_to_be_deleted
from helper.utils import get_option_strike


class HighCallVolumeBuy(BaseStrategy):
    def __init__(self, market_book, **kwargs):
        print('HighCallVolumeBuy+++++++++++++ init')
        args = get_startegy_args(**kwargs)
        #print(args)
        BaseStrategy.__init__(self, market_book=market_book, **args)


    def register_instrument(self, signal):
        if (signal.category, signal.indicator) == get_signal_key_to_be_deleted('BULLISH_MOMENTUM'):
            self.derivative_instruments = []
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])
        print('register instr', self.derivative_instruments)
    def process_post_entry(self):
        self.derivative_instruments = []

