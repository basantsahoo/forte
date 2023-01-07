import aiohttp_cors
from pathlib import Path
from datetime import datetime
CROS_ALLOWED_ORIGINS =['http://localhost:4200', 'http://localhost:8080', 'http://localhost:8000', 'http://localhost:8081', 'http://api.niftybull.in:8080']

CROS_DEFAULTS={
    "http://localhost:4200": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        ),
"http://localhost:8080": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        ),
"http://localhost:8000": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        ),

"http://localhost:8081": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        ),

"http://api.niftybull.in:8080": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        )
}

live_feed = True
chromedriver = './executables/chromedriver'
market_profile_db = './data/market_profile.db'
cache_dir = str(Path(__file__).parent.parent) + '/cache/'
reports_dir = str(Path(__file__).parent.parent) + '/reports/'
#models_dir = str(Path(__file__).parent.parent) + '/models/'
log_dir = str(Path(__file__).parent.parent) + '/logs'
token_dir = str(Path(__file__).parent.parent) + '/token/'

oms_service = 'http://localhost:8081/'
feed_socket_service = 'http://localhost:8080/'