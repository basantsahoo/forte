import numpy as np
from datetime import datetime
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.core_strategy import BaseStrategy
from research.strategies.core_option_strategy import BaseOptionStrategy
from research.strategies.strat_mixin import PatternMetricRecordMixin


class OptionSellStrategy(BaseOptionStrategy, PatternMetricRecordMixin):
    def test(self):
        pass
