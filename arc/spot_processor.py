from collections import OrderedDict
from helper.time_utils import get_epoc_minute
from talipp.indicators import EMA, SMA, Stoch
from talipp.ohlcv import OHLCVFactory
from datetime import datetime
from entities.base import Signal


class SpotProcessor:
    def __init__(self, asset_book):
        self.asset_book = asset_book
        self.last_tick = {}
        self.spot_ts = OrderedDict()
        self.candles_5 = []
        self.candles_15 = []
        self.ema_5 = EMA(period=2) #Eventually converts candle 5
        self.last_candle_5_count = 0


    def process_minute_data(self, minute_data, notify=True):
        #print('spot process_minute_data+++++', datetime.fromtimestamp(minute_data['timestamp']))
        key_list = ['timestamp', 'open', 'high', "low", "close"]
        feed_small = {key: minute_data[key] for key in key_list}
        epoch_minute = get_epoc_minute(minute_data['timestamp'])
        self.spot_ts[epoch_minute] = feed_small
        self.last_tick = feed_small
        pat = Signal(asset=self.asset_book.asset, category="PRICE", instrument="SPOT", indicator="TICK_PRICE", signal_time=self.last_tick['timestamp'], notice_time=self.last_tick['timestamp'], info= self.last_tick, strength=1)
        """
        pat = {'category': 'PRICE', 'indicator': 'TICK_PRICE', 'strength': 1,
               'signal_time': self.last_tick['timestamp'], 'notice_time': self.last_tick['timestamp'],
               'info': self.last_tick}
        """
        self.asset_book.pattern_signal(pat)

    def process_spot_signals(self, notify=True):
        if notify and len(list(self.spot_ts.keys())) > 1:
            self.perform_calculations()

    def ema_5_signal(self):
        candle_count = self.asset_book.candle_5_processor.get_candle_count()
        if candle_count != self.last_candle_5_count:
            self.last_candle_5_count = candle_count
            candle_5 = self.asset_book.candle_5_processor.get_last_n_candles(1)[0]
            #print('new candle start time===', datetime.fromtimestamp(candle_5['timestamp']))
            pat = Signal(asset=self.asset_book.asset, category="PRICE", instrument="", indicator="CANDLE",
                         signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                         info=candle_5, strength=1)
            self.asset_book.pattern_signal(pat)
            if candle_count > 2 and candle_count<6:
                self.ema_5 = EMA(period=candle_count, input_values=[candle['close'] for candle in self.asset_book.candle_5_processor.candles])
            else:
                self.ema_5.add_input_value(candle_5['close'])
            if self.ema_5:
                #print('ema_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), self.ema_5[-1])
                #print('candle_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), candle_5)
                candle_low = candle_5['low']
                if candle_low > self.ema_5[-1]:
                    print('candle signal =========',datetime.fromtimestamp(self.last_tick['timestamp']))
                    pat = Signal(asset=self.asset_book.asset,  category='TECHNICAL', instrument="SPOT", indicator='CDL_5_ABOVE_EMA_5', strength=1, signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'], info= candle_5)
                    self.asset_book.pattern_signal(pat)

                price_below_ema = int(candle_5['close'] < self.ema_5[-1])
                if price_below_ema:
                    print('price_below_ema signal===========',datetime.fromtimestamp(self.last_tick['timestamp']))
                    pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="PRICE_BELOW_EMA_5",
                                 signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                                 info=candle_5, strength=1)


                else:
                    pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="PRICE_ABOVE_EMA_5",
                                 signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                                 info=candle_5, strength=1)
                self.asset_book.pattern_signal(pat)

    def perform_calculations(self):
        self.ema_5_signal()
