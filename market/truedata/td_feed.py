from truedata_ws.websocket.TD import TD
from truedata_ws.websocket.TD_chain import OptionChain
from copy import deepcopy
import pandas as pd
from datetime import date
import truedata.settings as  td_settings
from truedata.custom import TDCustom
from datetime import datetime as dt
from threading import Thread
import socketio
import asyncio
import time
import requests
from io import StringIO
import re
import numpy as np
from settings import expiry_dt
"""
Fyers socket for live tick
"""
default_symbols = ['NSE:NIFTY50-INDEX', 'NSE:NIFTYBANK-INDEX']
live_feed = True
sio = socketio.Client(reconnection_delay=5)

class TrueDataLiveFeed(socketio.ClientNamespace):
    def __init__(self,namespace=None):
        socketio.ClientNamespace.__init__(self,namespace)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.td_scoket = None
        self.obs = None
        self.price_lst = []


    def price_received_live(self,feed):

        feed_d = feed.to_dict()
        #print(feed_d)
        feed_d['timestamp'] = feed_d['timestamp'].strftime('%Y-%m-%dT%H:%M:%S') if feed_d['timestamp'] is not None else feed_d['timestamp']
        try:
            self.emit('td_price_feed', feed_d)
        except Exception as e:
            print(e)
            print('Error sending data to server')

    def oc_received_live(self,feed):
        print('oc_received_live+++++++++++++++')
        feed['ltt'] = feed['ltt'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%S') if x is not None else x)
        feed_d = feed.to_dict('records')
        #print(feed_d)
        try:
            self.emit('td_oc_feed', feed_d)
        except Exception as e:
            print(e)
            print('Error sending data to server')

    def option_price_received_live(self,feed):
        try:
            self.emit('td_option_price_feed', feed)
        except Exception as e:
            print(e)
            print('Error sending option price data to server')

    async def true_data_connect_2(self):
        print('True data connect +++++++++++++++++++++++++++++++++++')

        self.td_scoket = TDCustom.getInstance()
        symbols = ["NIFTY 50", "NIFTY BANK"]

        print('Starting Real Time Feed.... ')
        #print(f'Port > {realtime_port}')
        req_ids = self.td_scoket.start_live_data(symbols)
        #print(req_ids)
        live_data_objs = {}

        time.sleep(1)
        nifty_chain = self.td_scoket.start_option_chain('NIFTY', expiry_dt, chain_length=12, bid_ask=True)
        bnf_chain = self.td_scoket.start_option_chain('BANKNIFTY', expiry_dt, chain_length=20, bid_ask=True)
        live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
        live_data_objs['BANKNIFTY'] = bnf_chain.get_option_chain().to_dict('records')
        #print(bnf_chain.get_option_chain())


        for req_id in req_ids:
            live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
            #print(f'touchlinedata -> {td_app.touchline_data[req_id]}')
            self.price_received_live(self.td_scoket.live_data[req_id])
        oc_send = False
        while self.td_scoket is not None:
            for req_id in req_ids:
                if not self.td_scoket.live_data[req_id] == live_data_objs[req_id]:
                    live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
                    self.price_received_live(self.td_scoket.live_data[req_id])
            nifty_future_price = self.td_scoket.get_n_historical_bars('NIFTY 50', bar_size="tick")[0]['ltp']
            banknifty_future_price = self.td_scoket.get_n_historical_bars('NIFTY BANK', bar_size="tick")[0]['ltp']
            #print(self.td_scoket.get_n_historical_bars('BANKNIFTY22050536100CE', bar_size="tick", no_of_bars=1)[0]['ltp'])
            print(nifty_future_price, banknifty_future_price)
            #expiry_dt = dt(2022, 5, 12)
            expiry = expiry_dt.strftime('%y%m%d')
            """
            expiry = dt(2022, 5, 5).strftime('%y%m%d')
            tick_url = 'https://history.truedata.in/getlastnticks?'
            chain_link = f'{tick_url}symbol=BANKNIFTY22050535900PE&nticks=1&response=json&interval=tick'
            print(chain_link)
            chain = requests.get(chain_link).text
            print(chain)
            """
            if not nifty_chain.get_option_chain().to_dict('records') == live_data_objs['NIFTY']:
                nifty_call_of_interest = round(nifty_future_price / 100) * 100 + 100
                nifty_put_of_interest = round(nifty_future_price / 100) * 100 - 100
                bank_nifty_call_of_interest = round(banknifty_future_price / 100) * 100 + 100
                bank_nifty_put_of_interest = round(banknifty_future_price / 100) * 100 - 100
                """
                df =  nifty_chain.get_option_chain()
                nifty_call_price = df[(df['strike'] == str(nifty_call_of_interest)) & (df['type'] == 'CE')]['ltp'].to_list()[0]
                nifty_put_price = df[(df['strike'] == str(nifty_put_of_interest)) & (df['type'] == 'PE')]['ltp'].to_list()[0]
                df =  bnf_chain.get_option_chain()
                #print(df)
                bank_nifty_call_price = df[(df['strike'] == str(bank_nifty_call_of_interest)) & (df['type'] == 'CE')]['ltp'].to_list()[0]
                bank_nifty_put_price = df[(df['strike'] == str(bank_nifty_put_of_interest)) & (df['type'] == 'PE')]['ltp'].to_list()[0]
                """
                """
                print(nifty_put_of_interest)
                put_data = self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_put_of_interest) +'PE', bar_size="1 min", no_of_bars=375)
                spot_data = self.td_scoket.get_n_historical_bars('NIFTY-I', bar_size="1 min", no_of_bars=375)
                call_data = self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_call_of_interest) + 'CE', bar_size="1 min", no_of_bars=375)
                #print([x['c'] for x in data])
                #print(data)
                tim_to_expiry = [((x+5)/60 + 1 * 24) / (365 * 24) for x in range(len(spot_data))]
                r = 10/100
                #print(tim_to_expiry)
                from py_vollib_vectorized import price_dataframe, get_all_greeks
                from py_vollib_vectorized import vectorized_implied_volatility
                import pandas as pd
                iv_p = vectorized_implied_volatility([x['c'] for x in put_data], [x['c'] for x in spot_data], nifty_put_of_interest, tim_to_expiry, r, 'p', return_as='array')
                greeks = get_all_greeks('p', [x['c'] for x in spot_data], nifty_put_of_interest, tim_to_expiry, r, iv_p, model='black', return_as='dict')
                #print(greeks)
                df = pd.DataFrame()
                df['Spot'] = [x['c'] for x in spot_data]
                df['Price'] = [x['c'] for x in put_data]
                df['IV'] = iv_p
                df['delta'] = greeks['delta']
                df['gamma'] = greeks['gamma']
                df['vega'] = greeks['vega']
                df['theta'] = greeks['theta']
                df.to_csv("IV_analysis_put_5_min.csv")
                
                iv_c = vectorized_implied_volatility([x['c'] for x in call_data], [x['c'] for x in spot_data], nifty_call_of_interest, tim_to_expiry, r, 'c', return_as='array')
                greeks = get_all_greeks('c', [x['c'] for x in spot_data], nifty_call_of_interest, tim_to_expiry, r, iv_c, model='black', return_as='dict')
                #print(greeks)
                df = pd.DataFrame()
                df['Spot'] = [x['c'] for x in spot_data]
                df['Price'] = [x['c'] for x in call_data]
                df['IV'] = iv_c
                df['delta'] = greeks['delta']
                df['gamma'] = greeks['gamma']
                df['vega'] = greeks['vega']
                df['theta'] = greeks['theta']
                df.to_csv("IV_analysis_call_5_min.csv")
                """

                nifty_call_price =  self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_call_of_interest) +'CE', bar_size="tick", no_of_bars=1)[0]['ltp']
                nifty_put_price = self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_put_of_interest) +'PE', bar_size="tick", no_of_bars=1)[0]['ltp']
                bank_nifty_call_price = self.td_scoket.get_n_historical_bars('BANKNIFTY' + expiry + str(bank_nifty_call_of_interest) +'CE', bar_size="tick", no_of_bars=1)[0]['ltp']
                bank_nifty_put_price = self.td_scoket.get_n_historical_bars('BANKNIFTY' + expiry + str(bank_nifty_put_of_interest) +'PE', bar_size="tick", no_of_bars=1)[0]['ltp']
                option_prices = [['NIFTY_CE', nifty_call_of_interest, nifty_call_price, nifty_future_price, expiry],
                ['NIFTY_PE', nifty_put_of_interest, nifty_put_price, nifty_future_price, expiry],
                ['BANKNIFTY_CE', bank_nifty_call_of_interest, bank_nifty_call_price, banknifty_future_price, expiry],
                ['BANKNIFTY_PE', bank_nifty_put_of_interest, bank_nifty_put_price, banknifty_future_price,expiry]]
                self.option_price_received_live(option_prices)

                now = dt.now()
                if now.minute % 2 == 1:
                    oc_send = True
                if now.minute % 2 == 0 and oc_send:
                    oc_send = False
                    live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
                    self.oc_received_live(nifty_chain.get_option_chain())
            time.sleep(0.1)

    async def true_data_connect(self):
        print('True data connect +++++++++++++++++++++++++++++++++++')

        self.td_scoket = TDCustom.getInstance()
        symbols = ["NIFTY 50", "NIFTY BANK"]

        print('Starting Real Time Feed.... ')
        # print(f'Port > {realtime_port}')
        req_ids = self.td_scoket.start_live_data(symbols)
        # print(req_ids)
        live_data_objs = {}
        time.sleep(1)
        nifty_chain = self.td_scoket.start_option_chain('NIFTY', expiry_dt, chain_length=12, bid_ask=True)
        bnf_chain = self.td_scoket.start_option_chain('BANKNIFTY', expiry_dt, chain_length=20, bid_ask=True)
        live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
        live_data_objs['BANKNIFTY'] = bnf_chain.get_option_chain().to_dict('records')
        # print(bnf_chain.get_option_chain())

        for req_id in req_ids:
            live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
            #print(f'touchlinedata -> {self.td_scoket.touchline_data[req_id]}')
            self.price_received_live(self.td_scoket.live_data[req_id])

        while self.td_scoket is not None:
            for req_id in req_ids:
                if True:#not self.td_scoket.live_data[req_id] == live_data_objs[req_id]:
                    live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
                    self.price_received_live(self.td_scoket.live_data[req_id])
            #nifty_future_price = self.td_scoket.get_n_historical_bars('NIFTY 50', bar_size="tick")[0]['ltp']
            #banknifty_future_price = self.td_scoket.get_n_historical_bars('NIFTY BANK', bar_size="tick")[0]['ltp']
            # print(self.td_scoket.get_n_historical_bars('BANKNIFTY22050536100CE', bar_size="tick", no_of_bars=1)[0]['ltp'])
            #print(nifty_future_price, banknifty_future_price)
            # expiry_dt = dt(2022, 5, 12)
            expiry = expiry_dt.strftime('%y%m%d')
            if True:#not nifty_chain.get_option_chain().to_dict('records') == live_data_objs['NIFTY']:
                """
                nifty_call_of_interest = round(nifty_future_price / 100) * 100 + 100
                nifty_put_of_interest = round(nifty_future_price / 100) * 100 - 100
                bank_nifty_call_of_interest = round(banknifty_future_price / 100) * 100 + 100
                bank_nifty_put_of_interest = round(banknifty_future_price / 100) * 100 - 100


                nifty_call_price = \
                self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_call_of_interest) + 'CE',
                                                     bar_size="tick", no_of_bars=1)[0]['ltp']
                nifty_put_price = \
                self.td_scoket.get_n_historical_bars('NIFTY' + expiry + str(nifty_put_of_interest) + 'PE',
                                                     bar_size="tick", no_of_bars=1)[0]['ltp']
                bank_nifty_call_price = \
                self.td_scoket.get_n_historical_bars('BANKNIFTY' + expiry + str(bank_nifty_call_of_interest) + 'CE',
                                                     bar_size="tick", no_of_bars=1)[0]['ltp']
                bank_nifty_put_price = \
                self.td_scoket.get_n_historical_bars('BANKNIFTY' + expiry + str(bank_nifty_put_of_interest) + 'PE',
                                                     bar_size="tick", no_of_bars=1)[0]['ltp']
                option_prices = [['NIFTY_CE', nifty_call_of_interest, nifty_call_price, nifty_future_price, expiry],
                                 ['NIFTY_PE', nifty_put_of_interest, nifty_put_price, nifty_future_price, expiry],
                                 ['BANKNIFTY_CE', bank_nifty_call_of_interest, bank_nifty_call_price,
                                  banknifty_future_price, expiry],
                                 ['BANKNIFTY_PE', bank_nifty_put_of_interest, bank_nifty_put_price,
                                  banknifty_future_price, expiry]]
                self.option_price_received_live(option_prices)
                """

                live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
                self.oc_received_live(nifty_chain.get_option_chain())
                """
                now = dt.now()
                if now.minute % 2 == 1:
                    oc_send = True
                if now.minute % 2 == 0 and oc_send:
                    oc_send = False
                    live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
                    self.oc_received_live(nifty_chain.get_option_chain())
                """
            time.sleep(0.1)

    def on_connect(self):
        #global counter
        #counter += 1
        #print('counter on_connect', counter)
        print('I am connected')
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        #print(self.td_scoket)
        if live_feed:
            if self.td_scoket is None:
                self.loop.run_until_complete(self.true_data_connect())
        print('I am connected asw ell')

    def on_disconnect(self):
        print('disconnect')
        if live_feed:
            self.td_scoket.disconnect()
            self.td_scoket = None
        else:
            #self.obs.run()
            self.obs = None
        print(self.td_scoket)


def connect_to_server():
    #global counter
    #counter +=1
    #print('counter connect_to_server', counter)
    try:
        sio.connect('http://localhost:8080/',  wait_timeout=100)
        print('connection success')
    except Exception as e:
        print('connection fail')
        print(e)
        time.sleep(2)
        connect_to_server()




def start():
    #global counter
    #counter +=1
    #print('counter start', counter)

    ns = TrueDataLiveFeed('/livefeed')
    sio.register_namespace(ns)
    connect_to_server()



def run():
    # Default production port is 8082 in the library. Other ports may be given to you during trial.
    realtime_port = 8082

    td_app = TD(td_settings.user_name, td_settings.pass_word, live_port=td_settings.realtime_port, historical_api=True)


    symbols = ["NIFTY 50","NIFTY BANK"]

    print('Starting Real Time Feed.... ')
    print(f'Port > {realtime_port}')

    req_ids = td_app.start_live_data(symbols)
    print(req_ids)
    live_data_objs = {}

    time.sleep(1)
    nifty_chain = td_app.start_option_chain('NIFTY', dt(2022, 5, 5), chain_length=10, bid_ask=True)
    print(nifty_chain.get_option_chain())

    for req_id in req_ids:
        live_data_objs[req_id] = deepcopy(td_app.live_data[req_id])
        print(f'touchlinedata -> {td_app.touchline_data[req_id]}')

    while True:
        for req_id in req_ids:
            if not td_app.live_data[req_id] == live_data_objs[req_id]:
                print(td_app.live_data[req_id])  # your code in the previous version had a  print(td_app.live_data[req_id]).__dict__ here.
                live_data_objs[req_id] = deepcopy(td_app.live_data[req_id])
        print(nifty_chain.get_option_chain())

