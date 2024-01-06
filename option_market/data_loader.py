from datetime import datetime
from db.market_data import get_daily_option_ion_data, get_daily_spot_ion_data
from collections import OrderedDict



class OptionIonBuilder:
    def __init__(self, asset, trade_day):
        ion_data_df = get_daily_option_ion_data(asset, trade_day)
        ion_data_df['trade_date'] = trade_day
        self.ion_data = ion_data_df.to_dict("records")
        #print('total option records====', len(self.ion_data))

class SpotIonBuilder:
    def __init__(self, asset, trade_day):
        ion_data_df = get_daily_spot_ion_data(asset, trade_day)
        ion_data_df['trade_date'] = trade_day
        ion_data_df['instrument'] = 'spot'
        recs = ion_data_df.to_dict("records")
        #self.ion_data = ion_data_df.to_dict("records")
        self.ion_data = {rec['timestamp']: rec for rec in recs}
        #print('total spot records====', len(self.ion_data))

class MultiDayOptionDataLoader:
    def __init__(self, asset="NIFTY", trade_days=[]):
        self.asset = asset
        self.option_ions = OrderedDict()
        self.spot_ions = OrderedDict()
        self.last_ts = None
        start = datetime.now()
        for day in trade_days:
            ob = OptionIonBuilder(asset, day)
            sb = SpotIonBuilder(asset, day)
            self.option_ions[day] = ob.ion_data
            self.spot_ions[day] = sb.ion_data
        end = datetime.now()
        print('option data loading took===', (end-start).total_seconds())
        self.data_present = True

    def generate_next_feed(self):

        if list(self.option_ions.keys()):
            day_key = list(self.option_ions.keys())[0]
            #print(day_key)
            next_option_feed = self.option_ions[day_key][0]
            curr_ts = next_option_feed['timestamp']
            #print(self.last_ts, curr_ts)

            if curr_ts != self.last_ts:
                #print('inside loop')

                try:
                    #next_spot_feed = self.spot_ions[day_key].get(curr_ts, {'instrument': 'spot', 'timestamp': self.last_ts, 'trade_date': day_key, 'ion': '0|0|0|0'})
                    next_spot_feed = self.spot_ions[day_key].get(curr_ts, None)
                    if next_spot_feed:
                        next_spot_feed['asset'] = self.asset
                        self.last_ts = curr_ts
                        return {'feed_type': 'spot', 'asset': self.asset, 'data': [next_spot_feed]}
                except:
                    pass
            next_feed = self.option_ions[day_key].pop(0)
            next_feed['asset'] = self.asset
            self.last_ts = curr_ts

            if not self.option_ions[day_key]:
                del self.option_ions[day_key]
                del self.spot_ions[day_key]
            return {'feed_type': 'option', 'asset': self.asset, 'data': [next_feed]}

        else:
            self.data_present = False
            return []