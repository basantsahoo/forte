import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)
from datetime import datetime
from db.market_data import (get_all_days, get_daily_tick_data, get_daily_option_data_2)
from collections import OrderedDict

class IntradayOptionProcessor:
    def __init__(self, symbol):
        self.symbol = symbol
        self.option_data_cross_ts_inst_oi = OrderedDict() #{}
        self.option_data_cross_ts_inst_volume = OrderedDict() #{}
        self.option_data_inst_ts = {}
        self.price_inst_ts = {}
        self.oi_inst_ts = {}
        self.volume_inst_ts = {}

    def process_input_stream(self,option_data_list):
        for option_data in option_data_list:
            if option_data['symbol'] == self.symbol:
                ts = option_data['timestamp']
                option_recs = option_data['records']
                if ts not in self.option_data_cross_ts_inst_oi:
                    self.option_data_cross_ts_inst_oi[ts] = {}
                if ts not in self.option_data_cross_ts_inst_volume:
                    self.option_data_cross_ts_inst_volume[ts] = {}

                for instrument, data in option_recs.items():
                    if instrument not in self.option_data_inst_ts:
                        self.option_data_inst_ts[instrument] = OrderedDict() #{}
                    self.option_data_inst_ts[instrument][ts] = data
                    self.option_data_cross_ts_inst_oi[ts][instrument] = data['oi']
                    self.option_data_cross_ts_inst_volume[ts][instrument] = data['volume']

    def perform_calculations(self):
        pass

    def get_ts_by_inst(self, inst, fields=[]):
        inst_series = self.option_data_inst_ts[inst]
        inst_series = list(inst_series.values()) #list(dict(sorted(inst_series.items())).values())
        if fields:
            inst_series = [{key: dct[key] for key in fields} for dct in inst_series]
        return inst_series


symbol = 'NIFTY'
day = '2022-12-30'
option_df = get_daily_option_data_2(symbol, day)
#option_list = option_list.to_dict('records')

timestamps = option_df['timestamp'].unique()
timestamps.sort()
start = datetime.now()
option_processor = IntradayOptionProcessor(symbol)
for ts in timestamps:
    t_df = option_df[option_df['timestamp'] == ts][['instrument', 'oi', 'volume', 'open','high','low','close']]
    t_df.set_index('instrument', inplace=True)
    recs = t_df.to_dict('index')
    option_processor.process_input_stream([{'timestamp': ts, 'symbol' : symbol, 'records' : recs}])
    ttt = option_processor.get_ts_by_inst('18600_PE')

#print(option_processor.option_data_cross_ts_inst_volume)
print(option_processor.get_ts_by_inst('18600_PE', ['close']))
end = datetime.now()

print('total time====', (end-start).total_seconds())