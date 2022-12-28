import pandas as pd
from market.db.db_engine import get_db_engine, get_db_sqlite_engine
from sqlalchemy.types import VARCHAR, Boolean, DATE, TEXT, JSON, ARRAY, DateTime

def get_sqlite_data(table):
    engine = get_db_sqlite_engine()
    conn = engine.connect()
    qry = "select * from " + table
    df = pd.read_sql_query(qry, con=conn)
    conn.close()
    return df

def load_fpi_data(df):
    engine = get_db_engine()
    conn = engine.connect()
    df.to_sql('fpi_data', conn, method='multi', chunksize=100, if_exists="replace", index=False, dtype={'date':DATE, 'sector':VARCHAR(length=200)})
    conn.execute('ALTER TABLE fpi_data ADD PRIMARY KEY (date, sector);')
    conn.close()

def load_daily_profile(df):
    engine = get_db_engine()
    conn = engine.connect()
    df.to_sql('daily_profile', conn, method='multi', chunksize=100, if_exists="replace", index=False, dtype={'date':DATE, 'symbol':VARCHAR(length=50)})
    conn.execute('ALTER TABLE daily_profile ADD PRIMARY KEY (date, symbol);')
    conn.close()


def load_minute_data(df):
    engine = get_db_engine()
    conn = engine.connect()
    df.to_sql('minute_data', conn, method='multi', chunksize=500, if_exists="replace", index=False, dtype={'date':DATE, 'symbol':VARCHAR(length=50)})
    conn.execute('ALTER TABLE minute_data ADD PRIMARY KEY (timestamp, symbol);')
    conn.execute('ALTER TABLE minute_data ADD INDEX (date);')
    conn.close()

df1 = get_sqlite_data('fpi_data')
load_fpi_data(df1)

df2 = get_sqlite_data('daily_profile')
load_daily_profile(df2)

df3 = get_sqlite_data('minute_data')
load_minute_data(df3)
