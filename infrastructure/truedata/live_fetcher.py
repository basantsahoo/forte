from copy import deepcopy
from infrastructure.truedata.custom import TDCustom
from datetime import datetime as dt
from datetime import  timedelta
import time

import socketio
import asyncio
import numpy as np

from py_vollib_vectorized import price_dataframe, get_all_greeks
from py_vollib_vectorized import vectorized_implied_volatility
from config import get_expiry_date, default_symbols, market_open_time, market_close_time, bank_nifty_constituents, nifty_constituents

import helper.utils as helper_utils
import sys
import os
import psutil
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

tz_ist = pytz.timezone('Asia/Kolkata')


"""
Truedata socket for servers tick
"""
sio = socketio.Client(reconnection_delay=5)
expiry_dt = get_expiry_date()
expiry = expiry_dt.strftime('%y%m%d')
fetcher_started = False
ns = None
class TrueDataLiveFeed(socketio.ClientNamespace):
    def __init__(self,namespace=None):
        socketio.ClientNamespace.__init__(self,namespace)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.td_scoket = None
        self.obs = None
        self.price_lst = []
        self.live_data_objs = {}
        self.spot_data = {}
        self.volume_data = {'NIFTY 50': 0, 'NIFTY BANK': 0}
        self.turn_over_data = {'NIFTY 50': 0, 'NIFTY BANK': 0}
        self.last_spot_time = dt.now()
        self.last_oc_time = dt.now()
    def socket_sending_response(self):
        resp = True
        time_now = dt.now()
        """
        print('calculate+++++')
        print(helper_utils.is_time_between(market_open_time, market_close_time))
        print((time_now-self.last_spot_time).total_seconds())
        print((time_now-self.last_oc_time).total_seconds())
        """
        if helper_utils.is_time_between(market_open_time, market_close_time) and (((time_now-self.last_spot_time).total_seconds() > 30) or ((time_now-self.last_oc_time).total_seconds() > 30)):
            resp = False
        return resp

    def price_received_live(self, feed):
        #print('spot_received_live')
        self.last_spot_time = dt.now()
        feed_d = feed.to_dict()
        #print(feed_d)
        feed_d['timestamp'] = feed_d['timestamp'].strftime('%Y-%m-%dT%H:%M:%S') if feed_d['timestamp'] is not None else feed_d['timestamp']
        if feed_d['symbol'] in self.volume_data:
            feed_d['volume'] = self.volume_data[feed_d['symbol']]
        try:
            self.emit('td_price_feed', feed_d)
        except Exception as e:
            print(e)
            print('Error sending data to server')

    def oc_received_live(self,ticker, feed):
        print('oc_received_live+++++++++++++++')
        self.last_oc_time = dt.now()
        feed['ltt'] = feed['ltt'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%S') if x is not None else x)
        feed_d = feed.to_dict('records')
        #print(feed_d)
        try:
            self.emit('td_oc_feed', {'symbol':ticker, 'options_data':feed_d})
        except Exception as e:
            print(e)
            print('Error sending data to server')

    def option_price_received_live(self,feed):
        print('option_price_received_live+++++++++++++++')
        try:
            self.emit('td_option_price_feed', feed)
        except Exception as e:
            print(e)
            print('Error sending option price data to server')

    def get_suitable_option(self, ticker, option_type):
        spot_price = self.spot_data[ticker]
        if option_type == 'CE':
            option_of_interest = round(spot_price / 100) * 100 + 100
        elif option_type == 'PE':
            option_of_interest = round(spot_price / 100) * 100 - 100
        return option_of_interest


    def calculate_option_geeks(self,  option_chain, ticker):
        #print(option_chain.shape)
        oc_middle_row = round(option_chain.shape[0]/2)
        ltt = option_chain['ltt'].iloc[oc_middle_row]
        option_chain['flag'] = option_chain['type'].apply(lambda x: 'p' if x == 'PE' else 'c')
        spot_price = self.spot_data[ticker]
        tim_to_expiry = self.td_scoket.get_time_to_expiry(ltt)/(3600*24*365) #(6.25*1+6*24)/(365*24*3600)
        r = 10 / 100
        # print(tim_to_expiry)
        iv_p = vectorized_implied_volatility(option_chain['ltp'].to_list(), spot_price, option_chain['strike'].to_list() , tim_to_expiry, r, option_chain['flag'].to_list(), return_as='array')
        greeks = get_all_greeks(option_chain['flag'].to_list(), spot_price, option_chain['strike'].to_list(), tim_to_expiry, r, iv_p, model='black_scholes', return_as='dict')
        option_chain = option_chain[['strike','type','ltp','ltq','ltt', 'volume','price_change','oi','prev_oi', 'oi_change', 'bid', 'ask']]
        #print(greeks)
        #option_chain.loc[:, ['delta']] = greeks['delta']
        option_chain['ltt'] = ltt
        option_chain['IV'] = np.array(iv_p).tolist()
        option_chain['delta'] = np.array(greeks['delta']).tolist()
        option_chain['gamma'] = np.array(greeks['gamma']).tolist()
        option_chain['vega'] = np.array(greeks['vega']).tolist()
        option_chain['theta'] = np.array(greeks['theta']).tolist()

        return option_chain

    async def true_data_connect(self):
        print('True data connect +++++++++++++++++++++++++++++++++++')
        self.td_scoket = TDCustom.getInstance()
        symbols = [helper_utils.get_nse_index_symbol(symbol) for symbol in default_symbols]

        print('Starting Real Time Feed.... ')
        req_ids = self.td_scoket.start_live_data(symbols)
        all_index_futs = ['NIFTY-I', 'BANKNIFTY-I']
        req_id_futs = self.td_scoket.start_live_data(all_index_futs)
        time.sleep(1)
        nifty_chain = self.td_scoket.start_option_chain(helper_utils.get_oc_symbol('NIFTY'), expiry_dt, chain_length=20, bid_ask=True)
        bnf_chain = self.td_scoket.start_option_chain(helper_utils.get_oc_symbol('BANKNIFTY'), expiry_dt, chain_length=30, bid_ask=True)
        time.sleep(1)
        self.live_data_objs['NIFTY'] = nifty_chain.get_option_chain().to_dict('records')
        self.live_data_objs['BANKNIFTY'] = bnf_chain.get_option_chain().to_dict('records')
        #print('about here')
        #print(bnf_chain.get_option_chain())

        for req_id in req_ids:
            self.live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
            self.spot_data[self.td_scoket.live_data[req_id].to_dict()['symbol']] = self.td_scoket.live_data[req_id].to_dict()['ltp']
            print(f'touchlinedata -> {self.td_scoket.touchline_data[req_id]}')
            self.price_received_live(self.td_scoket.live_data[req_id])
        """
        for req_id in req_id_stocks:
            self.live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
            self.spot_data[self.td_scoket.live_data[req_id].to_dict()['symbol']] = self.td_scoket.live_data[req_id].to_dict()['ltp']
            print(f'touchlinedata -> {self.td_scoket.touchline_data[req_id]}')
            self.price_received_live(self.td_scoket.live_data[req_id])
        """
        while self.td_scoket is not None:
            if not self.socket_sending_response():
                restart_process()

            for req_id in req_ids:
                if not self.td_scoket.live_data[req_id] == self.live_data_objs[req_id]:
                    self.live_data_objs[req_id] = deepcopy(self.td_scoket.live_data[req_id])
                    self.spot_data[self.td_scoket.live_data[req_id].to_dict()['symbol']] = self.td_scoket.live_data[req_id].to_dict()['ltp']
                    self.price_received_live(self.td_scoket.live_data[req_id])
            for req_id in req_id_futs:
                stock_last_tick = self.td_scoket.live_data[req_id].to_dict()
                if stock_last_tick['symbol'] == 'BANKNIFTY-I':
                    turn_over = stock_last_tick['turnover'] if stock_last_tick['turnover'] is not None else 0
                    last_turn_over = self.turn_over_data['NIFTY BANK']
                    volume_delta = round((turn_over - last_turn_over) / stock_last_tick['ltp'])
                    self.volume_data['NIFTY BANK'] = self.volume_data['NIFTY BANK'] + volume_delta
                    self.turn_over_data['NIFTY BANK'] = turn_over
                if stock_last_tick['symbol'] == 'NIFTY-I':
                    turn_over = stock_last_tick['turnover'] if stock_last_tick['turnover'] is not None else 0
                    last_turn_over = self.turn_over_data['NIFTY 50']
                    volume_delta = round((turn_over - last_turn_over) / stock_last_tick['ltp'])
                    self.volume_data['NIFTY 50'] = self.volume_data['NIFTY 50'] + volume_delta
                    self.turn_over_data['NIFTY 50'] = turn_over

            latest_nifty_chain = nifty_chain.get_option_chain()
            #print('latest_nifty_chain++++++++++++++')
            #print(latest_nifty_chain.to_dict('records'))
            #print(latest_nifty_chain.head().T)
            latest_bank_nifty_chain = bnf_chain.get_option_chain()
            #print(latest_bank_nifty_chain)
            if not latest_nifty_chain.to_dict('records') == self.live_data_objs['NIFTY']:
                nifty_call_strike_suitable = self.get_suitable_option(helper_utils.get_nse_index_symbol('NIFTY'), 'CE')
                nifty_put_strike_suitable = self.get_suitable_option(helper_utils.get_nse_index_symbol('NIFTY'), 'PE')
                bank_nifty_call_strike_suitable = self.get_suitable_option(helper_utils.get_nse_index_symbol('BANKNIFTY'), 'CE')
                bank_nifty_put_strike_suitable = self.get_suitable_option(helper_utils.get_nse_index_symbol('BANKNIFTY'), 'PE')
                try:
                    #print(latest_nifty_chain[15:20].T)
                    nifty_call_price = latest_nifty_chain[(latest_nifty_chain['strike'] == str(nifty_call_strike_suitable)) & (latest_nifty_chain['type'] == 'CE')]['ltp'].to_list()[0]
                    nifty_put_price = latest_nifty_chain[(latest_nifty_chain['strike'] == str(nifty_put_strike_suitable)) & (latest_nifty_chain['type'] == 'PE')]['ltp'].to_list()[0]
                    bank_nifty_call_price = latest_bank_nifty_chain[(latest_bank_nifty_chain['strike'] == str(bank_nifty_call_strike_suitable)) & (latest_bank_nifty_chain['type'] == 'CE')]['ltp'].to_list()[0]
                    bank_nifty_put_price = latest_bank_nifty_chain[(latest_bank_nifty_chain['strike'] == str(bank_nifty_put_strike_suitable)) & (latest_bank_nifty_chain['type'] == 'PE')]['ltp'].to_list()[0]

                    option_prices = [['NIFTY_CE', nifty_call_strike_suitable, nifty_call_price, self.spot_data[helper_utils.get_nse_index_symbol('NIFTY')], expiry],
                                     ['NIFTY_PE', nifty_put_strike_suitable, nifty_put_price, self.spot_data[helper_utils.get_nse_index_symbol('NIFTY')], expiry],
                                     ['BANKNIFTY_CE', bank_nifty_call_strike_suitable, bank_nifty_call_price,
                                      self.spot_data[helper_utils.get_nse_index_symbol('BANKNIFTY')], expiry],
                                     ['BANKNIFTY_PE', bank_nifty_put_strike_suitable, bank_nifty_put_price,
                                      self.spot_data[helper_utils.get_nse_index_symbol('BANKNIFTY')], expiry]]
                    #print(option_prices)
                    self.option_price_received_live(option_prices)
                except Exception as e:
                    print(e)
                self.live_data_objs['NIFTY'] = latest_nifty_chain.to_dict('records')
                self.live_data_objs['BANKNIFTY'] = latest_bank_nifty_chain.to_dict('records')
                if latest_nifty_chain.shape[0] > 0:
                    latest_nifty_chain = self.calculate_option_geeks(latest_nifty_chain, helper_utils.get_nse_index_symbol('NIFTY'))
                    self.oc_received_live('NIFTY', latest_nifty_chain)
                if latest_bank_nifty_chain.shape[0] > 0:
                    latest_bank_nifty_chain = self.calculate_option_geeks(latest_bank_nifty_chain, helper_utils.get_nse_index_symbol('BANKNIFTY'))
                    self.oc_received_live('BANKNIFTY', latest_bank_nifty_chain)

                #latest_bank_nifty_chain = self.calculate_option_geeks(latest_bank_nifty_chain, 'NIFTY BANK')
            time.sleep(0.5)

    def on_connect(self):
        #global counter
        #counter += 1
        #print('counter on_connect', counter)
        print('I am connected')
        if self.td_scoket is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            #print(self.td_scoket)
            if self.td_scoket is None:
                self.loop.run_until_complete(self.true_data_connect())
        print('I am connected asw ell')

    def on_disconnect(self):
        print('disconnect++++++++++++++++++++++++++++++++++')
        """
        self.td_scoket.disconnect()
        self.td_scoket = None
        print(self.td_scoket)
        """

def connect_to_server():
    #global counter
    #counter +=1
    #print('counter connect_to_server', counter)
    try:
        sio.connect('http://localhost:8080/',  wait_timeout=100, auth={'internal_app_id':'FEEDTD136148'})
        fetcher_started = True
        print('connection success')
    except Exception as e:
        print('connection fail')
        print(e)
        time.sleep(2)
        connect_to_server()


def start_fetcher():
    global ns
    ns = TrueDataLiveFeed('/livefeed')
    sio.register_namespace(ns)
    connect_to_server()




def restart_process():
    global ns
    print("argv was", sys.argv)
    print("sys.executable was", sys.executable)
    print("restart now")
    if ns.td_scoket is not None:
        ns.td_scoket.disconnect()
    ns = None
    try:
        #print(os.getpid())
        #print(psutil.Process(os.getpid()))
        p = psutil.Process(os.getpid())
        #print(p.open_files())
        #print(p.connections())

        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        print(e)
    time.sleep(10)
    os.execv(sys.executable, ['python3'] + sys.argv)

def check_running_scheduler(scheduler):
    schl = dt.now(tz_ist) + timedelta(minutes=1)
    if helper_utils.is_time_between(market_open_time, market_close_time):
        scheduler.add_job(start_fetcher, 'cron', day_of_week='mon-fri', hour=schl.hour, minute=schl.minute)

def start():
    #
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Asia/Kolkata'}, use_reloader=False)
    check_running_scheduler(scheduler)
    scheduler.add_job(restart_process, 'cron', day_of_week='mon-fri', hour='8', minute='45')
    scheduler.add_job(start_fetcher, 'cron', day_of_week='mon-sat', hour='22', minute='33')
    scheduler.add_job(restart_process, 'cron', day_of_week='mon-fri', hour='16', minute='46')
    #scheduler.add_job(restart_process, 'cron', day_of_week='mon-fri', hour='16', minute='55') #Do twice

    scheduler.start()
    while True:
        pass

