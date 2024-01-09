import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)


from datetime import datetime
from entities.trading_day import TradeDateTime, NearExpiryWeek
from truedata_ws.websocket.TD import TD
from config import get_expiry_date, default_symbols
import infrastructure.truedata.settings as td_settings
import helper.utils as helper_utils
from db.market_data import get_last_option_loaded_date, get_last_minute_data
from infrastructure.truedata.custom import OptionChainCustom
symbol = 'NIFTY'
trade_day = '2023-12-05'
start_str = trade_day + " 09:15:00"
end_str = trade_day + " 15:30:30"
start_ts = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
print(start_ts)
end_ts = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
end_time = end_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
start_time = start_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
t_day = TradeDateTime(trade_day)
expiry_week = NearExpiryWeek(t_day, symbol)
last_close = get_last_minute_data(symbol, expiry_week.last_expiry_end.date_string)
spot_price = last_close['close'].to_list()[-1]
expiry_dt = expiry_week.end_date.date_time  # get_expiry_date(trade_day, symbol)
print('expiry_dt', expiry_dt, spot_price)
expiry = expiry_dt.strftime('%y%m%d')
chain_length = {'NIFTY': 15, 'BANKNIFTY': 40}
TD_object = TD(td_settings.user_name, td_settings.pass_word, live_port=None, historical_api=True)

chain = OptionChainCustom(TD_object, helper_utils.get_oc_symbol(symbol), expiry_dt,
                          chain_length[helper_utils.get_oc_symbol(symbol)], spot_price, bid_ask=False,
                          market_open_post_hours=False)
for option_symbol in chain.option_symbols:
    print(option_symbol)

"""
hist_data = TD_object.historical_datasource.get_historic_data(option_symbol, start_time=start_time,
                                                              end_time=end_time, bar_size="1 min")
"""