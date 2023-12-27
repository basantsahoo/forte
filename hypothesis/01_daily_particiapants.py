import pandas as pd
import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
asset = "BANKNIFTY"
from entities.trading_day import NearExpiryWeek
from option_market.option_matrix import MultiDayOptionDataLoader, OptionMatrix, OptionSignalGenerator

expiry_dates = NearExpiryWeek.get_asset_expiry_dates(asset)
list_of_data = []
for expiry_date in expiry_dates[1:len(expiry_dates)-8]:
    expiry_week = NearExpiryWeek(expiry_date, asset)

    expiry_week.get_all_trade_days()
    days_formatted = [day.date_string for day in expiry_week.all_trade_days]
    data_loader = MultiDayOptionDataLoader(asset="BANKNIFTY", trade_days=days_formatted)
    option_matrix = OptionMatrix(feed_speed=1, throttle_speed=1)
    signal_generator = OptionSignalGenerator(option_matrix)

    while data_loader.data_present:
        feed_list = data_loader.generate_next_feed()
        if feed_list:
            option_matrix.process_feed(feed_list)
            option_matrix.generate_signal()
    for day in expiry_week.all_trade_days:
        current_date = day.date_string
        day_capsule = option_matrix.get_day_capsule(current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        dct = {'asset':asset, 'date': current_date, 'expiry_date':expiry_week.end_date.date_string, 'trade_d2e': day.trade_d2e, 'cal_d2e': day.cal_d2e, 'min_total_oi': min(total_oi), 'max_total_oi': max(total_oi)}
        list_of_data.append(dct)

    pd.DataFrame(list_of_data).to_csv('01_daily_particiapants.csv')