import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

import asyncio
from infrastructure.oms_server import socketmain

asyncio.run(socketmain())
