from strat_machine.core_strategies.core_strategy import BaseStrategy
from strat_machine.core_strategies.signal_setup import get_startegy_args
from helper.utils import get_option_strike


class DoubleTopStrategy(BaseStrategy):
    def __init__(self, market_book, **kwargs):
        args = get_startegy_args(**kwargs)
        BaseStrategy.__init__(self, market_book=market_book, **args)


