import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

import asyncio
from infrastructure.namespace.option_matrix_client import OptionMatrixClient
import socketio
import pytz
from datetime import datetime
import time
from servers.server_settings import oms_service

sio = socketio.Client(reconnection_delay=5)
full_week = False

async def start():
    ns = OptionMatrixClient('/oms', full_week=full_week)
    sio.register_namespace(ns)
    connect_to_oms()
    ns.connect_feed()


def connect_to_oms():
    try:
        sio.connect(oms_service, wait_timeout=100, auth={'internal_app_id': 'CALG136148'})
        #sio.emit('join_feed', default_symbols[0])
        print('oms connection success')
    except Exception as e:
        print('oms connection fail')
        print(e)
        time.sleep(2)
        connect_to_oms()



asyncio.run(start())