import time
from profile.market_profile import HistMarketProfileService
import numpy as np
from itertools import compress
from settings import market_profile_db,reports_dir
from config import exclued_days
import pandas as pd
import os
import datetime
from dateutil.relativedelta import relativedelta
import calendar
from config import regimes, regime_desc
from db.db_engine import get_db_engine
engine = get_db_engine()
"""
date:0
open:1
high:2
low:3
close:4
volume:5
poc_price:6
va_l_p:7
va_h_p:8
ib_l:9
ib_h:10

HIGH > VAH|OBH > POC | OBH | OBL > VAL | OBL > LOW
CLOSE > VAH | OBH > POC
CLOSE < VAL | OBL < POC
VAL < CLOSE < VAH  

feature_set = {
                'date': row[0],
                'regime_desc':regime_desc[reg_idx],
                'day': calendar.day_name[datetime.datetime.strptime(row[0], '%Y-%m-%d').weekday()],
                'y_vah_above_ibh':  int(y_vah > y_ibh),
                'y_val_below_ibl': int(y_val < y_ibl),
                'y_close_below_ibl': int(y_close < y_ibl),
                'y_close_above_ibh': int(y_close > y_ibh),
                'y_close_in_ob_rng': int((y_close < y_ibh) and (y_close > y_ibl)),
                'y_close_below_val': int(y_close < y_val),
                'y_close_above_vah': int(y_close > y_vah),
                'y_close_in_va_rng': int((y_close < y_vah) and (y_close > y_val)),
                't_open_above_vah': int(t_open > y_vah),
                't_open_below_val': int(t_open < y_val),
                't_open_in_va_rng': int((t_open < y_vah) and (t_open > y_val)),
                't_open_above_yhigh': int(t_open > y_high),
                't_open_below_ylow': int(t_open < y_low),
                't_low_above_vah': int(t_low > y_vah),
                't_low_below_val': int(t_low < y_val),
                't_low_in_va_rng': int((t_low < y_vah) and (t_low > y_val)),
                't_low_above_yhigh': int(t_low > y_high),
                't_low_below_ylow': int(t_low < y_low),
                't_high_above_vah': int(t_high > y_vah),
                't_high_below_val': int(t_high < y_val),
                't_high_in_va_rng': int((t_high < y_vah) and (t_high > y_val)),
                't_high_above_yhigh': int(t_high > y_high),
                't_high_below_ylow': int(t_high < y_low),
                't_open_gap': (t_open - y_high if t_open > y_high else t_open - y_low if t_open < y_low else 0)/y_close,
                't_gap': row[1] - yesterday[2] if row[1] > yesterday[2] else row[1] - yesterday[3] if row[1] < yesterday[
                    3] else 0,
                't_range' : (t_high - t_low)/y_close,
                't_oh': (t_high - t_open)/y_close,
                't_ol': (t_low - t_open)/y_close,
                't_hal' : t_hal

            }

"""
stmt_1 = "select date,open,high,low,close,volume,poc_price,va_l_p,va_h_p,ib_l,ib_h,h_a_l, ht, lt,poc_price,ext_low,ext_high,le_f,he_f from daily_profile where symbol = 'NSE:NIFTY50-INDEX' and date >= date('{0}') and date < date('{1}') order by date desc"
stmt_2 = """select date,open,high,low,close,volume,poc_price,va_l_p,va_h_p,ib_l,ib_h, h_a_l, ht, lt,poc_price,ext_low,ext_high,le_f,he_f
                from daily_profile
                where symbol = 'NSE:NIFTY50-INDEX' and date = 
                (select  max(date) as yesterday from daily_profile where symbol = 'NSE:NIFTY50-INDEX'  and date<  date('{0}'))"""

def get_features():
    conn = engine.connect()
    daily_features = []
    for reg_idx in range(len(regimes)-1):
        rs = conn.execute(stmt_1.format(regimes[reg_idx], regimes[reg_idx+1]))

        for row in rs:
            rs2 = conn.execute(stmt_2.format(row[0]))
            try:
                yesterday = list(rs2)[0]
                t_open = row[1]
                t_high = row[2]
                t_low = row[3]
                t_close = row[4]
                t_poc = row[6]
                t_val = row[7]
                t_vah = row[8]
                t_ibl = row[9]
                t_ibh = row[10]
                t_hal = row[11]
                t_ht = row[12]
                t_lt = row[13]
                t_poc_price = row[14]
                t_ext_low = row[15]
                t_ext_high = row[16]
                t_le_f = row[17]
                t_he_f = row[18]

                y_open = yesterday[1]
                y_high = yesterday[2]
                y_low = yesterday[3]
                y_close = yesterday[4]
                y_poc = yesterday[6]
                y_val = yesterday[7]
                y_vah = yesterday[8]
                y_ibl = yesterday[9]
                y_ibh = yesterday[10]
                y_hal = yesterday[11]
                y_ht = yesterday[12]
                y_lt = yesterday[13]

                y_poc_price = yesterday[14]
                y_ext_low = yesterday[15]
                y_ext_high = yesterday[16]
                y_le_f = yesterday[17]
                y_he_f = yesterday[18]

                tmp_y_va = list(range(int(np.floor(y_val)), int(np.ceil(y_vah)) + 1))
                tmp_t_ib = list(range(int(np.floor(t_ibl)), int(np.ceil(t_ibh)) + 1))
                over_lap = list(set(tmp_y_va) & set(tmp_t_ib))
                over_lap_pct = len(over_lap)/len(tmp_y_va)
                feature_set = {
                    'date': row[0],
                    'regime_desc':regime_desc[reg_idx],
                    'day': calendar.day_name[datetime.datetime.strptime(row[0], '%Y-%m-%d').weekday()],
                    'y_close_below_ibl': (y_close - y_ibl),
                    'y_close_above_ibh': (y_close - y_ibh)/(y_ibh - y_ibl),
                    'y_close_in_ib_rng': int((y_close < y_ibh) and (y_close > y_ibl)),
                    'y_close_below_val': (y_close - y_val),
                    'y_close_above_vah': (y_close - y_vah),
                    'y_close_in_va_rng': int((y_close < y_vah) and (y_close > y_val)),
                    'y_hal': y_hal,
                    'y_open': y_open,
                    'y_high': y_high,
                    'y_low': y_low,
                    'y_close': y_close,
                    'y_val': y_val,
                    'y_vah': y_vah,
                    'y_ibl': y_ibl,
                    'y_ibh': y_ibh,
                    't_open_above_y_vah': t_open - y_vah,
                    't_open_below_y_val': t_open - y_val,
                    't_open_in_y_va_rng': int((t_open < y_vah) and (t_open > y_val)),
                    't_open_above_y_high': t_open > y_high,
                    't_open_below_y_low': t_open < y_low,
                    't_open_in_y_rng': int((t_open < y_high) and (t_open > y_low)),
                    't_open_gap': ((t_open - y_high) if t_open > y_high else (t_open - y_low) if t_open < y_low else 0) / y_close,
                    't_open_va_gap': ((t_open - y_vah) if (t_open > y_vah) else (t_open - y_val) if t_open < y_val else 0) / y_close,
                    't_range': (t_high - t_low),
                    't_oh': (t_high - t_open),
                    't_ol': (t_low - t_open),
                    't_hal': t_hal,
                    't_low_y_vah': (t_low - y_vah) ,
                    't_low_y_val': (t_low - y_val),
                    't_low_in_va_y_rng': int((t_low < y_vah) and (t_low > y_val)),
                    't_high_y_vah': t_high - y_vah,
                    't_high_y_val': (t_high - y_val) ,
                    't_high_in_va_rng': int((t_high < y_vah) and (t_high > y_val)),
                    't_low_y_low': (t_low - y_low),
                    't_low_y_high': (t_low - y_high),
                    't_low_in_y_rng': int((t_low < y_high) and (t_low > y_low)),
                    't_high_y_low': t_high - y_low,
                    't_high_y_high': (t_high - y_high),
                    't_high_in_y_rng': int((t_high < y_high) and (t_high > y_low)),
                    't_ib_y_va_over_lap': over_lap_pct,
                    't_open': t_open,
                    't_high': t_high,
                    't_low': t_low,
                    't_close': t_close,
                    't_val': t_val,
                    't_vah': t_vah,
                    't_ibl': t_ibl,
                    't_ibh': t_ibh,

                    't_low_time': datetime.datetime.fromtimestamp(t_lt).hour*100+datetime.datetime.fromtimestamp(t_lt).minute,
                    't_high_time': datetime.datetime.fromtimestamp(t_ht).hour*100+datetime.datetime.fromtimestamp(t_ht).minute,
                    't_ext_low': t_ext_low,
                    't_ext_high': t_ext_high,
                    't_le_f' : t_le_f,
                    't_he_f' : t_he_f,
                    't_return': t_close/y_close-1
                }
                dt = datetime.datetime.fromtimestamp(t_lt)
                dt = dt.replace(hour=9, minute=15, second=0)
                t_low_since_mkt = (datetime.datetime.fromtimestamp(t_lt)-dt).total_seconds()/60
                t_high_since_mkt = (datetime.datetime.fromtimestamp(t_ht)-dt).total_seconds()/60
                feature_set['t_low_since_mkt'] = t_low_since_mkt
                feature_set['t_high_since_mkt'] = t_high_since_mkt
                daily_features.append(feature_set)
                """
                print(row[0])
                print(t_low_since_mkt)
                print(t_high_since_mkt)
                """
            except Exception as e:
                print(e)
                pass
    conn.close()
    df = pd.DataFrame(daily_features)
    df['gap_ind'] = df['t_open_gap'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
    df['va_gap_ind'] = df['t_open_va_gap'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
    return df
"""
summary of weekday effect on open
"""
"""
print('analysis for ++++++++', regimes[reg_idx], regimes[reg_idx + 1])
cols = ['date','regime_desc', 'day', 't_open_gap','t_open_va_gap','t_range','t_oh','t_ol',  't_hal', 't_return', 't_low_y_vah', 't_high_y_val', 't_ib_y_va_over_lap']
df.head()
df_i = df[cols].copy()

df_i['gap_ind'] = df_i['t_open_gap'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
#print(df_i)

date_wise_df = df_i.groupby(['day', 'gap_ind']).agg({'t_oh': ['count', 'mean', 'min', 'max'], 't_ol': ['mean', 'min', 'max'], 't_gap': ['mean'], 't_hal' : ['sum']})
date_wise_df.columns = ['count', 't_oh_avg', 't_oh_min', 't_oh_max', 't_ol_avg', 't_ol_min', 't_ol_max', 't_gap_avg', 't_hal']
date_wise_df = date_wise_df.reset_index()

print(date_wise_df)
date_wise_df.to_csv(reports_dir + 'date_wise_df_' + regimes[reg_idx] +'_'+ regimes[reg_idx + 1] + '.csv')
"""



