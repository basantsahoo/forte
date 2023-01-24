from research.core_strategies.t_core_strategy import BaseStrategy
from helper.utils import  get_overlap


class DoubleTopStrategy(BaseStrategy):
    def __init__(self, insight_book, **kwargs):
        BaseStrategy.__init__(self, insight_book, **kwargs)



