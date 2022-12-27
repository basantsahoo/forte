import requests
import json
import pandas as pd


class EODCloud:
    def __init__(self, sandbox=True):
        self.base_url = 'https://eodhistoricaldata.com/api/'
        self.exchange_end_point = 'exchanges-list/'
        self.token = '6253abd923d977.07185416'
        self.token_str = '?api_token=' + self.token
        self.nse_suffix = '.NSE'

    def get_exchange_list(self):
        url = self.base_url + self.exchange_end_point + self.token_str
        print(url)
        r = requests.get(url)
        print(r.text)

    def get_ticker_list(self):
        url = self.base_url + 'exchange-symbol-list/NSE' + self.token_str
        print(url)
        r = requests.get(url)
        print(r.text)

    def get_exchange_details(self):
        url = self.base_url + 'exchange-details/NSE' + self.token_str + '&from=2022-04-17'
        print(url)
        r = requests.get(url)
        resp = json.loads(r.text)
        holidays = [day['Date'] for day in resp['ExchangeHolidays'].values()]
        print(holidays)

    def get_economic_events(self):
        url = self.base_url + 'economic-events/' + self.token_str + '&from=2022-04-01' +'&to=2022-04-30' + '&country=IN'
        print(url)
        r = requests.get(url)
        resp = json.loads(r.text)
        # holidays = [day['Date'] for day in resp['ExchangeHolidays'].values()]
        print(resp)

    def get_calendar_events(self):
        url = self.base_url + 'calendar/earnings' + self.token_str + '&from=2022-04-25' + '&to=2022-04-25'
        print(url)
        r = requests.get(url)
        data = pd.read_csv(url)
        data = data[data['Currency'] == 'INR']
        print(data)

    def get_fundamental_data(self):
        url = self.base_url + 'fundamentals/INFY.NSE' + self.token_str
        print(url)
        r = requests.get(url)
        print(r.text)

    def get_index_const(self):
        url = self.base_url + 'fundamentals/NSEBANK.INDX' + self.token_str
        url = self.base_url + 'fundamentals/NSEI.INDX' + self.token_str
        # https://eodhistoricaldata.com/financial-apis/list-supported-indices/



obj = EODCloud()
# Get exchanges
print(obj.get_calendar_events())

