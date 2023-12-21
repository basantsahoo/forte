import time
import pandas as pd
import traceback
from datetime import datetime
from sqlalchemy.types import VARCHAR, DATE
import logging

from dateutil.relativedelta import relativedelta
from truedata_ws.websocket.TD_hist import HistoricalREST , cache_symbol_id
from truedata_ws.websocket.TD import TD
from config import get_expiry_date, default_symbols
import infrastructure.truedata.settings as td_settings
import helper.utils as helper_utils

from infrastructure.truedata.custom import OptionChainCustom
from db.db_engine import get_db_engine

log_format = "(%(asctime)s) %(levelname)s :: %(message)s (PID:%(process)d Thread:%(thread)d)"
log_formatter = logging.Formatter(log_format)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.WARNING)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger('hist_downloader')
logger.addHandler(log_handler)
logger.setLevel(log_handler.level)
logger.debug("Logger ready...")


def get_last_option_loaded_date(symbol):
    last_date = None
    engine = get_db_engine()
    conn = engine.connect()
    try:
        qry = "select max(date) as last_date from option_data where underlying = '{}'".format(symbol)
        print(qry)
        df = pd.read_sql_query(qry, con=conn)
        print(df)
        last_date = df['last_date'].to_list()[0] if df['last_date'].to_list() else None
    except:
        pass
    conn.close()
    return last_date



#hist_fetcher = HistoricalREST(td_settings.user_name, td_settings.pass_word, td_settings.hist_url, None, logger)

def get_option_details(option_symbol, inst_symbol, expiry):

    inst_oc_symbol = helper_utils.get_oc_symbol(inst_symbol)
    #opt_type = option_symbol[-2:]
    return {'strike': option_symbol[len(inst_oc_symbol)+len(expiry):-2], 'kind': option_symbol[-2:]}

def download(trade_days=[], symbols=[]):
    print("====starting download====")
    if len(symbols) == 0:
        symbols = [helper_utils.get_nse_index_symbol(symbol) for symbol in default_symbols]
    TD_object = TD(td_settings.user_name, td_settings.pass_word, live_port=None, historical_api=True)
    chain_length = {'NIFTY': 10, 'BANKNIFTY': 30}
    engine = get_db_engine()
    conn = engine.connect()

    for symbol in symbols:
        tmp_trade_days = trade_days
        if len(tmp_trade_days) == 0:
            last_date = get_last_option_loaded_date(helper_utils.get_nse_index_symbol(symbol))
            print('last_date=================', last_date)
            if last_date is None:
                last_date = datetime(2022, 9, 18).date()
            # print(last_date)
            curr_date = datetime.now().date()
            delta = curr_date - last_date
            # print(delta.days)
            for d in range(1, delta.days + 1):
                day_from_now = last_date + relativedelta(days=d)
                date_formated = day_from_now.strftime("%Y-%m-%d")
                tmp_trade_days.append(date_formated)
            print(tmp_trade_days)
        IDX = 0
        for idx in range(len(tmp_trade_days)):
            trade_day = tmp_trade_days[idx]
            print(trade_day, "+++++++++++++++++++++++++++++++++++++++")
            start_str = trade_day + " 09:15:00"
            end_str = trade_day + " 15:30:30"
            start_ts = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end_ts = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            end_time = end_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
            start_time = start_ts.strftime('%y%m%dT%H:%M:%S')  # This is the request format
            """
            hist_data = hist_fetcher.get_historic_data(helper_utils.get_td_index_symbol(symbol), start_time=start_time,
                                                       end_time=end_time, bar_size="eod")
            future_price = hist_data[0]['o']
            """
            #print(len(tmp_trade_days)-idx)
            #print(TD_object.historical_datasource.get_historic_data(helper_utils.get_td_index_symbol(symbol), start_time=start_time, end_time=end_time,  bar_size="eod"))
            #print(TD_object.get_n_historical_bars(helper_utils.get_td_index_symbol(symbol), no_of_bars=len(tmp_trade_days)-idx, bar_size="eod"))
            #future_price = TD_object.get_n_historical_bars(helper_utils.get_td_index_symbol(symbol), no_of_bars=len(tmp_trade_days)-idx, bar_size="eod")[-1]['o']
            spot_daily_bar = TD_object.historical_datasource.get_historic_data(helper_utils.get_td_index_symbol(symbol), start_time=start_time,
                                                       end_time=end_time,  bar_size="eod")
            if spot_daily_bar:
                spot_price = spot_daily_bar[0]['o']
                print(spot_price)
                expiry_dt = get_expiry_date(trade_day, symbol)
                print('expiry_dt', expiry_dt)
                expiry = expiry_dt.strftime('%y%m%d')

                chain = OptionChainCustom(TD_object, helper_utils.get_oc_symbol(symbol), expiry_dt, chain_length[helper_utils.get_oc_symbol(symbol)], spot_price, bid_ask=False, market_open_post_hours=False)
                for option_symbol in chain.option_symbols:
                    print(option_symbol)
                    hist_data = TD_object.historical_datasource.get_historic_data(option_symbol, start_time=start_time,
                                                           end_time=end_time,  bar_size="1 min")
                    try:
                        converted = []
                        option_details = get_option_details(option_symbol, symbol, expiry)
                        for minute_candle in hist_data:
                            tick_date_time = minute_candle['time']
                            if not int(tick_date_time.strftime("%H")) > 15:
                                time_string = tick_date_time.strftime("%H:%M:%S")
                                tmp = {
                                    'date': trade_day,
                                    'time_string': time_string,

                                    'timestamp': int(
                                        time.mktime(time.strptime(tick_date_time.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"))),
                                    'underlying': helper_utils.get_nse_index_symbol(symbol),
                                    'option_symbol': option_symbol,
                                    'expiry_date': expiry_dt,
                                    'strike': option_details['strike'],
                                    'kind': option_details['kind'],
                                    'open': minute_candle['o'],
                                    'high': minute_candle['h'],
                                    'low': minute_candle['l'],
                                    'close': minute_candle['c'],
                                    'volume': minute_candle['v'],
                                    'oi': minute_candle['oi']
                                }
                                #print(tmp)
                                converted.append(tmp)
                        df = pd.DataFrame(converted)
                        df.to_sql('option_data', conn, if_exists="append", index=False, method="multi", chunksize=500, dtype={"option_symbol": VARCHAR(length=40), "date":DATE, "underlying": VARCHAR(length=30)})
                    except Exception as e:
                        print(traceback.format_exc())
                        print(trade_day, symbol)
                        print(e)

                time.sleep(0.3)
    """
    try:
        conn.execute("ALTER TABLE option_data ADD PRIMARY KEY (option_symbol, timestamp);")
        conn.execute("CREATE INDEX sym_dt ON option_data (date, underlying)")
        conn.execute("CREATE INDEX opt_sym_dt ON option_data (date, option_symbol)")
        conn.execute("CREATE INDEX opt_ts ON option_data (option_symbol)")
    except Exception as e:
        print(e)
    """
    conn.close()


def run2():
    print('run 2')
    download()

#download()