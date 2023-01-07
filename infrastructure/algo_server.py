from infrastructure.namespace.algo_client import AlgoClient
import socketio
import pytz
from datetime import datetime
import time
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

def connect_to_oms():
    try:
        sio.connect('http://localhost:8081/', wait_timeout=100, auth={'internal_app_id': 'CALG136148'})
        #sio.emit('join_feed', default_symbols[0])
        print('oms connection success')
    except Exception as e:
        print('oms connection fail')
        print(e)
        time.sleep(2)
        connect_to_oms()


async def start():
    ns = AlgoClient('/oms')
    sio.register_namespace(ns)
    task = sio.start_background_task(refresh, ns)
    #ns.connect_feed()
    connect_to_oms()
    ns.connect_feed()


