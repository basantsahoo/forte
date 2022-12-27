from strategies.double_top_strategy import DoubleTopStrategy
from strategies.double_top_break_strategy import DoubleTopBreakStrategy
from strategies.trend_strategy import TrendStrategy

class PatternAggregator:
    def __init__(self, insight_book=None):
        self.insight_book = insight_book
        self.id = 'PATTERN_AGGR'
        self.is_aggregator = True
        self.individual_strategies = []
        #self.individual_strategies.append(DoubleTopStrategy(insight_book, 'TREND', "SELL", 10, 1, 'UP'))

        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 15, 1, 'UP'))
        #self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 10, 1, 'UP'))
        # ABOVE 2 TRIGGERED LOT OF TRADES WHY?

        """
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 15, 1, 'UP'))
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 20, 1, 'UP'))
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 30, 1, 'UP'))
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 45, 1, 'UP'))
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 60, 1, 'UP'))
        self.individual_strategies.append(DoubleTopBreakStrategy(insight_book, 'DT', "BUY", 90, 1, 'UP'))
        """
        """
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 15, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 20, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 30, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 45, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 60, 1, 'UP'))
        """
        """
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 10, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 15, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 20, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 30, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 45, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "BUY", 60, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 10, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 15, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 20, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 30, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 45, 1, 'UP'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DT', "SELL", 60, 1, 'UP'))

        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 10, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 15, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 20, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 30, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 45, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "BUY", 60, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 10, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 15, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 20, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 30, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 45, 1, 'DOWN'))
        self.individual_strategies.append(DoubleTopStrategy(insight_book, 'DB', "SELL", 60, 1, 'DOWN'))
        """
    def process_signal(self, pattern, pattern_match_idx):
        for strategy in self.individual_strategies:
            if strategy.price_pattern == pattern:
                strategy.process_signal(pattern_match_idx)


    def evaluate(self):
        for strategy in self.individual_strategies:
            strategy.evaluate()

    def get_signal_generator_from_id(self, strat_id):
        strategy_signal_generator = None
        for signal_generator in self.individual_strategies:
            if signal_generator.id == strat_id:
                strategy_signal_generator = signal_generator
                break
        return strategy_signal_generator