from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework import status
from django.db.models import Max,F,Func, Value, CharField


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
from options.models import Chain
from options.serializers import ChainDetailsSerializer
from helper.utils import get_nse_index_symbol
from db.db_engine import get_db_engine
#from market.models import OptionChainHistory

baseurl = "https://www.nseindia.com/"
oc_url = 'https://www.nseindia.com/api/option-chain-indices?symbol='

class OCDataLoader:
    def __init__(self):
        self.fresh_data_df = None


    def get_fresh_data(self,ticker):
        print('frsh data ++++++++++++')
        resp = {}
        lots = {'NIFTY': 50, 'BANKNIFTY':75}
        lot_size = lots[ticker]
        try:

            #headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36", 'Origin': 'https://www.nseindia.com', 'Referer': 'https://www.nseindia.com/'}
            session = requests.Session()

            headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/534.7 (KHTML, like Gecko) Chrome/7.0.517.44 Safari/534.7',
			   'Accept':'application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
			   'Accept-Encoding':'gzip,deflate,sdch',
			   'Referer':'https://www.nseindia.com/market-data/equity-derivatives-watch'}
            request = session.get(baseurl, headers=headers, timeout=3)
            cookies = dict(request.cookies)
            response = session.get(oc_url+ticker, headers=headers)
            #print(response.text)
            resp_dict = json.loads(response.text)
            #print(resp_dict)
            option_data = resp_dict['records']['data']
            expiry_dates = resp_dict['records']['expiryDates']
            expiry_dates = [datetime.strptime(x, '%d-%b-%Y') for x in expiry_dates]
            #print(expiry_dates)
            dt = [expiry_dates[x].strftime('%d-%b-%Y') for x in range(6)]
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

            expiries = list(df.expiry_date.unique())
            print(expiries)
            expiries.sort()
            print(expiries)
            resp['expiry_dates'] = [pd.to_datetime(x).strftime('%d-%m-%Y') for x in expiries]
            df['expiry_date'] = df['expiry_date'].apply(lambda x: x.strftime('%d-%m-%Y'))

            resp['strike_prices'] = list(df.strike_price.unique())
            resp['strike_prices'].sort()
            resp['oi'] = df.to_dict('records')

        except Exception as e:
            print('+++++++++++++')
            print(e)

        return resp



class OptionDataView(APIView):
    def get(self, request):
        ticker = request.GET.get("ticker", None)
        print(ticker)
        sm = OCDataLoader()
        result = sm.get_fresh_data(ticker)
        return Response(
            {"message": "Option Data", ticker: result, "status": True},
            status=status.HTTP_200_OK,
        )

class OptionDataView22(APIView):
    def get(self, request):
        ticker = request.GET.get("ticker", None)
        max_date = Chain.objects.filter(ticker=ticker).latest('created_on').created_on
        #print(max_date)
        lst = Chain.objects.filter(ticker=ticker, created_on=max_date).order_by('expiry_date', 'strike_price')
        #lst2 = Chain.objects.filter(ticker=ticker).annotate(max_date=Max('created_on')).filter(created_on=F('max_date'))
        lst.annotate(
            formatted_date=Func(
                F('expiry_date'),
                Value('dd-MM-yyyy'),
                function='DATE_FORMAT',
                output_field=CharField()
            )
        )

        expiry_dates = list(set(lst.values_list('expiry_date', flat=True)))
        print(expiry_dates)
        expiry_dates.sort()
        strike_prices = list(set(lst.values_list('strike_price', flat=True)))
        #list = Chain.objects.latest('created_on') #filter(role_type=SPACE_ROLE_TYPE)
        #print(list)
        serializer = ChainDetailsSerializer(lst,many=True)
        resp = {}
        resp['expiry_dates'] = [pd.to_datetime(x).strftime('%Y-%m-%d') for x in expiry_dates]

        resp['strike_prices'] = strike_prices
        resp['strike_prices'].sort()
        resp['oi'] = serializer.data

        #print(serializer.data)
        return Response(
            {"message": "Option Data", ticker: resp, "status": True},
            status=status.HTTP_200_OK,
        )



