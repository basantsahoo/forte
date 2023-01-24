from research.core_strategies.core_strategy import BaseStrategy
from research.strategies.signal_setup import get_signal_key
from helper.utils import get_option_strike


class DTBuyPut(BaseStrategy):
    def __init__(self, insight_book, **kwargs):
        BaseStrategy.__init__(self, insight_book=insight_book, **kwargs)

    def register_instrument(self, signal):

        if (signal['category'], signal['indicator']) == get_signal_key('DT'):
            #print('instrument register')
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            atm_strike = round(ltp/100)*100
            for instr in self.instr_to_trade:
                # e.g instr = ['OTM', 1, 'PE']
                strike = get_option_strike(ltp, instr[0],instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])

    def process_post_entry(self):
        self.derivative_instruments = []