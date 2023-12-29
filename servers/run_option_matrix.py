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

sio = socketio.Client(reconnection_delay=5)


async def start():
    ns = OptionMatrixClient('/oms')
    sio.register_namespace(ns)
    ns.connect_feed()

asyncio.run(start())