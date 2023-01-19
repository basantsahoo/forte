from research.strategies.core_option_strategy import BaseOptionStrategy
from research.strategies.signal_setup import get_signal_key


class CheapOptionBuy(BaseOptionStrategy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY", order_type="BUY",spot_instruments=[], exit_time=60,  max_signal = 10000000, instr_targets=[0.1,0.2, 0.3, 0.5], instr_stop_losses=[0.5,0.5, 0.5,0.5], signal_filter_conditions=[], weekdays_allowed=[]):
        entry_criteria = [{'OPTION_PRICE_DROP': []}]
        BaseOptionStrategy.__init__(self, insight_book, id=id, order_type=order_type, spot_instruments=spot_instruments, exit_time=exit_time, max_signal=max_signal, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses, signal_filter_conditions=signal_filter_conditions, weekdays_allowed=weekdays_allowed, entry_criteria = entry_criteria)

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP'):
            self.derivative_instruments.append(signal['instrument'])

    def process_post_entry(self):
        self.derivative_instruments = []



