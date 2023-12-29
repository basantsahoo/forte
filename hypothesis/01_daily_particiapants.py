import pandas as pd
import numpy as np
import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
asset = "NIFTY"
from entities.trading_day import NearExpiryWeek
from option_market.option_matrix import MultiDayOptionDataLoader, OptionMatrix, OptionSignalGenerator
from option_market.exclude_trade_days import exclude_trade_days


expiry_dates = NearExpiryWeek.get_asset_expiry_dates(asset)
list_of_data = []
for expiry_date in expiry_dates[1:len(expiry_dates)-5]:
    print(expiry_date.date_string)
    expiry_week = NearExpiryWeek(expiry_date, asset)
    expiry_week.get_all_trade_days()
    days_formatted = [day.date_string for day in expiry_week.all_trade_days if day.date_string not in exclude_trade_days[asset]]
    print(days_formatted)
    data_loader = MultiDayOptionDataLoader(asset=asset, trade_days=days_formatted)
    option_matrix = OptionMatrix(feed_speed=1, throttle_speed=1)
    #signal_generator = OptionSignalGenerator(option_matrix)

    while data_loader.data_present:
        feed_list = data_loader.generate_next_feed()
        if feed_list:
            option_matrix.process_feed(feed_list)
            option_matrix.generate_signal()
    for day in expiry_week.all_trade_days:
        current_date = day.date_string
        if current_date not in exclude_trade_days[asset]:
            day_capsule = option_matrix.get_day_capsule(current_date)
            call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
            put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
            total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
            poi_point = 5
            dct = {'asset': asset,
                   'date': current_date,
                   'expiry_date':expiry_week.end_date.date_string,
                   'trade_d2e': day.trade_d2e, 'cal_d2e': day.cal_d2e,
                   'min_total_oi': min(total_oi[0:len(total_oi)-poi_point+1]),
                   'max_total_oi': max(total_oi[0:len(total_oi)-poi_point+1]),
                   'poi_total_oi': total_oi[len(total_oi)-poi_point+1],
                   'poi_call_oi': call_oi_series[len(total_oi) - poi_point],
                   'poi_put_oi': put_oi_series[len(total_oi) - poi_point],
                   'poi_total_drop_pct': np.round(total_oi[-poi_point]*1.00/max(total_oi[0:len(total_oi)-poi_point+1])-1, 2),
                   'poi_call_drop_pct': np.round(
                       call_oi_series[-poi_point] * 1.00 / max(call_oi_series[0:len(call_oi_series) - poi_point + 1]) - 1, 2),
                   'poi_put_drop_pct': np.round(
                       put_oi_series[-poi_point] * 1.00 / max(
                           put_oi_series[0:len(put_oi_series) - poi_point + 1]) - 1, 2),
                   'close_total_oi': total_oi[-1]
                   }
            list_of_data.append(dct)

    pd.DataFrame(list_of_data).to_csv('01_daily_particiapants_' + asset + '.csv')