import sys
import os
import psutil
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler import td_download_spot_data
from scheduler import td_download_option_data
from scheduler import calculate_historical_measures
from scheduler import historical_profile
from scheduler import running_weekly_stats
from scheduler import download_economic_calendar
from scheduler import download_earnings_calendar
from scheduler import calculate_support_resistance
import time


def restart_process():
    print("argv was", sys.argv)
    print("sys.executable was", sys.executable)
    print("restart now")
    try:
        p = psutil.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        print(e)
    time.sleep(10)
    os.execv(sys.executable, ['python3'] + sys.argv)


def start():

    scheduler = BackgroundScheduler()
    scheduler.add_job(td_download_spot_data.run, 'cron', day_of_week='mon-sun', hour='1', minute='00')
    scheduler.add_job(td_download_option_data.run2, 'cron', day_of_week='mon-sun', hour='1', minute='02')
    scheduler.add_job(calculate_historical_measures.run, 'cron', day_of_week='mon-sun', hour='4', minute='08')
    scheduler.add_job(calculate_support_resistance.run, 'cron', day_of_week='mon-sun', hour='8', minute='25')
    scheduler.add_job(historical_profile.run, 'cron', day_of_week='mon-sun', hour='7', minute='35')
    scheduler.add_job(running_weekly_stats.run, 'cron', day_of_week='mon-sun', hour='8', minute='35')
    scheduler.add_job(restart_process, 'cron', day_of_week='mon-sun', hour='21', minute='45')
    scheduler.add_job(download_economic_calendar.run, 'cron', day_of_week='*', hour='8', minute='40')
    scheduler.add_job(download_earnings_calendar.run, 'cron', day_of_week='*', hour='8', minute='45')


    scheduler.start()




