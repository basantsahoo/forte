from infrastructure.namespace.algo_client import AlgoClient
import socketio
import pytz
from datetime import datetime

sio = socketio.Client(reconnection_delay=5)

def refresh(ns):
    #print('refresh 1')
    #loop = asyncio.get_running_loop()
    tz_ist = pytz.timezone('Asia/Kolkata')
    #clean_up = True
    while True:
        now = datetime.now(tz_ist)
        if (now.hour == 15 and now.minute >= 45) or (now.hour == 8 and now.minute >= 45):
            #print('refresh 2')
            #clean_up=False
            ns.refresh()
        sio.sleep(15*60)

async def start():
    ns = AlgoClient('/livefeed')
    sio.register_namespace(ns)
    task = sio.start_background_task(refresh, ns)
    ns.connect_feed()
    ns.connect_to_oms()


