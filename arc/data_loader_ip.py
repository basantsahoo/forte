from datetime import datetime
from db.market_data import get_daily_option_ion_data, get_daily_spot_ion_data
from collections import OrderedDict



class OptionIonBuilder:
    def __init__(self, assets, trade_day):
        ion_data_df = get_daily_option_ion_data(assets, trade_day)
        ion_data_df['trade_date'] = trade_day
        self.ion_data = ion_data_df.to_dict("records")
        #print('total option records====', len(self.ion_data))

class SpotIonBuilder:
    def __init__(self, assets, trade_day):
        ion_data_df = get_daily_spot_ion_data(assets, trade_day)
        ion_data_df['trade_date'] = trade_day
        ion_data_df['instrument'] = 'spot'
        recs = ion_data_df.to_dict("records")
        #self.ion_data = ion_data_df.to_dict("records")
        self.ion_data = {}
        for rec in recs:
            self.ion_data[rec['timestamp']] = [rec] if rec['timestamp'] not in self.ion_data.keys() else self.ion_data[rec['timestamp']] + [rec]
        #print('total spot records====', len(self.ion_data))

class MultiDayOptionDataLoader:
    def __init__(self, assets=["NIFTY"], trade_days=[], spot_only=False):
        self.assets = assets
        self.option_ions = OrderedDict()
        self.spot_ions = OrderedDict()
        self.last_ts = None
        self.spot_only = spot_only
        start = datetime.now()
        for day in trade_days:
            ob = OptionIonBuilder(assets, day)
            sb = SpotIonBuilder(assets, day)
            self.option_ions[day] = ob.ion_data
            self.spot_ions[day] = sb.ion_data
        end = datetime.now()
        print('option data loading took===', (end-start).total_seconds())
        self.data_present = True
        self.market_close_for_day = False

    def generate_next_feed(self):
        if self.spot_only:
            return self.generate_next_feed_spot_only()
        else:
            return self.generate_next_feed_spot_options()

    def generate_next_feed_spot_options(self):
        if self.market_close_for_day:
            self.market_close_for_day = False
            yield {'feed_type': 'market_close', 'asset': self.assets[0], 'data': []}

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
                    next_spot_feed_list = self.spot_ions[day_key].get(curr_ts, [])
                    #print(next_spot_feed_list)
                    for next_spot_feed in next_spot_feed_list:
                        yield {'feed_type': 'spot', 'asset': next_spot_feed['asset'], 'data': [next_spot_feed]}
                    self.last_ts = curr_ts
                except:
                    pass
            next_feed = self.option_ions[day_key].pop(0)
            #print(next_feed)
            self.last_ts = curr_ts

            if not self.option_ions[day_key]:
                del self.option_ions[day_key]
                del self.spot_ions[day_key]
                self.market_close_for_day = True
            yield {'feed_type': 'option', 'asset': next_feed['asset'], 'data': [next_feed]}

        else:
            self.data_present = False
            yield {}

    def generate_next_feed_spot_only(self):
        if self.market_close_for_day:
            self.market_close_for_day = False
            return {'feed_type': 'market_close', 'asset': self.asset, 'data': []}
        if list(self.spot_ions.keys()):
            day_key = list(self.spot_ions.keys())[0]
            print(day_key)
            ts_keys = list(self.spot_ions[day_key].keys())
            ts_keys.sort()
            ts_key = ts_keys[0]
            next_spot_feed = self.spot_ions[day_key][ts_key].copy()
            del self.spot_ions[day_key][ts_key]
            next_spot_feed['asset'] = self.asset
            if not self.spot_ions[day_key]:
                del self.spot_ions[day_key]
                self.market_close_for_day = True
            return {'feed_type': 'spot', 'asset': self.asset, 'data': [next_spot_feed]}
        else:
            self.data_present = False
            return []

class MultiDaySpotDataLoader:
    def __init__(self, assets=["NIFTY"], trade_days=[]):
        self.assets = assets
        self.spot_ions = OrderedDict()
        self.last_ts = None
        start = datetime.now()
        for day in trade_days:
            sb = SpotIonBuilder(assets, day)
            self.spot_ions[day] = sb.ion_data
        end = datetime.now()
        print('option data loading took===', (end-start).total_seconds())
        self.data_present = True
        self.market_close_for_day = False

    def generate_next_feed(self):
        if self.market_close_for_day:
            self.market_close_for_day = False
            yield {'feed_type': 'market_close', 'asset': self.assets[0], 'data': []}

        if list(self.spot_ions.keys()):
            day_key = list(self.spot_ions.keys())[0]
            print(day_key)
            ts_keys = list(self.spot_ions[day_key].keys())
            ts_keys.sort()
            ts_key = ts_keys[0]
            next_spot_feed_list = self.spot_ions[day_key].get(ts_key, []).copy()
            del self.spot_ions[day_key][ts_key]
            if not self.spot_ions[day_key]:
                del self.spot_ions[day_key]
                self.market_close_for_day = True

            for next_spot_feed in next_spot_feed_list:
                yield {'feed_type': 'spot', 'asset': next_spot_feed['asset'], 'data': [next_spot_feed]}
        else:
            self.data_present = False
            yield {}


class DayHistTickDataLoader:
    def __init__(self, asset="NIFTY"):
        self.asset = asset
        self.option_ions = OrderedDict()
        self.spot_ions = OrderedDict()
        self.last_ts = None
        self.data_present = False

    def set_option_ion_data(self, trade_day, ion_data):
        self.option_ions[trade_day] = ion_data
        all_ts = [ion_d['timestamp'] for ion_d in ion_data]
        max_ts = max(all_ts)
        last_data = [ion_d for ion_d in ion_data if ion_d['timestamp']==max_ts]
        data_dct = {ion_d['instrument']:ion_d['oi'] for ion_d in last_data}
        #print("last data===========", data_dct)
        self.data_present = True

    def set_spot_ion_data(self, trade_day, ion_data):
        self.spot_ions[trade_day] = {rec['timestamp']: rec for rec in ion_data}
        #print(self.spot_ions)
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