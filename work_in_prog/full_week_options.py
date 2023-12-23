import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
from config import get_expiry_date
from db.market_data import get_prev_week_minute_data_by_start_day, get_curr_week_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from dynamics.profile.market_profile import HistMarketProfileService
from datetime import datetime, date
from servers.server_settings import reports_dir
import pandas as pd
import numpy as np
import traceback
from config import default_symbols
from helper.utils import determine_day_open, determine_level_reach, get_overlap, get_percentile, candle_reversal_score
from dynamics.profile.utils import get_next_lowest_index, get_next_highest_index
from helper.time_utils import epoch_to_ordinal

from entities.trading_day import TradeDateTime, NearExpiryWeek
day = "2023-12-18"

trading_day = TradeDateTime(day)
print("********************************")

print("date_string==", trading_day.date_string)
print("date_time_string==", trading_day.date_time_string)
print("time_string==", trading_day.time_string)
print("date_time==", trading_day.date_time_string)
print("ordinal==", trading_day.ordinal)
print("weekday_iso==", trading_day.weekday_iso)
print("weekday==", trading_day.weekday)
print("weekday_name==", trading_day.weekday_name)
print("epoc_time==", trading_day.epoc_time)
print("epoc_minute==", trading_day.epoc_minute)
print("day_start_epoc==", trading_day.day_start_epoc)
print("market_start_epoc==", trading_day.market_start_epoc)
print("market_end_epoc==", trading_day.market_end_epoc)
print("month==", trading_day.month)
print("@@@@expiry week@@@@@")
expiry_week = NearExpiryWeek(trading_day, "BANKNIFTY")
print("start==", expiry_week.start_date.date_string)
print("end==", expiry_week.end_date.date_string)
print("month end==", expiry_week.moth_end_expiry)


from option_market.option_matrix import MultiDayOptionDataLoader, OptionMatrix
from db.market_data import get_trading_days_between_days
days = get_trading_days_between_days(expiry_week.start_date.date_string, expiry_week.end_date.date_string)
days_formatted = [day.strftime('%Y-%m-%d') for day in days]
print(days_formatted)

data_loader = MultiDayOptionDataLoader(asset="BANKNIFTY", trade_days=days_formatted[0:1])
option_matrix = OptionMatrix()

while data_loader.data_present:
    feed_list = data_loader.generate_next_feed()
    if feed_list:
        option_matrix.process_feed(feed_list)
