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


class Signal:
    def __init__(self,
                 asset: Optional[str],
                 category: Literal["PRICE_ACTION_PATTERN",
                                   "CANDLE_PATTERN",
                                   "TECHNICAL",
                                   "PRICE_SIGNAL",
                                   "OPTION_MARKET",
                                   "TIME_SIGNAL",
                                   "COMPOUND"],
                 indicator: str,
                 instrument: Optional[Literal['SPOT', "OPTION"]],
                 signal_time: Optional[int],
                 notice_time: Optional[int],
                 strength: Optional[Union[int, float]],
                 signal_info: Optional[Dict],
                 option_market_info: Optional[Dict] = {},
                 spot_market_info: Optional[Dict] = {},
                 key_levels: Optional[Dict] = {},
                 period: Optional[Literal["1min", "5min", "15min", "1hr", "daily", "weekly"]] = None,
                 name: Optional[str] = None,
                 ):
        self.name= name
        self.asset = asset
        self.category = category
        self.indicator = indicator
        self.instrument = instrument
        self.strength = strength
        self.signal_time = signal_time
        self.notice_time = notice_time
        self.signal_info = signal_info
        self.option_market_info = option_market_info
        self.spot_market_info = spot_market_info
        self.key_levels = key_levels
        self.instrument = instrument
        self.period = period

    def copy(self):
        return type(self)(self.asset, self.category, self.indicator, self.instrument, self.signal_time,
                          self.notice_time, self.strength, self.signal_info, self.option_market_info, self.spot_market_info, self.key_levels,
                          self.period,  self.name
                          )

    def is_option_signal(self):
        return self.instrument == "OPTION"

    def is_trend_signal(self):
        return self.indicator == "INDICATOR_TREND"


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