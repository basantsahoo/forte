from strategies.core_strategy import BaseStrategy
from helper.utils import pattern_param_match, get_broker_order_type, get_overlap
from statistics import mean
import math
from db.market_data import get_candle_body_size
from helper.utils import get_overlap, compare_day_activity

class BuySellActivity:
    def __init__(self, insight_book):
        self.insight_book = insight_book
        self.candle_stats = []
        self.activity = {}

    def process(self):
        price_list = list(self.insight_book.market_data.values())
        if len(price_list) < 2:
            return
        self.candle_process()
        #print('process++++++')
        #print(self.insight_book.yday_profile)

    def set_up(self):
        self.candle_stats = get_candle_body_size(self.insight_book.ticker, self.insight_book.trade_day)
        self.t_minus_1 = {'high':self.insight_book.yday_profile['high'], 'va_h_p':self.insight_book.yday_profile['va_h_p'],'poc_price':self.insight_book.yday_profile['poc_price'], 'va_l_p':self.insight_book.yday_profile['va_l_p'], 'low':self.insight_book.yday_profile['low'], 'open':self.insight_book.yday_profile['open'], 'close':self.insight_book.yday_profile['close']}
        self.t_minus_2 = {'high': self.insight_book.day_before_profile['high'],
                          'va_h_p': self.insight_book.day_before_profile['va_h_p'],
                          'poc_price': self.insight_book.day_before_profile['poc_price'],
                          'va_l_p': self.insight_book.day_before_profile['va_l_p'],
                          'low': self.insight_book.day_before_profile['low'],
                          'open': self.insight_book.day_before_profile['open'],
                          'close': self.insight_book.day_before_profile['close']}
        self.open_type = self.insight_book.state_generator.get_features()['open_type']
        self.activity = compare_day_activity(self.t_minus_1, self.t_minus_2)

        """
        self.daily_trend = round((self.t_minus_1['poc_price'] / self.t_minus_2['poc_price'] - 1)*100, 2)
        new_teritory = 1 - round(get_overlap([self.t_minus_1['low'], self.t_minus_1['high']], [self.t_minus_2['low'],self.t_minus_2['high']])/(self.t_minus_1['high']-self.t_minus_1['low']), 2)
        retest = round(get_overlap([self.t_minus_2['low'], self.t_minus_2['high']], [self.t_minus_1['low'], self.t_minus_1['high']]) / (self.t_minus_2['high'] - self.t_minus_2['low']), 2)
        print(self.open_type)
        print(self.daily_trend)
        print(advance)
        print(retest)
        """
    def candle_process(self):
        price_list = list(self.insight_book.market_data.values())
        chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
        chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]
        #self.five_min_trend = self.get_candle_trend(chunks_5_ohlc)[0]
