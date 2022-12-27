import requests
import json
import pandas as pd
from lxml import etree,html
import numpy as np
from bs4 import BeautifulSoup
import time
from urllib.request import urlopen
from dateutil import parser
from datetime import datetime,date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.types import  DATE

from db.db_engine import get_db_engine

baseurl = "https://www.nseindia.com/"
oc_url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'

class OCDataLoader:
    def __init__(self):
        self.rdbms_table = 'fpi_data'
        self.fresh_data_df = None


    def get_fresh_data(self):
        print('frsh data ++++++++++++')
        res = []
        try:

            #headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36", 'Origin': 'https://www.nseindia.com', 'Referer': 'https://www.nseindia.com/'}
            session = requests.Session()

            headers = {'User-Agent': 'Mozilla/5.0'}
            request = session.get(baseurl, headers=headers, timeout=2)
            cookies = dict(request.cookies)
            response = session.get(oc_url, headers=headers)
            #print(response.text)
            resp_dict = json.loads(response.text)
            #print(resp_dict)
            option_data = resp_dict['records']['data']
            expiry_dates = resp_dict['records']['expiryDates']
            expiry_dates = [datetime.strptime(x, '%d-%b-%Y') for x in expiry_dates]
            #print(expiry_dates)
            dt = [expiry_dates[x].strftime('%d-%b-%Y') for x in range(3)]
            print(dt)
            selected_data = [data for data in option_data if data['expiryDate'] in dt]
            #print(selected_data)
            res = {}
            for data in selected_data:
                key =  data['expiryDate'] + "_" + str(data['strikePrice'])
                if key not in res.keys():
                    res[key] = {}
                res[key]['expiry_date'] = datetime.strptime(data['expiryDate'], '%d-%b-%Y')
                res[key]['strike_price'] = data['strikePrice']
                if 'CE' in data.keys():
                    res[key]['calls_oi'] = data['CE']['openInterest']
                    res[key]['calls_change_oi'] = data['CE']['changeinOpenInterest']
                    res[key]['calls_volume'] = data['CE']['totalTradedVolume']
                    res[key]['calls_iv'] = data['CE']['impliedVolatility']
                    res[key]['calls_ltp'] = data['CE']['lastPrice']
                if 'PE' in data.keys():
                    res[key]['puts_oi'] = data['PE']['openInterest']
                    res[key]['puts_change_oi'] = data['PE']['changeinOpenInterest']
                    res[key]['puts_volume'] = data['PE']['totalTradedVolume']
                    res[key]['puts_iv'] = data['PE']['impliedVolatility']
                    res[key]['puts_ltp'] = data['PE']['lastPrice']
            df = pd.DataFrame.from_dict(res.values())
            df.sort_values(by=['expiry_date', 'strike_price'], ascending=[True, True], na_position='first')
            df['expiry_date'] = df['expiry_date'].apply(lambda x: x.strftime('%d-%m-%Y'))
            resp = {}
            resp['expiry_dates'] = list(df.expiry_date.unique())
            resp['strike_prices'] = list(df.strike_price.unique())
            resp['data'] = df.to_dict('records')
            print(resp)


        except Exception as e:
            print('+++++++++++++')
            print(e)

        return res

    def load_data(self):
            fresh_data = self.get_fresh_data()
            """
            if len(fresh_data) > 0:
                print('loading FPI data for ' + period)
                fresh_data_df = pd.DataFrame(fresh_data)
                fresh_data_df.columns = ['date', 'sector', 'curr_eq', 'curr_tot', 'prev_eq', 'prev_tot', 'eq_diff', 'tot_diff']
                con = get_db_engine().connect()
                #fresh_data_df.to_sql(self.rdbms_table, con, index=False, if_exists='append', method='multi', chunksize=500)
                try:
                    con.execute('ALTER TABLE {0} ADD PRIMARY KEY (sector, date);'.format(self.rdbms_table))
                except:
                    pass
                con.close()
            """


