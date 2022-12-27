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
from market_client import MarketClient

class LiveFeedNamespace(socketio.AsyncNamespace):
    def __init__(self,namespace=None):
        socketio.AsyncNamespace.__init__(self, namespace)
        self.live_data_client = MarketClient()


    async def on_connect(self, sid,environ, auth={}):
        print('AUTH++++++++++++', auth)
        if not socket_auth_enabled or (socket_auth_enabled and self.is_authenticated(auth)):
            await self.emit('other_message', 'connection successful')
        else:
            raise socketio.exceptions.ConnectionRefusedError('authentication failed')


    def on_disconnect(self, sid):
        print('disconnect ', sid)


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

