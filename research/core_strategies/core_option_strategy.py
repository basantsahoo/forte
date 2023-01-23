from research.core_strategies.t_core_strategy import BaseStrategy


class BaseOptionStrategy(BaseStrategy):
    def __init__(self, insight_book=None, **kwargs):
        kwargs['order_type'] = 'BUY'
        BaseStrategy.__init__(self, insight_book=insight_book, **kwargs)

    def test_base(self):
        print('test base', self.derivative_instruments)