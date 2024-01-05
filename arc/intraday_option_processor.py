from collections import OrderedDict
from entities.base import Signal

class IntradayOptionProcessor:
    def __init__(self, asset_book, symbol):
        self.asset_book = asset_book
        self.symbol = symbol
        self.option_data_cross_ts_inst_oi = OrderedDict() #{}
        self.option_data_cross_ts_inst_volume = OrderedDict() #{}
        self.option_data_inst_ts = {}
        self.vwap = {}
        self.price_drop_book = {}


    def weighted_average(self,nums, weights):
        return sum(x * y for x, y in zip(nums, weights)) / sum(weights)

    def process_input_stream(self, option_data, notify=True):
        #print('option processor process_input_stream', option_data['timestamp'])
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
        if notify and len(list(self.option_data_cross_ts_inst_oi.keys())) > 2:
            self.perform_calculations()


    def perform_calculations(self):
        #self.calculate_vwap()
        self.calculate_price_drop()

    def get_inst_details(self, inst):
        strike = int(inst.split("_")[0])
        kind = inst.split("_")[1]
        #print(self.asset_book.last_tick)
        spot = list(self.asset_book.spot_processor.spot_ts.values())[0]['close']
        #spot = self.asset_book.last_tick['close']
        dist = round((strike - spot) / 100)
        if kind == 'CE':
            money_ness = ('OTM_' if dist > 0 else 'ITM_' if dist < 0 else 'ATM_') + str(abs(dist))
        else:
            money_ness = ('OTM_' if dist < 0 else 'ITM_' if dist > 0 else 'ATM_') + str(abs(dist))
        return {'strike' : strike, 'kind': kind, 'money_ness' : money_ness, 'dist' :abs(dist)}

    def calculate_price_drop(self):
        drop_pcts = [20, 30, 40, 50, 60, 70, 80, 90]
        for inst in self.option_data_inst_ts:
            if inst not in self.price_drop_book:
                self.price_drop_book[inst] = {}
            first_ts = list(self.option_data_inst_ts[inst].keys())[0]
            #print(first_ts)
            first_item = list(self.option_data_inst_ts[inst].values())[0]
            #print('first_item+++++', list(self.option_data_inst_ts[inst].keys())[0])
            (last_ts, last_item) = list(self.option_data_inst_ts[inst].items())[-1]
            #print(last_item)
            for pct in drop_pcts:

                if last_item['close']/first_item['close'] < (1 - pct/100):
                    #print(inst,round(last_item['close'] / first_item['close'], 2))
                    if self.price_drop_book[inst].get('drop_'+ str(pct), None) is None:
                        #print('triger+++++++++++++++++')
                        self.price_drop_book[inst]['drop_'+ str(pct)] = last_ts
                        inst_details = self.get_inst_details(inst)
                        if inst_details['dist'] <= 10:
                            pat = Signal(asset=self.asset_book.asset, category="OPTION", instrument=inst,
                                         indicator="PRICE_DROP",
                                         signal_time=last_ts,
                                         notice_time=last_ts,
                                         info=inst_details, strength=pct)

                            #matched_pattern = {'time': last_ts, 'instrument': inst, 'strength': pct, **inst_details}
                            #pat = {'category':'OPTION', 'indicator': 'PRICE_DROP', 'strength': pct, 'signal_time': last_ts, 'notice_time': last_ts, 'instrument': inst, 'info': inst_details}
                            self.asset_book.pattern_signal(pat)
                else:
                    self.price_drop_book[inst]['drop_' + str(pct)] = None



    def calculate_vwap(self):
        for inst in self.option_data_inst_ts:
            if inst not in self.vwap:
                self.vwap[inst] = OrderedDict()
            max_ts = list(self.option_data_inst_ts[inst].keys())[-1]
            #print(self.option_data_inst_ts[inst].values())
            prices = [x['close'] for x in self.option_data_inst_ts[inst].values()]
            volumes = [x['volume'] for x in self.option_data_inst_ts[inst].values()]
            vwap = self.weighted_average(prices, volumes)
            self.vwap[inst][max_ts] = vwap


    def get_ts_by_inst(self, inst, fields=[]):
        inst_series = self.option_data_inst_ts[inst]
        inst_series = list(inst_series.values()) #list(dict(sorted(inst_series.items())).values())
        if fields:
            inst_series = [{key: dct[key] for key in fields} for dct in inst_series]
        return inst_series


    def get_last_tick(self, inst):
        ts, data = list(self.option_data_inst_ts[inst].items())[-1]
        return {'timestamp': ts, **data}