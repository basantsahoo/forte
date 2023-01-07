import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

import socketio
import asyncio
from aiohttp import web
import aiohttp_cors
import rx
import rx.operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler
from datetime import datetime
import time
import pytz

from infrastructure.namespace.live_tick import LiveFeedNamespace
from infrastructure.namespace.back_test_feed import BacktestFeedNamespace
import servers.server_settings as settings

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
            """
            for broker in ns.portfolio_manager.brokers:
                broker.refresh()
            """
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
    ns_bt = BacktestFeedNamespace('/histfeed')
    sio.register_namespace(ns)
    sio.register_namespace(ns_bt)
    cors = aiohttp_cors.setup(app, defaults=settings.CROS_DEFAULTS)
    cors.add(app.router.add_resource("/"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner)
    await site.start()
    await refresh(ns)
    if settings.live_feed:
        loop = asyncio.get_event_loop()
        """
        obs = rx.interval(31).pipe(ops.map(lambda i: i))
        obs.subscribe(on_next=lambda s: loop.create_task(send_profile_data()), scheduler=AsyncIOScheduler(loop))
        obs2 = rx.interval(30).pipe(ops.map(lambda i: i))
        obs2.subscribe(on_next=lambda s: loop.create_task(calculate()), scheduler=AsyncIOScheduler(loop))
        """
    await asyncio.Event().wait()
asyncio.run(socketmain())
