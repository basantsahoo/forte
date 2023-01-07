import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

import asyncio
import socketio
from aiohttp import web
import aiohttp_cors
import rx
import rx.operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler
from datetime import datetime
import time
import pytz
import sys
from infrastructure.namespace.oms_ns import OMSNamespace
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
        if (now.hour == 8 and now.minute >= 45) or (now.hour == 9 and now.minute <= 15):
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

    ns = OMSNamespace('/oms')
    #ns_bt = BacktestFeedNamespace('/hist_feed')
    sio.register_namespace(ns)
    #sio.register_namespace(ns_bt)
    cors = aiohttp_cors.setup(app, defaults=settings.CROS_DEFAULTS)
    cors.add(app.router.add_resource("/"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8081)
    await site.start()
    ns.connect_feed()
    await refresh(ns)
    await asyncio.Event().wait()


asyncio.run(socketmain())
