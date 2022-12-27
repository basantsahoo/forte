
url = 'https://www.moneycontrol.com/economic-calendar'
import requests

r = requests.get(url)
#print(r.text)


"""
import pyEX as p
print(p.chart?)
"""
"""
import requests
url = "https://sandbox.iexapis.com/stable/stock/aapl/quote?token=Tpk_0a3b62f798054d58abd8a8c4f6502f2a&symbols=aapl"
base_url = 'https://cloud.iexapis.com/stable'
url2 = '/ref-data/exchanges'
token_str = '?token=pk_749ebf5d985d4721b6d75fdac3865ac1'
region_url = base_url+url2+token_str
sym_url = '/ref-data/exchange/XNSE/symbols'
print(base_url+'/stock/EQINTELLECT-SI/quote' + token_str)
r = requests.get(base_url+'/stock/EQINFY-IS/quote' + token_str)
"""
#r = requests.get(base_url+ sym_url + token_str)
#print(r.text)

import requests
import json
class IEXCloud:
    def __init__(self, sandbox=True):
        if sandbox:
            self.base_url = 'https://sandbox.iexapis.com/stable'
            self.token = 'Tpk_0a3b62f798054d58abd8a8c4f6502f2a'
        else:
            self.base_url = 'https://cloud.iexapis.com/stable'
            self.token='pk_749ebf5d985d4721b6d75fdac3865ac1'
        self.token_str = '?token='+self.token

    def get_region_list(self,tt):
        url = self.base_url + '/ref-data/exchanges' + self.token_str
        print(url)
        r = requests.get(url)
        print(r.text)

    def get_symbol_list(self):
        url = self.base_url + '/ref-data/exchange/XNSE/symbols' + self.token_str
        r = requests.get(url)
        print([k['symbol'] for k in json.loads(r.text)])

    def get_quote(self, symbol):
        ticker = 'EQ' + symbol + '-IS'
        quote_url = '/stock/' + ticker + '/quote'
        url = self.base_url + quote_url + self.token_str
        r = requests.get(url)
        print(r.text)

    def get_intraday_price(self, symbol):
        ticker = 'EQ' + symbol + '-IS'
        quote_url = '/stock/' + 'market' + '/upcoming-events'
        url = self.base_url + quote_url + self.token_str
        r = requests.get(url)
        print(r.text)

    def get_events(self, symbol):
        ticker = 'EQ' + symbol + '-IS'
        quote_url = '/stock/market/today-earnings' + self.token_str #+ '&exactDate=20220411'
        url = self.base_url + quote_url
        print(url)
        r = requests.get(url)
        print(r.text)

    def get_time_series(self):
        quote_url = '/time-series'
        url = self.base_url + quote_url + self.token_str
        r = requests.get(url)
        print(r.text)

    def get_news(self):
        quote_url = '/time-series/PREMIUM_CITYFALCON_NEWS/IN/'
        url = self.base_url + quote_url + self.token_str
        print(url)
        r = requests.get(url)
        print(r.text)

obj = IEXCloud(False)
# Get exchanges
#print(obj.get_region_list('fff'))

# Get symbols
print(obj.get_news())