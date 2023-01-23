from research.core_strategies.core_option_strategy import BaseOptionStrategy
from research.strategies.signal_setup import get_signal_key


class CheapOptionBuy(BaseOptionStrategy):
    def __init__(self, insight_book, **kwargs):
        kwargs['entry_criteria'] = [{'OPTION_PRICE_DROP': []}]
        BaseOptionStrategy.__init__(self, insight_book, **kwargs)

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP'):
            self.derivative_instruments.append(signal['instrument'])

    def process_post_entry(self):
        self.derivative_instruments = []



