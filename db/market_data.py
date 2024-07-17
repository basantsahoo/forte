import pandas as pd
from db.db_engine import get_db_engine
from collections import OrderedDict
import pytz
import json
from datetime import datetime
import calendar
import numpy as np
engine = get_db_engine()
import helper.utils as helper_utils
from config import exclued_days


def get_pending_key_level_days(symbol):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    pending_dates = []
    conn = engine.connect()
    try:
        qry = """select distinct date as pending from minute_data where symbol = '{0}' 
                and date not in (
                    select date  from key_levels where symbol = '{1}'
                ) order by date asc""".format(symbol, symbol)
        df = pd.read_sql_query(qry, con=conn)
        pending_dates = df['pending'].to_list() if df['pending'].to_list() else []
    except:
        pass
    #print(pending_dates)
    conn.close()
    return pending_dates


def get_prev_day_key_levels(symbol, trade_day):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    yesterday = [trade_day, json.dumps([]), json.dumps([])]
    stmt = """select date,supports,resistances
            from key_levels
            where symbol = '{0}' and date = 
            (select  max(date) as yesterday from key_levels where symbol = '{0}'  and date < date('{1}'))"""
    conn = engine.connect()
    try:
        rs = conn.execute(stmt.format(symbol, trade_day))
        yesterday = list(rs)[0]
    except:
        pass
    conn.close()
    return yesterday


def get_pending_profile_dates(symbol):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    conn = engine.connect()
    qry = "select * from daily_profile where symbol = '{0}' and date = (select max(date) as last_date from daily_profile where symbol = '{0}')".format(symbol)
    df = pd.read_sql_query(qry, con=conn)
    conn.close()

    df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['candle'] = df[['open', 'high', 'low', 'close', ]].apply(lambda x: evaluate_candle_type(*x),axis=1)
    return df[['date', 'open', 'high', 'low', 'close', 'candle']].to_dict('records')
    #pending_dates = df['last_date'].to_list() if df['last_date'].to_list() else []
    #pending_dates = [x.strftime('%Y-%m-%d') for x in pending_dates]

    #return pending_dates


def get_filtered_days(ticker, filter):
    ticker = helper_utils.get_nse_index_symbol(ticker)
    stmt = "select * from daily_profile where symbol = '{0}' order by date asc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt.format(ticker), conn)
    conn.close()
    df = df[1:]
    df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['day'] = df['date'].apply(lambda x:  calendar.day_name[datetime.strptime(x, '%Y-%m-%d').weekday()])
    df['year'] = df['date'].apply(lambda x: x[0:4])
    df['body'] = df['close'] - df['open']
    df['range'] = df['high'] - df['low']
    df['ht'] = df['high'] - df[['close', 'open']].max(axis=1)
    df['lt'] = df[['close', 'open']].min(axis=1)-df['low']
    df['candle'] = df[['open', 'high', 'low', 'close', ]].apply(lambda x: evaluate_candle_type(*x),axis=1)

    #print(df[0:1])
    for key, value in filter.items():
        df = df[df[key] == value]
    return df[['date', 'open', 'high', 'low', 'close', 'candle']].to_dict('records')

def prev_day_data(symbol, trade_day):
    print('prev_day_data', symbol)
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt = """select date,open,high,low,close,volume,poc_price,va_l_p,va_h_p,ib_l,ib_h, h_a_l, ht, lt,poc_price,ext_low,ext_high,le_f,he_f
            from daily_profile
            where symbol = '{0}' and date = 
            (select  max(date) as yesterday from daily_profile where symbol = '{0}'  and date<  date('{1}'))"""
    conn = engine.connect()
    rs = conn.execute(stmt.format(symbol, trade_day))
    yesterday = list(rs)[0]
    conn.close()
    return yesterday


def get_daily_profile_data(symbol, trade_day):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select date,open,high,low,close,va_h_p, va_l_p,ib_l_acc,ib_h_acc,poc_price from daily_profile where symbol = '{0}' and date = date('{1}')"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day), conn)
    conn.close()
    return df


def get_daily_tick_data(symbol, trade_day):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    #stmt_1 = "select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and date = date('{1}') order by timestamp asc"
    stmt_1 = "select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and date = date('{1}') order by timestamp asc"
    #print(stmt_1.format(symbol, trade_day))
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day), conn)
    conn.close()
    return df

def get_last_minute_data(symbol, trade_day):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and date = date('{1}') and timestamp = (select max(timestamp) from minute_data where symbol = '{0}' and date = date('{1}'))"
    #print(stmt_1.format(symbol, trade_day))
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day), conn)
    conn.close()
    return df


def get_nth_day_hist_data(symbol, trade_day, n):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = """select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and date = (select date from 
            (SELECT DISTINCT date, DENSE_RANK() OVER (ORDER BY date DESC) AS DATE_RANK FROM (select DISTINCT date from minute_data where date < date('{1}') and symbol = '{0}')as A) as B
            WHERE DATE_RANK = {2})"""
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, n), conn)
    conn.close()
    return df


def get_nth_day_profile_data(symbol, trade_day, n):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = """select  date,open,high,low,close,va_h_p, va_l_p,ib_l_acc,ib_h_acc,poc_price,below_poc, above_poc from daily_profile where symbol = '{0}' and date = (select date from 
            (SELECT DISTINCT date, DENSE_RANK() OVER (ORDER BY date DESC) AS DATE_RANK FROM (select DISTINCT date from daily_profile where date < date('{1}') and symbol = '{0}') as A) as B
            WHERE DATE_RANK = {2})"""
    conn = engine.connect()
    #print(stmt_1.format(symbol, trade_day, n))
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, n), conn)
    conn.close()
    return df

def get_previous_n_day_profile_data(symbol, trade_day, n):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = """select  date as timestamp,open,high,low,close,va_h_p, va_l_p,ib_l_acc,ib_h_acc,poc_price,below_poc, above_poc from daily_profile where symbol = '{0}' and date >= (select date from 
            (SELECT DISTINCT date, DENSE_RANK() OVER (ORDER BY date DESC) AS DATE_RANK FROM (select DISTINCT date from daily_profile where date < date('{1}') and symbol = '{0}') as A) as B
            WHERE DATE_RANK = {2}) and date < date('{1}') and date > (date('{1}')  - ({2} + 4) )"""
    conn = engine.connect()
    #print(stmt_1.format(symbol, trade_day, n))
    #print(stmt_1.format(symbol, trade_day, n))
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, n), conn)
    conn.close()
    return df


def convert_to_n_period_candles(df, period):
    df = df.resample(period).agg(
        OrderedDict([
            ('open', 'first'),
            ('high', 'max'),
            ('low', 'min'),
            ('close', 'last'),
        ])
    )
    return df

def get_prev_week_candle(symbol, trade_day):
    res = {}
    try:
        symbol = helper_utils.get_nse_index_symbol(symbol)
        t_day = datetime.strptime(trade_day,  '%Y-%m-%d').toordinal() if type(trade_day) == str else trade_day.toordinal()
        last_week = t_day - 6
        sunday = last_week - (last_week % 7)
        saturday = datetime.strftime(datetime.fromordinal(sunday + 6), '%Y-%m-%d')
        monday = datetime.strftime(datetime.fromordinal(sunday + 1), '%Y-%m-%d')
        stmt_1 = """select  date,open,high,low,close from daily_profile where symbol = '{0}' and date between date('{1}') and date('{2}') order by date asc"""
        #print(stmt_1)
        conn = engine.connect()
        df = pd.read_sql_query(stmt_1.format(symbol, monday, saturday), conn)
        conn.close()
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.resample('W').agg(
            OrderedDict([
                ('open', 'first'),
                ('high', 'max'),
                ('low', 'min'),
                ('close', 'last'),
            ])
        )
        res = df.to_dict('records')[0]
    except Exception as e:
        print(e)
    return res


def get_uk_opening_time(day):
    tz_in = pytz.timezone('Asia/Kolkata')
    tz_uk = pytz.timezone('UTC')
    daylight_period = {
        2018: [datetime.strptime('15-03-2018', '%d-%m-%Y'),
               datetime.strptime('29-10-2018', '%d-%m-%Y')],
        2019: [datetime.strptime('31-03-2019', '%d-%m-%Y'),
               datetime.strptime('29-10-2019', '%d-%m-%Y')],
        2020: [datetime.strptime('29-03-2020', '%d-%m-%Y'),
               datetime.strptime('26-10-2020', '%d-%m-%Y')],
        2021: [datetime.strptime('28-03-2021', '%d-%m-%Y'),
               datetime.strptime('01-11-2021', '%d-%m-%Y')],
        2022: [datetime.strptime('27-03-2022', '%d-%m-%Y'),
               datetime.strptime('31-10-2022', '%d-%m-%Y')],
        2023: [datetime.strptime('26-03-2023', '%d-%m-%Y'),
               datetime.strptime('29-10-2023', '%d-%m-%Y')],
        2024: [datetime.strptime('31-03-2024', '%d-%m-%Y'),
               datetime.strptime('27-10-2024', '%d-%m-%Y')],
        2025: [datetime.strptime('30-03-2025', '%d-%m-%Y'),
               datetime.strptime('26-10-2025', '%d-%m-%Y')],
        2026: [datetime.strptime('29-03-2026', '%d-%m-%Y'),
               datetime.strptime('25-10-2026', '%d-%m-%Y')],
        2027: [datetime.strptime('28-03-2027', '%d-%m-%Y'),
               datetime.strptime('31-10-2027', '%d-%m-%Y')],
        2028: [datetime.strptime('26-03-2028', '%d-%m-%Y'),
               datetime.strptime('29-10-2028', '%d-%m-%Y')]
    }
    uk_open = day.replace(hour=12, minute=30, second=0, microsecond=0)
    year = day.year
    ds_period = daylight_period[year]
    # print(day.astimezone(tz_uk))
    if day >= tz_in.localize(ds_period[0]) and day <= tz_in.localize(ds_period[1]):
        uk_open = day.replace(hour=13, minute=30, second=0, microsecond=0)
    """
    uk_open = day.astimezone(tz_uk).replace(hour=8, minute=00, second=0)
    #print(uk_open.astimezone(tz_in))
    return uk_open.astimezone(tz_in)
    """
    return uk_open

def evaluate_candle_type(open, high, low,close):
    ct = None
    body = abs(close -open)
    range = high - low
    ht =  high - max(open,close)
    lt =  min(open, close) - low
    if body > 0.8 * range:
        ct = 'Marubuzu'
    return ct

def get_filtered_days(ticker, filter):
    ticker = helper_utils.get_nse_index_symbol(ticker)
    stmt = "select * from daily_profile where symbol = '{0}' order by date asc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt.format(ticker), conn)
    conn.close()
    df = df[1:]
    df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['day'] = df['date'].apply(lambda x:  calendar.day_name[datetime.strptime(x, '%Y-%m-%d').weekday()])
    df['year'] = df['date'].apply(lambda x: x[0:4])
    df['body'] = df['close'] - df['open']
    df['range'] = df['high'] - df['low']
    df['ht'] = df['high'] - df[['close', 'open']].max(axis=1)
    df['lt'] = df[['close', 'open']].min(axis=1)-df['low']
    df['candle'] = df[['open', 'high', 'low', 'close', ]].apply(lambda x: evaluate_candle_type(*x),axis=1)

    #print(df[0:1])
    for key, value in filter.items():
        df = df[df[key] == value]
    return df[['date', 'open', 'high', 'low', 'close', 'candle']].to_dict('records')


def get_all_days(symbol):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    conn = engine.connect()
    stmt_1 = "select distinct date from minute_data where symbol = '{0}' order by date desc"
    rs = conn.execute(stmt_1.format(symbol))
    days = list(rs)
    days = [x[0] for x in days]
    conn.close()
    return days

def get_all_trade_dates_between_two_dates(symbol, start_date, end_date):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    conn = engine.connect()
    stmt_1 = "select distinct date from minute_data where symbol = '{0}' and date>= '{1}' and date <= '{2}' order by date"
    #print(stmt_1.format(symbol, start_date, end_date))
    rs = conn.execute(stmt_1.format(symbol, start_date, end_date))
    days = list(rs)
    days = [x[0] for x in days]
    conn.close()
    return days


def get_hist_ndays_profile_data(symbol, trade_day, n):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select date,open,high,low,close,va_h_p, va_l_p,ib_l_acc,ib_h_acc,poc_price from daily_profile where symbol = '{0}' and date < date('{1}') and  date > date('{1}' - INTERVAL {2} DAY)"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, n), conn)
    conn.close()
    return df

import time

def get_curr_week_consolidated_minute_data_by_start_day(symbol, trade_day, week_start_day=None, start_time=None, full_week=True):
    #print('get_curr_week_minute_data_by_start_day', symbol, trade_day, week_start_day, start_time)
    df = None
    try:
        symbol = helper_utils.get_nse_index_symbol(symbol)
        week_start_day = 'Monday' if week_start_day is None else week_start_day
        start_time = '9:15:00' if start_time is None else start_time
        week_start_day_as_int = time.strptime(week_start_day, "%A").tm_wday
        week_end_day_as_int = (week_start_day_as_int + 6) % 7
        t_day = datetime.strptime(trade_day, '%Y-%m-%d') if type(trade_day) == str else trade_day
        t_day_weekday = t_day.weekday()
        offset = (t_day_weekday - week_end_day_as_int) % 7
        offset = 7 if offset == 0 else offset
        t_day_ordinal = t_day.toordinal()
        last_week_end = t_day_ordinal - offset
        this_week_start = last_week_end + 1
        this_week_end_plus_one = this_week_start + 7

        this_week_start_str = datetime.strftime(datetime.fromordinal(this_week_start), '%Y-%m-%d')
        this_week_end_plus_one_str = datetime.strftime(datetime.fromordinal(this_week_end_plus_one), '%Y-%m-%d')
        this_week_start_str = this_week_start_str + " " + start_time
        this_week_end_plus_one_str = this_week_end_plus_one_str + " " + start_time

        start_ts = int(time.mktime(time.strptime(this_week_start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(this_week_end_plus_one_str, "%Y-%m-%d %H:%M:%S")))
        if full_week:
            stmt_1 = """
            select M.timestamp,M.open,M.high,M.low,M.close, IFNULL(O.volume, 0) as volume from
            (select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and timestamp >= {1} and timestamp < {2} and date not in {3}) M 
            LEFT JOIN
            (select timestamp, sum(volume) as volume  from option_data od where underlying = '{0}' and timestamp >= {1} and timestamp < {2}  group by timestamp) O 
            ON M.timestamp = O.timestamp
            order by timestamp asc
            """.format(symbol, start_ts, end_ts, tuple(exclued_days))
        else:
            stmt_1 = """
            select M.timestamp,M.open,M.high,M.low,M.close, IFNULL(O.volume, 0) as volume from
            (select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and timestamp >= {1} and timestamp < {2} and date not in {3} and date < '{4}') M 
            LEFT JOIN
            (select timestamp, sum(volume) as volume  from option_data od where underlying = '{0}' and timestamp >= {1} and timestamp < {2} and date not in {3} and date < '{4}' group by timestamp) O 
            ON M.timestamp = O.timestamp
            order by timestamp asc
            """.format(symbol, start_ts, end_ts, tuple(exclued_days), trade_day)

            #print(stmt_1.format(symbol, start_ts, end_ts, tuple(exclued_days)))
        conn = engine.connect()
        df = pd.read_sql_query(stmt_1, conn)
        conn.close()
    except Exception as e:
        print(e)
    return df

def get_prev_week_consolidated_minute_data_by_start_day(symbol, trade_day, week_start_day=None, start_time=None):
    res = {}
    try:
        symbol = helper_utils.get_nse_index_symbol(symbol)
        week_start_day = 'Monday' if week_start_day is None else week_start_day
        start_time = '9:15:00' if start_time is None else start_time
        week_start_day_as_int = time.strptime(week_start_day, "%A").tm_wday
        week_end_day_as_int = (week_start_day_as_int + 6) % 7
        t_day = datetime.strptime(trade_day, '%Y-%m-%d') if type(trade_day) == str else trade_day
        t_day_weekday = t_day.weekday()
        offset = (t_day_weekday - week_end_day_as_int) % 7
        offset = 7 if offset == 0 else offset
        t_day_ordinal = t_day.toordinal()
        last_week_end = t_day_ordinal - offset
        last_week_start = last_week_end - 6
        last_week_end_plus_one = last_week_start + 7

        last_week_start_str = datetime.strftime(datetime.fromordinal(last_week_start), '%Y-%m-%d')
        last_week_end_plus_one_str = datetime.strftime(datetime.fromordinal(last_week_end_plus_one), '%Y-%m-%d')
        last_week_start_str = last_week_start_str + " " + start_time
        last_week_end_plus_one_str = last_week_end_plus_one_str + " " + start_time

        start_ts = int(time.mktime(time.strptime(last_week_start_str, "%Y-%m-%d %H:%M:%S")))
        end_ts = int(time.mktime(time.strptime(last_week_end_plus_one_str, "%Y-%m-%d %H:%M:%S")))

        stmt_1 = """
        select M.timestamp,M.open,M.high,M.low,M.close, IFNULL(O.volume, 0) as volume from
        (select timestamp,open,high,low,close,volume from minute_data where symbol = '{0}' and timestamp >= {1} and timestamp < {2} and date not in {3}) M 
        LEFT JOIN
        (select timestamp, sum(volume) as volume  from option_data od where underlying = '{0}' and timestamp >= {1} and timestamp < {2}  group by timestamp) O 
        ON M.timestamp = O.timestamp
        order by timestamp asc
        """.format(symbol, start_ts, end_ts, tuple(exclued_days))
        #print(stmt_1)
        conn = engine.connect()
        df = pd.read_sql_query(stmt_1.format(symbol, start_ts, end_ts, tuple(exclued_days)), conn)
        conn.close()
    except Exception as e:
        print(e)
    return df

def get_daily_option_oi_data(symbol, trade_day, kind='CE'):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp, strike AS instrument, oi  FROM option_data where underlying = '{0}' and date = '{1}' and kind='{2}' order by timestamp asc, strike desc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, kind), conn)
    conn.close()
    return df

def get_daily_option_price_data(symbol, trade_day, kind='CE'):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp, strike AS instrument, close as price  FROM option_data where underlying = '{0}' and date = '{1}' and kind='{2}' order by timestamp asc, strike desc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, kind), conn)
    conn.close()
    return df


def get_daily_option_volume_data(symbol, trade_day, kind='CE'):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp, strike AS instrument, volume  FROM option_data where underlying = '{0}' and date = '{1}' and kind='{2}' order by timestamp asc, strike desc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, kind), conn)
    conn.close()
    return df

def get_daily_option_data(asset, trade_day, data='close', kind=None):
    asset = helper_utils.get_nse_index_symbol(asset)
    if kind is None:
        stmt_1 = "select timestamp, CONCAT(strike,'_', kind) AS instrument, {2}   FROM option_data where underlying = '{0}' and date = '{1}' order by timestamp asc, strike desc".format(asset, trade_day, data)
    else:
        stmt_1 = "select timestamp, strike AS instrument, {3}   FROM option_data where underlying = '{0}' and date = '{1}' and kind='{2}' order by timestamp asc, strike desc".format(asset, trade_day, kind, data)
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1, conn)
    conn.close()
    return df

def get_daily_option_ion_data(assets, trade_day):
    assets = [helper_utils.get_nse_index_symbol(asset) for asset in assets]
    assets = str(tuple(assets)).replace(",)", ")")
    print(assets)
    stmt_1 = "select timestamp, CONCAT(strike,'_', kind) AS instrument, CONCAT(close, '|', volume, '|', oi) as ion  FROM option_data where underlying = '{0}' and date = '{1}' order by timestamp asc, strike desc".format(assets, trade_day)
    stmt_1 = "select timestamp, underlying as asset, CONCAT(strike,'_', kind) AS instrument, open, high, low, close,  volume, oi FROM option_data where oi > 0 and underlying IN {0} and date = '{1}' order by timestamp asc, strike desc".format(
        assets, trade_day)
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1, conn)
    df['asset'] = df['asset'].apply(lambda x: helper_utils.root_symbol(x))
    conn.close()
    return df

def get_prev_day_avg_volume(asset, trade_day):
    asset = helper_utils.get_nse_index_symbol(asset)
    #stmt_1 = "select  CONCAT(strike,'_', kind) AS instrument,  round(AVG(volume)) as avg_volume  FROM option_data where underlying = '{0}' and date = (select max(date) from option_data where underlying = '{0}' and date < '{1}') group by instrument".format(asset, trade_day)

    stmt_1 = """
    WITH 
        B AS (select max(date) as m_date, max(timestamp) as m_time_stamp 
        from option_data where underlying = '{0}' and date < '{1}' and date > date('{1}') - INTERVAL 7 day
    )
    
    select C.instrument , C.avg_volume, D.closing_oi from 
    (select  CONCAT(strike,'_', kind) AS instrument,  round(AVG(volume)) as avg_volume  
    FROM option_data AS A JOIN B
    ON  A.date = B.m_date
    and A.underlying = '{0}' 
    group by instrument) AS C
    JOIN
    
    (SELECT CONCAT(strike,'_', kind) AS instrument,  oi as closing_oi
    FROM option_data p1
    INNER JOIN (select CONCAT(strike,'_', kind) AS instrument, max(date) as m_date, max(timestamp) as m_time_stamp 
        from option_data where underlying = '{0}' and date = (select max(date) as m_date from option_data where underlying = '{0}' and date < '{1}' and date > date('{1}') - INTERVAL 7 day)
        group by instrument) p2
    ON (CONCAT(p1.strike,'_', p1.kind) = p2.instrument and p1.timestamp = p2.m_time_stamp)) AS D
    ON C.instrument = D.instrument
    """.format(asset, trade_day)
    #print(stmt_1)
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1, conn)
    conn.close()
    return df


def get_daily_spot_ion_data(assets, trade_day):
    assets = [helper_utils.get_nse_index_symbol(asset) for asset in assets]
    assets = str(tuple(assets)).replace(",)", ")")

    #stmt_1 = "select timestamp, CONCAT(open, '|', high, '|', low, '|', close) as ion  from minute_data where symbol = '{0}' and date = date('{1}') order by timestamp asc"
    stmt_1 = "select timestamp,symbol as asset, open, high, low, close  from minute_data where symbol IN {0} and date = date('{1}') order by timestamp asc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(assets, trade_day), conn)
    df['asset'] = df['asset'].apply(lambda x: helper_utils.root_symbol(x))
    conn.close()
    return df


def get_daily_option_data_2(symbol, trade_day):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp,option_symbol, CONCAT(strike,'_', kind) AS instrument, strike, kind, oi, volume,open,high,low,close  FROM option_data where underlying = '{0}' and date = '{1}' order by timestamp asc, strike desc"
    print(stmt_1.format(symbol, trade_day))
    start = datetime.now()
    conn = engine.connect()
    end = datetime.now()
    print('connection open took', (end - start).total_seconds())

    start = datetime.now()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day), conn)
    end = datetime.now()
    print('result fetch took', (end - start).total_seconds())

    start = datetime.now()
    conn.close()
    end = datetime.now()
    print('conn close took', (end - start).total_seconds())
    return df


def get_aggregate_option_data_ts(symbol, dt=None):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_a = """select A.date, A.timestamp ,S.time_string, S.spot, call_oi, put_oi, total_oi,total_volume,call_volume,put_volume, total_oi-call_oi-put_oi as diff from 
                (select date, timestamp ,round(sum(oi)/1000,0) as total_oi, round(sum(volume)/1000,0) as total_volume from option_data where underlying = "{0}" group by date, timestamp ) A,
                (select date, timestamp ,round(sum(oi)/1000,0) as call_oi,round(sum(volume)/1000,0) as call_volume from option_data where underlying = "{0}" and kind = 'CE' group by date, timestamp ) C,
                (select date, timestamp ,round(sum(oi)/1000,0) as put_oi,round(sum(volume)/1000,0) as put_volume from option_data where underlying = "{0}" and kind = 'PE' group by date, timestamp ) P,
                (select date, timestamp ,time_string, close as spot from minute_data md  where symbol = "{0}") S
                where  A.timestamp = C.timestamp and A.timestamp = P.timestamp and A.timestamp = S.timestamp """
                
    stmt_a = stmt_a + "and A.date = '{0}' ".format(dt) if dt is not None else stmt_a
    stmt_a = stmt_a + "order by A.timestamp asc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_a.format(symbol), conn)
    conn.close()
    return df

def get_option_data_with_time_jump(symbol, dt):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_a = """select  date, timestamp ,time_string,spot, call_oi, put_oi, total_oi,total_volume,call_volume,put_volume,  diff from
                (select A.date, A.timestamp , call_oi, put_oi, total_oi,total_volume,call_volume,put_volume, total_oi-call_oi-put_oi as diff,S.spot, S.time_string from 
                (select date, timestamp ,round(sum(oi)/1000,0) as total_oi, round(sum(volume)/1000,0) as total_volume from option_data where underlying = "{0}" group by date, timestamp ) A,
                (select date, timestamp ,round(sum(oi)/1000,0) as call_oi,round(sum(volume)/1000,0) as call_volume from option_data where underlying = "{0}" and kind = 'CE' group by date, timestamp ) C,
                (select date, timestamp ,round(sum(oi)/1000,0) as put_oi,round(sum(volume)/1000,0) as put_volume from option_data where underlying = "{0}" and kind = 'PE' group by date, timestamp ) P,
                (select date, timestamp ,time_string, close as spot from minute_data md  where symbol = "{0}") S
                where  A.timestamp = C.timestamp and A.timestamp = P.timestamp  and A.timestamp = S.timestamp and A.date = '{1}' ) F
                GROUP BY ((timestamp-0) DIV 300), date order by timestamp asc"""

    conn = engine.connect()
    df = pd.read_sql_query(stmt_a.format(symbol, dt), conn)
    conn.close()
    return df

def get_last_option_loaded_date(symbol):
    last_date = None
    engine = get_db_engine()
    conn = engine.connect()
    try:
        qry = "select max(date) as last_date from option_data where underlying = '{}'".format(symbol)
        df = pd.read_sql_query(qry, con=conn)
        last_date = df['last_date'].to_list()[0] if df['last_date'].to_list() else None
    except:
        pass
    conn.close()
    return last_date


def get_candle_body_size(symbol, trade_day, period='5Min'):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    df = get_nth_day_hist_data(symbol, trade_day, 1)
    df['timestamp'] = df['timestamp'].apply(lambda x : datetime.fromtimestamp(x))
    df = df.set_index('timestamp')
    df = df.resample(period).agg(
        OrderedDict([
            ('open', 'first'),
            ('high', 'max'),
            ('low', 'min'),
            ('close', 'last'),
        ])
    )
    res = df.to_dict('records')
    candle_bodies = [round(abs(cdl['high'] - cdl['low'])) for cdl in res]
    pcts = [np.percentile(candle_bodies, 30), np.percentile(candle_bodies, 50), np.percentile(candle_bodies, 70)]
    return pcts



def save_strategy_run_params(symbol, trade_day, kind='CE'):
    symbol = helper_utils.get_nse_index_symbol(symbol)
    stmt_1 = "select timestamp, strike AS instrument, oi  FROM option_data where underlying = '{0}' and date = '{1}' and kind='{2}' order by timestamp asc, strike desc"
    conn = engine.connect()
    df = pd.read_sql_query(stmt_1.format(symbol, trade_day, kind), conn)
    conn.close()
    return df
