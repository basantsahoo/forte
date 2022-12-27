from truedata_ws.websocket.TD import TD
from truedata_ws.websocket.TD_chain import OptionChain
import pandas as pd
import infrastructure.truedata.settings as td_settings
from threading import Thread
import requests
from io import StringIO
import re
import numpy as np
from py_vollib_vectorized import price_dataframe, get_all_greeks
from py_vollib_vectorized import vectorized_implied_volatility
import pandas as pd
from datetime import datetime
from config import get_expiry_date
expiry_dt = get_expiry_date()
expiry = expiry_dt.strftime('%y%m%d')


class TDCustom(TD):
    _instance = None

    @staticmethod
    def getInstance():
        """Static Access Method"""
        if TDCustom._instance is None:
            TDCustom()
        return TDCustom._instance

    def __init__(self):

        if TDCustom._instance is not None:
            raise Exception ("This class is a singleton class !")
        else:
            def force_logout():
                url = 'https://api.truedata.in/logoutRequest?user=' + td_settings.user_name + '&password=' + td_settings.pass_word + '&port=' + str(td_settings.realtime_port)
                print(url)
                resp = requests.get(url).text

            force_logout()
            TD.__init__(self, td_settings.user_name, td_settings.pass_word, live_port=td_settings.realtime_port,historical_api=True)
            TDCustom._instance = self


    def start_option_chain(self, symbol, expiry, chain_length=None, bid_ask=False, market_open_post_hours=False):
        chain_length = 10 if chain_length is None else chain_length  # setting default value for chain length
        #print(self.get_n_historical_bars(f'{symbol}-I'))
        future_price = self.get_n_historical_bars(f'{symbol}-I')[0]['c']
        #print(future_price)
        try:
            chain = OptionChainCustom(self, symbol, expiry, chain_length, future_price, bid_ask, market_open_post_hours)
        except Exception as e:
            # traceback.print_exc()
            print(e)
            print(f'Please check symbol: {symbol} and its expiry: {expiry.date()}')
            exit()
        #print(chain.option_symbols)
        symb_ids = self.start_live_data(chain.option_symbols)
        option_thread = Thread(target=chain.update_chain, args=(self, symb_ids), daemon=True)
        option_thread.start()
        return chain


    def get_intraday_geeks(self, ticker, option_type="PE"):
        #self.get_all_expiries()
        ticker_index = 'NIFTY 50' if ticker == 'NIFTY' else 'NIFTY BANK' if 'BANK' in ticker else None
        flag = 'p' if option_type == 'PE' else 'c' if option_type == 'CE' else None
        index_spot_price = self.get_n_historical_bars(ticker_index, bar_size="tick")[0]['ltp']
        option_strike = round(index_spot_price / 100) * 100 + 100 if option_type == 'CE' else round(index_spot_price / 100) * 100 - 100 if option_type == 'PE' else round(index_spot_price / 100) * 100
        #print(option_strike)
        option_data = self.get_n_historical_bars(ticker + expiry + str(option_strike) + option_type, bar_size="1 min", no_of_bars=375)
        eod_time_to_expiry = self.get_time_to_expiry(option_data[0]['time'])
        spot_data = self.get_n_historical_bars(ticker_index, bar_size="1 min", no_of_bars=375)
        tim_to_expiry = [(x*60 + eod_time_to_expiry) / (365 * 24*3600) for x in range(len(spot_data))]
        r = 10 / 100
        #print(tim_to_expiry)
        iv_list = vectorized_implied_volatility([x['c'] for x in option_data], [x['c'] for x in spot_data], option_strike, tim_to_expiry, r, flag, return_as='array')
        greeks = get_all_greeks(flag, [x['c'] for x in spot_data], option_strike, tim_to_expiry, r, iv_list, model='black_scholes', return_as='dict')
        # print(greeks)
        df = pd.DataFrame()
        df['Time'] = [x['time'] for x in spot_data]
        df['Spot'] = [x['c'] for x in spot_data]
        df['Price'] = [x['c'] for x in option_data]
        df['IV'] = iv_list
        df['delta'] = greeks['delta']
        df['gamma'] = greeks['gamma']
        df['vega'] = greeks['vega']
        df['theta'] = greeks['theta']
        df = df.sort_values(['Time'], ascending=True)
        return df

    def get_all_expiries(self):
        b_url = 'https://api.truedata.in/getAllSymbols?segment=fut'
        chain_link = f'{b_url}&user={self.login_id}&password={self.password}&allexpiry=true&csv=true'
        print(chain_link)
        chain = requests.get(chain_link).text
        df = pd.read_csv(StringIO(chain), header=None)
        print(df.head().T)

    def get_time_to_expiry(self, from_time=None):
        option_expiry_time = expiry_dt.strftime('%Y-%m-%d') + " 15:30:00"
        end_ts = datetime.strptime(option_expiry_time, "%Y-%m-%d %H:%M:%S")
        diff = (end_ts-from_time).total_seconds()#-(24-6.25)*3600
        return diff


class OptionChainCustom(OptionChain):
    def get_strike_step(self):
        print('get_strike_step++++++++++++', self.symbol)
        if self.symbol in ['NIFTY', 'BANKNIFTY']:
            return 100
        else:
            expiry = self.expiry.strftime('%Y%m%d')
            chain_link = f'{OptionChain.chain_url}user={self.login_id}&password={self.password}&symbol={self.symbol}&expiry={expiry}&csv=true'
            chain = requests.get(chain_link).text
            df = pd.read_csv(StringIO(chain), header=None)
            df[1] = df[1].apply(lambda x: re.findall('\D+', x)[0])
            df = df[df[1] == self.symbol]
            strikes = np.sort(df[6].unique())
            step = strikes[1] - strikes[0];
            for i in range(2, len(strikes)):
                step = min(step, strikes[i] - strikes[i - 1]);
            return step