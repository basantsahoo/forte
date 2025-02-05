from research.strategies.aggregators import CandleAggregator, PatternAggregator
#from research.strategies.double_top_break_strategy import DoubleTopBreakStrategy
#from research.strategies.state_cap_strategy import StateCapStrategy
#from research.strategies.opening_trend_bearish import OpeningBearishTrendStrategy
from live_algo.friday.friday_candle_first_30_mins import FridayCandleFirst30Buy,FridayCandleFirst30Sell #, #FridayCandleBuyFullDay
from research.strategies.cheap_option_buy import CheapOptionBuy
from research.strategies.option_sell import OptionSellStrategy
from live_algo.friday.friday_option_buy import FridayOptionBuy,FridayBelowVA
from live_algo.tuesday.tuesday_option_buy import TuesdayOptionBuy
from research.strategies.double_top_strategy import DoubleTopStrategy
from research.strategies.multi_pattern_q_strategy import MultiPatternQueueStrategy
from research.strategies.dt_buy_put_strategy import DTBuyPut
from research.technical_strategies.price_below_ema import PriceBreakEMADownward
from research.technical_strategies.price_reverse_ema_down import PriceReverseBreakDownEMA
from research.core_strategies.dummy_strategy import DummyStrategy
from research.weekly_strategies.weekly_sell import WeeklySell
