import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
import numpy as np
from dynamics.option_market.option_matrix import MultiDayOptionDataLoader, OptionMatrix
from db.market_data import get_prev_day_avg_volume
from dynamics.option_market.utils import get_average_volume_for_day

from entities.trading_day import TradeDateTime, NearExpiryWeek
t_day = "2023-12-27"
asset = "NIFTY"

trading_day = TradeDateTime(t_day)
expiry_week = NearExpiryWeek(trading_day, asset)

data_loader = MultiDayOptionDataLoader(asset=asset, trade_days=[t_day])
option_matrix = OptionMatrix(asset, feed_speed=1, throttle_speed=1)
#signal_generator = OptionSignalGenerator(option_matrix)
closing_oi_df = get_prev_day_avg_volume(asset, t_day)
# print(closing_oi_df['avg_volume'].sum())
closing_oi_df = closing_oi_df[['instrument', 'closing_oi']]
option_matrix.process_closing_oi(t_day, closing_oi_df.to_dict("record"))
avg_volume_recs = get_average_volume_for_day(asset, t_day)
# print(avg_volume_recs)
# print(avg_volume_df.to_dict("record"))

option_matrix.process_avg_volume(t_day, avg_volume_recs)

while data_loader.data_present:
    feed_ = data_loader.generate_next_feed()
    if feed_:
        feed_type = feed_['feed_type']
        feed_list = feed_['data']
        if feed_type == 'option':
            option_matrix.process_option_feed(feed_list)

        if feed_type == 'spot':
            #print(feed_list)
            option_matrix.process_spot_feed(feed_list)
            pass
        #option_matrix.generate_signal()

current_date = option_matrix.current_date
day_capsule = option_matrix.get_day_capsule(option_matrix.current_date)
call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
spot_series = day_capsule.cross_analyser.get_instrument_ion_field_series()
#print(spot_series)
t_series = day_capsule.cross_analyser.get_ts_series()

total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
poi_point = 5
print(len(t_series) - poi_point)
poi_ts = t_series[len(t_series) - poi_point]
poi_ts = TradeDateTime(poi_ts)
print(poi_ts.date_time_string)

day = trading_day
dct = {'asset': asset,
       'date': current_date,
       'expiry_date': expiry_week.end_date.date_string,
       'trade_d2e': day.trade_d2e, 'cal_d2e': day.cal_d2e,
       'min_total_oi': min(total_oi[0:len(total_oi) - poi_point + 1]),
       'max_total_oi': max(total_oi[0:len(total_oi) - poi_point + 1]),
       'poi_total_oi': total_oi[len(total_oi) - poi_point + 1],
       'poi_call_oi': call_oi_series[len(total_oi) - poi_point],
       'poi_put_oi': put_oi_series[len(total_oi) - poi_point],
       'poi_total_drop_pct': np.round(total_oi[-poi_point] * 1.00 / max(total_oi[0:len(total_oi) - poi_point + 1]) - 1,
                                      2),
       'poi_call_drop_pct': np.round(
           call_oi_series[-poi_point] * 1.00 / max(call_oi_series[0:len(call_oi_series) - poi_point + 1]) - 1, 2),
       'poi_put_drop_pct': np.round(
           put_oi_series[-poi_point] * 1.00 / max(
               put_oi_series[0:len(put_oi_series) - poi_point + 1]) - 1, 2),
       'close_total_oi': total_oi[-1]
       }
#print(call_oi_series)
"""
ts = 1703131200
ts_data = day_capsule.transposed_data[ts]
#print(ts_data)
for instrument, cell in ts_data.items():
    if instrument[-2::] == 'CE':
        print(instrument, cell.ion.oi)
"""