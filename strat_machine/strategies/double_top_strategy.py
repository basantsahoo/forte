from strat_machine.core_strategies.core_strategy import BaseStrategy
from helper.utils import  get_overlap


class DoubleTopStrategy(BaseStrategy):
    def __init__(self, market_book, **kwargs):
        BaseStrategy.__init__(self, market_book, **kwargs)



