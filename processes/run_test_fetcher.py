import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
import asyncio
from infrastructure.truedata.live_fetcher import start
from market.scheduler import historical_profile
#from fyers.live_fetcher import start


start()
#historical_profile.run()

#test_run_hist_data()

"""
from truedata.custom import TDCustom
td_scoket = TDCustom.getInstance()
greeks = td_scoket.get_intraday_geeks('NIFTY', option_type="PE")
print(greeks)
"""
"""
from nsepy.derivatives import get_expiry_date
from datetime import date
expiry = get_expiry_date(year=2022, month=5)
print(expiry)
from nsepy import get_rbi_ref_history
rbi_ref = get_rbi_ref_history(date(2015,1,1), date(2015,1,10))
print(rbi_ref)

"""