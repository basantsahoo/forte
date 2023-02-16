from research.core_strategies.core_strategy import BaseStrategy
from research.strategies.signal_setup import get_signal_key
from research.strategies.signal_setup import get_startegy_args

class CheapOptionBuy(BaseStrategy):
    def __init__(self, insight_book, **kwargs):
        args = get_startegy_args(**kwargs)
        BaseStrategy.__init__(self, insight_book, **args)

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP'):
            self.derivative_instruments.append(signal['instrument'])
            print('register ', self.derivative_instruments)

    def process_post_entry(self):
        self.derivative_instruments = []


class CheapOptionBuy_old(BaseStrategy):
    def __init__(self, insight_book, **kwargs):
        kwargs['entry_signal_queues'] = [{'signal_type': 'OPTION_PRICE_DROP', 'eval_criteria': [], 'flush_hist': True, 'id': 0, 'dependent_on': []}]
        BaseStrategy.__init__(self, insight_book, **kwargs)

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP'):
            self.derivative_instruments.append(signal['instrument'])

    def process_post_entry(self):
        self.derivative_instruments = []

