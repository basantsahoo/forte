from datetime import datetime
from db.market_data import get_daily_option_ion_data
from collections import OrderedDict



class OptionIonBuilder:
    def __init__(self, asset, trade_day):
        ion_data_df = get_daily_option_ion_data(asset, trade_day)
        ion_data_df['trade_date'] = trade_day
        self.ion_data = ion_data_df.to_dict("records")

class MultiDayOptionDataLoader:
    def __init__(self, asset="NIFTY", trade_days=[]):
        self.option_ions = OrderedDict()
        start = datetime.now()
        for day in trade_days:
            ob = OptionIonBuilder(asset, day)
            self.option_ions[day] = ob.ion_data
        end = datetime.now()
        print('option data loading took===', (end-start).total_seconds())
        self.data_present = True

    def generate_next_feed(self):
        if list(self.option_ions.keys()):
            day_key = list(self.option_ions.keys())[0]
            next_feed = self.option_ions[day_key].pop(0)
            if not self.option_ions[day_key]:
                del self.option_ions[day_key]
            return [next_feed]
        else:
            self.data_present = False
            return []