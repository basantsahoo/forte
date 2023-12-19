"""
from typing import Any, Dict, List, Optional, Tuple, Type, Union, overload

from haystack.nodes.base import BaseComponent
from haystack.nodes.prompt.invocation_layer import PromptModelInvocationLayer
from haystack.schema import Document, MultiLabel
from haystack.lazy_imports import LazyImport
"""
from typing import Any, Dict, List, Optional, Tuple, Type, Union, overload
from typing import Literal

class BaseEntity:
    name:str


class BaseSignal:
    name: Optional[str]
    asset: str
    category: Literal["PRICE_ACTION_PATTERN", "TECHNICAL", "PRICE"]
    period: Literal["5min", "15min", "1hr", "daily", "weekly"]
    indicator: str
    instrument: Literal["SPOT", "OPTION"]
    contract: Optional[str]
    signal_time: int
    notice_time: int
    strength: Optional[Union[int, float]]
    signal:Optional[str]
    info: Optional[Dict]

    def is_option_signal(self):
        return self.instrument == "OPTION"

    def is_trend_signal(self):
        return self.indicator == "INDICATOR_TREND"


class Signal(BaseSignal):
    def __init__(self,
                 asset:str,
                 category: Literal["PRICE_ACTION_PATTERN", "TECHNICAL", "PRICE"],
                 indicator: str,
                 instrument: Literal['SPOT', "OPTION"],
                 signal_time: int,
                 notice_time: int,
                 strength: Optional[Union[int, float]],
                 info: Optional[Dict],
                 signal: Optional[str] = None,
                 contract: Optional[str] = None,
                 period: Optional[Literal["5min", "15min", "1hr", "daily", "weekly"]] = None,
                 name: Optional[str] = None,
                 ):
        self.name= name
        self.asset = asset
        self.category = category
        self.indicator = indicator
        self.instrument = instrument
        self.strength = strength
        self.signal = signal
        self.signal_time = signal_time
        self.notice_time = notice_time
        self.info = info
        self.instrument = instrument
        self.period = period
        self.contract = contract



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