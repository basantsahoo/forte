from strat_machine.core_strategies.core_strategy import BaseStrategy
from strat_machine.strategies.signal_setup import get_startegy_args, get_signal_key
from helper.utils import get_option_strike


class OptionBuy(BaseStrategy):
    def __init__(self, market_book, **kwargs):
        print('OptionBuy+++++++++++++ init')
        args = get_startegy_args(**kwargs)
        #print(args)
        BaseStrategy.__init__(self, market_book=market_book, **args)


    def register_instrument(self, signal):
        if signal.key() == tuple(self.register_signal_category):
            self.derivative_instruments = []
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])
            print('register instr', self.derivative_instruments)
            print('signal.key_levels', signal.key_levels)
            if signal.key_levels:
                for key, val in signal.key_levels.items():
                    print(key, val)
                    self.restore_variables[key] = getattr(self, key)
                    setattr(self, key, val)
                    print(getattr(self, key))
                print('spot_stop_loss_levels+++++++++', self.spot_short_stop_loss_levels)
    def process_post_entry(self):
        self.derivative_instruments = []
        restore_variables_cp = self.restore_variables.copy()
        for key, val in restore_variables_cp.items():
            setattr(self, key, val)
            del self.restore_variables[key]

