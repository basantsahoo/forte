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
from website.market_profile_enabler import MarketProfileEnablerService, TickMarketProfileEnablerService
from arc.oms_portfolio import OMSPortfolioManager
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


class LiveFeedNamespace(socketio.AsyncNamespace):
    def __init__(self,namespace=None):
        socketio.AsyncNamespace.__init__(self,namespace)
        self.market_cache = Cache(reports_dir + 'market_cache')
        self.processor = TickMarketProfileEnablerService(market_cache=self.market_cache)
        self.option_processor = OptionProfileService(market_cache=self.market_cache)
        self.portfolio_manager = OMSPortfolioManager(place_live_orders=True, market_cache=self.market_cache)
        self.processor.socket = self
        self.option_processor.socket = self
        #print(self.market_cache.get('trends'))
        self.hist_insight = self.market_cache.get('hist_insight', [])
        self.latest_option_data = self.market_cache.get('latest_option_data', {})
        self.trends = {}

    def refresh(self):
        self.market_cache.set('hist_insight', [])
        self.market_cache.set('price_data', {})
        self.market_cache.set('option_data', {})

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


    async def on_connect(self, sid,environ, auth={}):
        print('AUTH++++++++++++', auth)
        if not socket_auth_enabled or (socket_auth_enabled and self.is_authenticated(auth)):
            await self.emit('other_message', 'connection successful')
        else:
            raise socketio.exceptions.ConnectionRefusedError('authentication failed')


    def on_disconnect(self, sid):
        print('disconnect ', sid)


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

async def index(request):
    return web.Response(text='good', content_type='text/html')


async def refresh(ns):
    #loop = asyncio.get_running_loop()
    tz_ist = pytz.timezone('Asia/Kolkata')
    while True:
        now = datetime.now(tz_ist)
        #print(now.hour)
        #print(now.minute)
        if (now.hour == 8 and now.minute >= 45) or (now.hour == 9 and now.minute <= 51):
            ns.refresh()
            ns.processor.refresh()

            for broker in ns.portfolio_manager.brokers:
                broker.refresh()

            ns.option_processor.refresh()
        await asyncio.sleep(15*60)
        #loop.stop()
        #sys.exit()


async def socketmain():
    sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True, cors_allowed_origins=settings.CROS_ALLOWED_ORIGINS)
    app = web.Application()
    sio.attach(app)
    app.router.add_get('/', index)

    ns = LiveFeedNamespace('/livefeed')
    #ns_bt = BacktestFeedNamespace('/hist_feed')
    sio.register_namespace(ns)
    #sio.register_namespace(ns_bt)
    cors = aiohttp_cors.setup(app, defaults=settings.CROS_DEFAULTS)
    cors.add(app.router.add_resource("/"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner)
    await site.start()
    await refresh(ns)
    if live_feed:
        loop = asyncio.get_event_loop()
        """
        obs = rx.interval(31).pipe(ops.map(lambda i: i))
        obs.subscribe(on_next=lambda s: loop.create_task(send_profile_data()), scheduler=AsyncIOScheduler(loop))
        obs2 = rx.interval(30).pipe(ops.map(lambda i: i))
        obs2.subscribe(on_next=lambda s: loop.create_task(calculate()), scheduler=AsyncIOScheduler(loop))
        """
    await asyncio.Event().wait()

