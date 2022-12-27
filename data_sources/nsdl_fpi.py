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
from pathlib import Path
root_path = str(Path(__file__).resolve().parent)
print(root_path)

from db.db_engine import get_db_engine


base_url = 'https://www.fpi.nsdl.co.in/web/Reports/FPI_Fortnightly_Selection.aspx'
fpi_base_url= 'https://www.fpi.nsdl.co.in/web/StaticReports/Fortnightly_Sector_wise_FII_Investment_Data/FIIInvestSector_'

class FPIDataLoader:
    def __init__(self):
        self.rdbms_table = 'fpi_data'
        self.fresh_data_df = None
        self.all_periods = []
        self.set_periods()

    def set_periods(self):
        today = date.today()
        #print(today)
        for year in range(2012,2023):
            for month in range(1, 13):
                month_mid = date(year, month, 15)
                month_end = date(year, month , 1) + relativedelta(months=1) - relativedelta(days=1)
                if month_mid < date.today():
                    self.all_periods.append(month_mid.strftime('%Y-%m-%d'))
                if month_end < date.today():
                    self.all_periods.append(month_end.strftime('%Y-%m-%d'))
        del self.all_periods[0]
        #print(self.all_periods)

    def get_existing_periods(self):
        print('Fetching results from the database...')
        df = None
        try:
            con = get_db_engine().connect()
            qry = "SELECT distinct date from {0}".format(self.rdbms_table)
            df = pd.read_sql_query(qry, con=con)
            con.close()
        except Exception as e:
            pass
        return [] if df is None else df['date'].to_list()

    def get_fresh_data(self,period):
        print('frsh data ++++++++++++')
        trs = []
        #'Jan312022.html'
        try:
            x = datetime.strptime(period, '%Y-%m-%d').strftime('%B%d%Y')
            print(x)
            url = fpi_base_url + x + ".html"
            print(url)

            headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
            response = requests.get(url, headers=headers)
            #print(response.text)
            soup = BeautifulSoup(response.text, 'html.parser')
            print(soup)
            tables = soup.find_all('table')
            print(tables)
            table = tables[0]
            trs = table.find_all('tr')
            trs = trs[3::]

        except Exception as e:
            print('+++++++++++++')
            print(e)
            try:
                x = datetime.strptime(period, '%Y-%m-%d').strftime('%b%d%Y')
                print(x)
                url = fpi_base_url + x + ".html"
                print(url)

                headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
                response = requests.get(url, headers=headers)
                #print(response.text)
                soup = BeautifulSoup(response.text, 'html.parser')
                print(soup)
                tables = soup.find_all('table')
                print(tables)
                table = tables[0]
                trs = table.find_all('tr')
                trs = trs[3::]
            except Exception as e:
                print(e)
                print('Error retrieving url')
                return []
        """
        col_tr_1 = trs[1]
        cols_1 = []
        for col in col_tr_1.find_all('td'):
            cols_1.append(col.text)
        print(cols_1)
        col_tr_2 = trs[2]
        cols_2 = []
        for col in col_tr_2.find_all('td'):
            cols_2.append(col.text)
        print(cols_2)
        res = [i + j for i, j in zip(cols_1, cols_2)]
        print(res)
        """
        res = []
        try:
            #print(trs)
            for row in trs:
                cols = row.find_all('td')
                sector = cols[1].text
                """
                curr_eq = int(cols[32].text.replace(',', ''))
                curr_tot = int(cols[36].text.replace(',', ''))
                prev_eq = int(cols[2].text.replace(',', ''))
                prev_tot = int(cols[6].text.replace(',', ''))
                """

                curr_eq = int(cols[20].text.replace(',', ''))
                curr_tot = int(cols[22].text.replace(',', ''))
                prev_eq = int(cols[2].text.replace(',', ''))
                prev_tot = int(cols[4].text.replace(',', ''))

                eq_diff = curr_eq-prev_eq
                tot_diff = curr_tot-prev_tot
                rd = [period, sector, curr_eq, curr_tot, prev_eq, prev_tot, eq_diff, tot_diff]
                res.append(rd)
        except:
            print('no of cols dont match')
        return res

    def load_data(self):
        existing_periods = self.get_existing_periods()
        #print(existing_periods)
        periods_to_fetch = list(set(self.all_periods) - set(existing_periods)) #self.all_periods [0:-1]#
        periods_to_fetch = ['2022-01-31']
        print(periods_to_fetch)

        for period in periods_to_fetch:
            fresh_data = self.get_fresh_data(period)
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


