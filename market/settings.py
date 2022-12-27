import aiohttp_cors
from pathlib import Path
from datetime import datetime
CROS_ALLOWED_ORIGINS =['http://localhost:4200', 'http://localhost:8080', 'http://localhost:8000', 'http://api.niftybull.in:8080']

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

"http://api.niftybull.in:8080": aiohttp_cors.ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
        )
}

chromedriver = '/home/ubuntu/chromedriver'
market_profile_db = '../data/market_profile.db'
reports_dir = str(Path(__file__).parent.parent) + '/reports/'
models_dir = str(Path(__file__).parent.parent) + '/models/'
log_dir = str(Path(__file__).parent.parent) + '/logs'
token_dir = str(Path(__file__).parent) + '/token/'
