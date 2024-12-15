from collections import OrderedDict
from talipp.indicators import EMA, SMA, Stoch
from datetime import datetime
from dynamics.patterns.price_action_pattern_detector import PriceActionPatternDetector
from dynamics.patterns.candle_pattern_detector import CandlePatternDetector
# Transitions
from dynamics.transition.intra_day_transition import DayFullStateGenerator
from dynamics.transition.mc_pre_process import MCPreprocessor
from dynamics.transition.second_level_mc import MarkovChainSecondLevel
from dynamics.transition.empirical import EmpiricalDistribution
from arc.candle_processor import CandleProcessor
from entities.base import Signal
from entities.trading_day import TradeDateTime

class SpotSignalGenerator:
    def __init__(self, spot_book, asset):
        self.spot_book = spot_book
        self.asset_book = self.spot_book.asset_book
        self.asset = asset
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
        self.last_periodic_update = None
        self.periodic_update_sec = 60

        self.candle_1_processor = CandleProcessor(self, 1, 0)
        self.candle_5_processor = CandleProcessor(self, 5, 0)
        #self.candle_15_processor = CandleProcessor(self, 15, 0)
        self.state_generator = None
        self.trend = {}
        self.price_action_pattern_detectors = [PriceActionPatternDetector(self.spot_book, period=1)]
        self.candle_pattern_detectors = [CandlePatternDetector(self.spot_book, period=1), CandlePatternDetector(self.spot_book, period=2), CandlePatternDetector(self.spot_book, period=5)]
        self.candle_pattern_detectors = [CandlePatternDetector(self.spot_book, period=1)]
        self.day_setup_done = False
        self.mc = MarkovChainSecondLevel()

        self.last_tick = {}

    def generate_signals(self):
        self.process_spot_signals()
        for pattern_detector in self.price_action_pattern_detectors:
            pattern_detector.evaluate()
        for candle_detector in self.candle_pattern_detectors:
            candle_detector.evaluate()


    def process_spot_signals(self, notify=True):
        self.last_tick = self.spot_book.spot_processor.last_tick
        pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument="SPOT", indicator="TICK_PRICE", signal_time=self.last_tick['timestamp'], notice_time=self.last_tick['timestamp'], signal_info= self.last_tick, strength=1, period="1min")
        self.asset_book.pattern_signal(pat)

        if notify and len(list(self.spot_book.spot_processor.spot_ts.keys())) > 1:
            #print('+++++++++++++++++++++process_spot_signals+++++++++++++++++++++++++++')
            self.perform_calculations()

    def ema_5_signal(self):
        candle_count = self.spot_book.candle_5_processor.get_candle_count()
        if candle_count > 2 and  candle_count != self.last_candle_5_count:
            self.last_candle_5_count = candle_count
            candle_5 = self.spot_book.candle_5_processor.get_last_n_candles(1)[0]
            #print('new candle start time===', datetime.fromtimestamp(candle_5['timestamp']))
            pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument=None, indicator="CANDLE_5",
                         signal_time=candle_5['timestamp'], notice_time=self.last_tick['timestamp'],
                         signal_info=candle_5, strength=1, period="1min")
            self.asset_book.pattern_signal(pat)
            if candle_count > 2 and candle_count<6:
                self.ema_5 = EMA(period=candle_count, input_values=[candle['close'] for candle in self.spot_book.candle_5_processor.candles])
            else:
                self.ema_5.add(candle_5['close'])
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
        candle_count = self.spot_book.candle_1_processor.get_candle_count()
        if candle_count != self.last_candle_1_count:
            self.last_candle_1_count = candle_count
            candle_1 = self.spot_book.candle_1_processor.get_last_n_candles(1)[0]
            #print('new candle start time===', datetime.fromtimestamp(candle_5['timestamp']))
            pat = Signal(asset=self.asset_book.asset, category="PRICE_SIGNAL", instrument=None, indicator="CANDLE_1",
                         signal_time=candle_1['timestamp'], notice_time=self.last_tick['timestamp'],
                         signal_info=candle_1, strength=1, period="1min")
            self.asset_book.pattern_signal(pat)
            if candle_count > 2 and candle_count<11:
                self.ema_1_10 = EMA(period=candle_count, input_values=[candle['close'] for candle in self.spot_book.candle_1_processor.candles])
                self.sma_1_10 = SMA(period=candle_count, input_values=[candle['close'] for candle in self.spot_book.candle_1_processor.candles])
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
        self.ema_5_signal()
