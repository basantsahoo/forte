from collections import OrderedDict
from entities.trading_day import TradeDateTime
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
        self.ema_1_10 = EMA(period=10)
        self.sma_1_10 = SMA(period=10)
        self.last_candle_5_count = 0
        self.last_candle_1_count = 0
        self.day_range = {'low': float('inf'), 'high': float('-inf')}


    def process_minute_data(self, minute_data, notify=True):
        #print('spot process_minute_data+++++', datetime.fromtimestamp(minute_data['timestamp']))
        key_list = ['timestamp', 'open', 'high', "low", "close"]
        feed_small = {key: minute_data[key] for key in key_list}
        epoch_minute = TradeDateTime.get_epoc_minute(minute_data['timestamp'])
        self.spot_ts[epoch_minute] = feed_small
        self.last_tick = feed_small
        self.day_range['low'] = min(self.day_range['low'], feed_small['low'])
        self.day_range['high'] = max(self.day_range['high'], feed_small['high'])

    def process_spot_signals(self, notify=True):
        pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument="SPOT", indicator="TICK_PRICE", signal_time=self.last_tick['timestamp'], notice_time=self.last_tick['timestamp'], signal_info= self.last_tick, strength=1, period="1min")
        self.asset_book.pattern_signal(pat)

        if notify and len(list(self.spot_ts.keys())) > 1:
            print('+++++++++++++++++++++process_spot_signals+++++++++++++++++++++++++++')
            self.perform_calculations()

    def ema_5_signal(self):
        candle_count = self.asset_book.candle_5_processor.get_candle_count()
        if candle_count != self.last_candle_5_count:
            self.last_candle_5_count = candle_count
            candle_5 = self.asset_book.candle_5_processor.get_last_n_candles(1)[0]
            #print('new candle start time===', datetime.fromtimestamp(candle_5['timestamp']))
            pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument="", indicator="CANDLE_5",
                         signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                         signal_info=candle_5, strength=1, period="1min")
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
                    print('candle signal =========', datetime.fromtimestamp(self.last_tick['timestamp']))
                    pat = Signal(asset=self.asset_book.asset,  category='TECHNICAL', instrument="SPOT", indicator='CDL_5_ABOVE_EMA_5', strength=1, signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'], signal_info= candle_5, period="1min")
                    self.asset_book.pattern_signal(pat)

                price_below_ema = int(candle_5['close'] < self.ema_5[-1])
                if price_below_ema:
                    #print('price_below_ema signal===========', datetime.fromtimestamp(self.last_tick['timestamp']))
                    pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="PRICE_BELOW_EMA_5",
                                 signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                                 signal_info=candle_5, strength=1, period="1min")


                else:
                    pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="PRICE_ABOVE_EMA_5",
                                 signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                                 signal_info=candle_5, strength=1, period="1min")
                self.asset_book.pattern_signal(pat)

    def ema_1_signal(self):
        candle_count = self.asset_book.candle_1_processor.get_candle_count()
        if candle_count != self.last_candle_1_count:
            self.last_candle_1_count = candle_count
            candle_1 = self.asset_book.candle_1_processor.get_last_n_candles(1)[0]
            #print('new candle start time===', datetime.fromtimestamp(candle_5['timestamp']))
            pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument=None, indicator="CANDLE_1",
                         signal_time=candle_1['timestamp'], notice_time=self.last_tick['timestamp'],
                         signal_info=candle_1, strength=1, period="1min")
            self.asset_book.pattern_signal(pat)
            if candle_count > 2 and candle_count<11:
                self.ema_1_10 = EMA(period=candle_count, input_values=[candle['close'] for candle in self.asset_book.candle_1_processor.candles])
                self.sma_1_10 = SMA(period=candle_count, input_values=[candle['close'] for candle in self.asset_book.candle_1_processor.candles])
            else:
                self.ema_1_10.add_input_value(candle_1['close'])
                self.sma_1_10.add_input_value(candle_1['close'])
            if self.ema_1_10:
                #print('ema_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), self.ema_5[-1])
                #print('candle_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), candle_5)

                pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="EMA_1_10",
                             signal_time=candle_1['timestamp'], notice_time=self.last_tick['timestamp'],
                             signal_info=candle_1, strength=self.ema_1_10[-1], period="1min")

                self.asset_book.pattern_signal(pat)
            if self.sma_1_10:
                #print('ema_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), self.ema_5[-1])
                #print('candle_5=======', datetime.fromtimestamp(self.last_tick['timestamp']), candle_5)

                pat = Signal(asset=self.asset_book.asset, category="TECHNICAL", instrument="SPOT", indicator="SMA_1_10",
                             signal_time=candle_1['timestamp'], notice_time=self.last_tick['timestamp'],
                             signal_info=candle_1, strength=self.sma_1_10[-1], period="1min")

                self.asset_book.pattern_signal(pat)

    def perform_calculations(self):
        pass
        self.ema_1_signal()
