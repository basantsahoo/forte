"""
from typing import Any, Dict, List, Optional, Tuple, Type, Union, overload

from haystack.nodes.base import BaseComponent
from haystack.nodes.prompt.invocation_layer import PromptModelInvocationLayer
from haystack.schema import Document, MultiLabel
from haystack.lazy_imports import LazyImport
"""
from typing import Any, Dict, List, Optional, Tuple, Type, Union, overload

class BaseEntity:
    name:str


class BaseSignal:
    name: str
    asset: str



class Signal:
    def __init__(self, asset, category, indicator, strength, signal_time, notice_time, info):
        self.asset = asset
        self.category: str = category
        self.indicator: str = indicator
        self.strength: int = strength
        self.signal_time: int = signal_time
        self.notice_time: int = notice_time
        self.info: Dict = info

"""
spot processor
data_interface
backtest_data_interface
state_cap_strategy
asset_book
common_fn
candle_pattern_detector
option_processor
trend_strategy
price_action_aggregator
double_top_strategy
price_action_aggregator
backtest_patterns

"""