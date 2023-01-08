import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

from db.market_data import (get_all_days, get_daily_tick_data, get_daily_option_data_2)

class IntradayOptionProcessor:
    def __init__(self, symbol):
        self.symbol = symbol

symbol = 'NIFTY'
day = '2022-12-30'
option_list = get_daily_option_data_2(symbol, day)
option_list = option_list.to_dict('records')
print(option_list[0])