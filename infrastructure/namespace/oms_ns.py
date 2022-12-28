import socketio
import asyncio
from aiohttp import web
import aiohttp_cors
import rx
import rx.operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler
import json
import numpy as np
import math
from datetime import datetime
from collections import OrderedDict
import time
import pytz
import sys
from infrastructure.arc.oms_portfolio import OMSPortfolioManager
from infrastructure.market_profile_enabler import TickMarketProfileEnablerService

from profile.options_profile import OptionProfileService
from profile.utils import NpEncoder, get_tick_size
from db.market_data import get_daily_tick_data
import settings
from config import live_feed, place_live_orders, socket_auth_enabled, allowed_apps
import helper.utils as helper_utils
from py_vollib_vectorized import price_dataframe
from config import get_expiry_date, rest_api_url
import requests
from settings import reports_dir
from diskcache import Cache
option_rooms = [helper_utils.get_options_feed_room('NIFTY'), helper_utils.get_options_feed_room('BANKNIFTY')]
from infrastructure.namespace.market_client import MarketClient

class OMSNamespace(socketio.AsyncNamespace):
    def __init__(self,namespace=None):
        socketio.AsyncNamespace.__init__(self, namespace)
        self.c_sio = socketio.Client(reconnection_delay=5)
        ns = MarketClient('/livefeed')
        self.c_sio.register_namespace(ns)
        self.market_cache = Cache(reports_dir + 'oms_cache')
        self.portfolio_manager = OMSPortfolioManager(place_live_orders=True, market_cache=self.market_cache)
        self.processor = TickMarketProfileEnablerService(market_cache=self.market_cache)
        self.processor.socket = self

    def is_authenticated(self, auth):
        app_id = auth.get('internal_app_id', '')
        if app_id in allowed_apps:
            return True
        token = auth.get('token', '')
        token = token.replace('JWT ', '')
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({"token": token})
        response = requests.post(rest_api_url + 'auth/verify-token', data=data, headers = headers)
        if response.status_code == 200:
            return True
        else:
            return False

    def connect_feed(self):
        try:
            self.c_sio.connect('http://localhost:8080/', wait_timeout=100, auth={'internal_app_id': 'FEEDTD136148'})
            fetcher_started = True
            print('fetcher success')
        except Exception as e:
            print('connection fail')
            print(e)
            time.sleep(2)
            self.connect_feed()

    async def on_connect(self, sid,environ, auth={}):
        print('AUTH++++++++++++', auth)
        if not socket_auth_enabled or (socket_auth_enabled and self.is_authenticated(auth)):
            await self.emit('other_message', 'connection successful')
        else:
            raise socketio.exceptions.ConnectionRefusedError('authentication failed')

    def on_disconnect(self, sid):
        print('disconnect ', sid)

    async def on_tick_data(self, sid, feed):
        print('td feed received')
        feed['symbol'] = helper_utils.root_symbol(feed['symbol'])
        epoch_tick_time = int(datetime.fromisoformat(feed['timestamp'] + '+05:30').timestamp())
        feed['timestamp'] = epoch_tick_time
        feed['min_volume'] = feed['volume'] if 'volume' in feed else 0
        self.option_processor.process_spot_data(feed)
        item = self.processor.process_input_data(feed)
        print(item)
        await self.emit('tick_data', {item['timestamp']: item}, room=item['symbol'])
        ley_list = ['symbol', 'ltp', "day_high", "day_low", "volume"]
        feed_small = {key: feed[key] for key in ley_list if key in feed}
        print(feed_small)
        for room in option_rooms:
            await self.emit('spot_data', feed_small, room=room)
        self.market_cache.set(item['symbol'], item) #3 Gets overwritten

    async def on_join_oms(self, sid):
        print('join oms successful')
        await self.update_position_to_user(sid)

    async def update_position_to_user(self, sid):
        positions = self.portfolio_manager.get_positions()
        await self.emit('position_update', json.dumps(positions, cls=NpEncoder), room=sid)

    async def on_exit_oms(self, sid):
        print('exit oms successful')

    async def on_place_oms_entry_order(self, sid, order_info):
        print('on_place_oms_order in socket')
        resp = self.portfolio_manager.place_entry_order(order_info)

    async def on_place_oms_exit_order(self, sid, order_info):
        print('on_place_oms_exit_order in socket')
        resp = self.portfolio_manager.place_exit_order(order_info)
        await self.emit('oms_exit_success', resp, room=sid)

    async def on_place_order(self, sid, orders):
        print("ORDER PLACE BY USER", orders)
        formated_orders = []
        for order in orders:

            last_info = self.processor.get_last_info(order['symbol'])
            print('last_info================', last_info)
            order['underlying_price'] = last_info['price']
            order['time'] = last_info['time']
            formated_orders.append(order)
        #print(last_info)
        self.portfolio_manager.manual_signal(formated_orders)
        await self.update_position_to_user(sid)

    async def on_close_position(self, sid, close_orders):
        print("Position closed BY USER", close_orders)
        formated_orders = []
        id = close_orders['id']
        orders = close_orders['positions']
        for order in orders:
            last_info = self.processor.get_last_info(order['symbol'])
            order['underlying_price'] = last_info['price']
            order['time'] = last_info['time']
            formated_orders.append(order)
        #print(last_info)
        self.portfolio_manager.close_manual_position(id,formated_orders)
        await self.update_position_to_user(sid)

    async def on_clear_position(self, sid, close_orders):
        print("Position clear BY USER", close_orders)
        id = close_orders['id']
        self.portfolio_manager.clear_manual_position(id)
        await self.update_position_to_user(sid)