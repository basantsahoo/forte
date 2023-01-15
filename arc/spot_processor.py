from collections import OrderedDict
from helper.utils import get_epoc_minute

class SpotProcessor:
    def __init__(self, insight_book, symbol):
        self.insight_book = insight_book
        self.symbol = symbol
        self.last_tick = {}
        self.spot_ts = OrderedDict()
        self.candles_5 = []
        self.candles_15 = []

    def process_minute_data(self, minute_data, notify=True):
        #print('spot processor+++++')
        key_list = ['timestamp', 'open', 'high', "low", "close"]
        feed_small = {key: minute_data[key] for key in key_list}
        epoch_minute = get_epoc_minute(minute_data['timestamp'])
        self.spot_ts[epoch_minute] = feed_small
        self.last_tick = feed_small

        if notify and len(list(self.spot_ts.keys())) > 2:
            self.perform_calculations()


    def perform_calculations(self):
        price_list = list(self.spot_ts.values())
        chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
        chunks_5 = [x for x in chunks_5 if len(x) == 5]
        chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
        chunks_15 = [x for x in chunks_15 if len(x) == 15]

        self.candles_5 = [{'timestamp':x[0]['timestamp'], 'open':x[0]['open'], 'high': max([y['high'] for y in x]), 'low':min([y['low'] for y in x]), 'close':x[-1]['close']} for x in chunks_5]
        self.candles_15 = [{'timestamp':x[0]['timestamp'], 'open':x[0]['open'], 'high': max([y['high'] for y in x]), 'low':min([y['low'] for y in x]), 'close':x[-1]['close']} for x in chunks_15]
