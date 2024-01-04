import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent.parent)
sys.path.insert(1, project_path)
from entities.trading_day import TradeDateTime, NearExpiryWeek
from helper.utils import get_nse_index_symbol
import numpy as np

import time
from dynamics.profile.market_profile import HistMarketProfileService
import numpy as np
from itertools import compress
from config import exclued_days
import pandas as pd
import sqlite3
import os
import datetime
from dateutil.relativedelta import relativedelta
from db.market_data import get_daily_tick_data
from db.db_engine import get_db_engine
from config import default_symbols
import helper.utils as helper_utils
"""
# for connecting to fyers for historical data
from data_feed.historical_data import HistoricalDataFetcher
hist_fetcher = HistoricalDataFetcher()
"""

 #['NSE:NIFTY50-INDEX']
symbol = 'BANKNIFTY'
def get_avg_volume_data_o(symbol):
    engine = get_db_engine()
    conn = engine.connect()
    qry = """
    SELECT  date, CONCAT(strike,'_', kind) AS instrument, round(AVG(volume)) as avg_volume  from option_data od 
    where underlying = '{0}' and date >= '2023-09-01'
    group by CONCAT(strike,'_', kind)  , date
    """.format(get_nse_index_symbol(symbol))
    df = pd.read_sql_query(qry, con=conn)
    df.to_csv(get_nse_index_symbol(symbol) + '_avg_volume.csv')
    return df

def get_avg_volume_data(symbol):
    df = pd.read_csv(get_nse_index_symbol(symbol) + '_avg_volume.csv')
    return df

def date_diff(td_1, td_2):
    return (td_2.end_date.date_time - td_1.date_time).days

df = get_avg_volume_data_o(symbol)
df['kind'] = df['instrument'].apply(lambda x: x[-2::])
aggregate_df_1 = df.groupby(['date', 'kind'])['avg_volume'].aggregate('sum').reset_index()
aggregate_df_1['expiry_date'] = aggregate_df_1['date'].apply(lambda x: NearExpiryWeek(TradeDateTime(x), symbol))
aggregate_df_1['date'] = aggregate_df_1['date'].apply(lambda x: TradeDateTime(x))
aggregate_df_1['days_to_expiry'] = aggregate_df_1.apply(lambda x: date_diff(x['date'], x['expiry_date']), axis=1)
aggregate_df_1['month_end_expiry'] = aggregate_df_1['expiry_date'].apply(lambda x: int(x.moth_end_expiry))
df2 = aggregate_df_1[['kind', 'avg_volume', 'days_to_expiry', 'month_end_expiry']]

aggregate_df = df2.groupby(['kind', 'days_to_expiry', 'month_end_expiry'])['avg_volume'].aggregate('mean')
aggregate_df = aggregate_df.reset_index()
aggregate_df['avg_volume'] = aggregate_df['avg_volume'].apply(lambda x: np.round(x, 0))
print(aggregate_df.to_dict('records'))


