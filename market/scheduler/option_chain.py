import requests
import json
import pandas as pd
from lxml import etree,html
import numpy as np
from bs4 import BeautifulSoup
import time
from urllib.request import urlopen
from dateutil import parser
from datetime import datetime,date
from options.models import Chain
from options.serializers import ChainSerializer
from django.utils import timezone
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

from settings import chromedriver
baseurl = "https://www.nseindia.com/"
oc_url = 'https://www.nseindia.com/api/option-chain-indices?symbol='

class OCDataLoader:
    def __init__(self):
        self.fresh_data_df = None


    def get_fresh_data(self,ticker,query_time):
        #query_time = timezone.now()
        #print(query_time)
        print('frsh data ++++++++++++')
        resp = {}
        lots = {'NIFTY': 50, 'BANKNIFTY':75}
        lot_size = lots[ticker]
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            browser = webdriver.Chrome(chromedriver, chrome_options=chrome_options)
            browser.get(baseurl)
            print(browser.get_cookies())
            cookies = browser.get_cookies()
            for cookie in cookies:
                print(cookie)

            #headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36", 'Origin': 'https://www.nseindia.com', 'Referer': 'https://www.nseindia.com/'}
            session = requests.Session()
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; '
            'x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36'}
            request = session.get(baseurl, headers=headers,verify=False, timeout=10, cookies=cookies)
            #cookies = dict(request.cookies)
            response = session.get(oc_url+ticker,verify=False, headers=headers, cookies=cookies)
            #print(response.text)
            resp_dict = json.loads(response.text)
            #print(resp_dict)
            option_data = resp_dict['records']['data']
            expiry_dates = resp_dict['records']['expiryDates']
            expiry_dates = [datetime.strptime(x, '%d-%b-%Y') for x in expiry_dates]
            #print(expiry_dates)
            dt = [expiry_dates[x].strftime('%d-%b-%Y') for x in range(5)]
            #print(dt)
            selected_data = [data for data in option_data if data['expiryDate'] in dt]
            #print(selected_data)
            res = {}
            for data in selected_data:
                key =  data['expiryDate'] + "_" + str(data['strikePrice'])
                if key not in res.keys():
                    res[key] = {}
                    res[key]['expiry_date'] = datetime.strptime(data['expiryDate'], '%d-%b-%Y')
                    res[key]['strike_price'] = data['strikePrice']
                    res[key]['ticker'] = ticker
                    res[key]['created_on'] = query_time

                if 'CE' in data.keys():
                    res[key]['calls_oi'] = data['CE']['openInterest'] * lot_size
                    res[key]['calls_change_oi'] = data['CE']['changeinOpenInterest'] * lot_size
                    res[key]['calls_volume'] = data['CE']['totalTradedVolume'] * lot_size
                    res[key]['calls_iv'] = data['CE']['impliedVolatility']
                    res[key]['calls_ltp'] = data['CE']['lastPrice']
                    res[key]['calls_buy_qty'] = data['CE']['totalBuyQuantity']
                    res[key]['calls_sell_qty'] = data['CE']['totalSellQuantity']
                    res[key]['spot'] = data['CE']['underlyingValue']
                if 'PE' in data.keys():
                    res[key]['puts_oi'] = data['PE']['openInterest'] * lot_size
                    res[key]['puts_change_oi'] = data['PE']['changeinOpenInterest'] * lot_size
                    res[key]['puts_volume'] = data['PE']['totalTradedVolume'] * lot_size
                    res[key]['puts_iv'] = data['PE']['impliedVolatility']
                    res[key]['puts_ltp'] = data['PE']['lastPrice']
                    res[key]['puts_buy_qty'] = data['PE']['totalBuyQuantity']
                    res[key]['puts_sell_qty'] = data['PE']['totalSellQuantity']
                    res[key]['spot'] = data['PE']['underlyingValue']
            df = pd.DataFrame.from_dict(res.values())
            df = df.fillna(0)
            df.sort_values(by=['expiry_date', 'strike_price'], ascending=[True, True], na_position='first')
            df['expiry_date'] = df['expiry_date'].apply(lambda x: x.strftime('%d-%m-%Y'))
            resp['oi'] = df.to_dict('records')

        except Exception as e:
            print('+++++++++++++')
            print(e)

        return resp



def load():
    tickers = ['NIFTY', 'BANKNIFTY']
    job_time = timezone.now()
    hr = job_time.hour
    min = job_time.minute
    tf = hr * 100 + min
    if tf >= 0 and tf<= 2400:
        for ticker in tickers:
            sm = OCDataLoader()
            result = sm.get_fresh_data(ticker, job_time)
            if result.get('oi',None) is not None:
                serializer = ChainSerializer(data=result['oi'], many=True)

                if serializer.is_valid(raise_exception=True):
                    try:
                        feed_list = [Chain(**item) for item in serializer.validated_data]
                        Chain.objects.bulk_create(feed_list)

                        #serializer.save()
                    except Exception as e:
                        logging.exception(
                            f"exception in creating chain data, exception is {e}"
                        )





