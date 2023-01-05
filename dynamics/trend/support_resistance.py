from dynamics.trend.technical_patterns import pattern_engine
from dynamics.trend.tick_price_smoothing import PriceInflexDetectorForTrend
from db.market_data import get_daily_tick_data
import helper.utils as helper_utils
import time

class SupportResistance:
    def __init__(self, symbol, day):
        self.supports = []
        self.resistances = []
        self.existing_supports = []
        self.existing_resistances = []
        self.support_additions = []
        self.support_removals = []
        self.resistance_additions = []
        self.resistance_removals = []
        self.symbol = symbol
        self.trade_day = day
        self.pattern_detector = PriceInflexDetectorForTrend(symbol, fpth = 0.001, spth = 0.001, callback=None)

    def record_intraday_highs(self, local_infl):
        #print('record_intraday_highs+++++++++++++')
        for infl in self.resistance_additions.copy():
            if local_infl >= infl:
                self.resistance_additions.remove(infl)
        self.resistance_additions.append(local_infl)
        #print(local_infl)
        #print(self.resistance_additions)

    def record_intraday_lows(self, local_infl):
        for infl in self.support_additions.copy():
            if local_infl <= infl:
                self.support_additions.remove(infl)
        self.support_additions.append(local_infl)

    def get_nearest_level(self, price):
        rem = price % 100
        if rem >= 80 or rem <= 20:
            levl = round(price/100, 0) * 100
        else:
            levl = round(price / 10, 0) * 10
        return levl
    def flatten_levels(self):
        self.resistance_additions = list(set([self.get_nearest_level(x) for x in self.resistance_additions]))
        self.support_additions = list(set([self.get_nearest_level(x) for x in self.support_additions]))
        self.resistance_additions.sort(reverse=True)
        self.support_additions.sort()

    def process(self):
        price_list = get_daily_tick_data(self.symbol, self.trade_day)
        price_list['symbol'] = helper_utils.root_symbol(self.symbol)
        #day_range = [min(price_list['close']), max(price_list['close'])]
        day_range = [min(price_list['low']), max(price_list['high'])]
        price_list = price_list.to_dict('records')
        try:
            for i in range(len(price_list)):
                price = price_list[i]
                self.pattern_detector.on_price_update([price['timestamp'], price['close']])
                time.sleep(0.005)
        except Exception as e:
            print('error on', day)
            print(e)
            print(traceback.format_exc())
        dfsub = self.pattern_detector.dfstock_3
        dfsub = dfsub[dfsub['SPExt']!='']
        #delete last index when in range -- to be done
        #print(dfsub.head().T)
        print(day_range)
        highs = dfsub[dfsub['SPExt'] == 'SPH']['Close'].tolist()
        print('highs+++++++++', highs)
        lows = dfsub[dfsub['SPExt'] == 'SPL']['Close'].tolist()
        print('lows+++++++++', lows)
        for high in highs:
            self.record_intraday_highs(high)
            #print(self.resistance_additions)

        for low in lows:
            self.record_intraday_lows(low)
            #print(self.support_additions)
        self.flatten_levels()
        print('intraday resistances', self.resistance_additions)
        print('intraday supports', self.support_additions)
        for ex_resist in self.existing_resistances.copy():
            if (ex_resist >= day_range[0]) and (ex_resist <= day_range[1]): #Price gets traded
                self.existing_resistances.remove(ex_resist)
                self.resistance_removals.append(ex_resist)
            elif ex_resist < day_range[0]: #Gap Up
                self.existing_resistances.remove(ex_resist)
                self.support_additions.append(ex_resist) #resistance becomes support
        for ex_supp in self.existing_supports.copy():
            if (ex_supp >= day_range[0]) and (ex_supp <= day_range[1]):
                self.existing_supports.remove(ex_supp)
                self.support_removals.append(ex_supp)
            elif ex_supp > day_range[1]:
                self.existing_supports.remove(ex_supp)
                self.resistance_additions.append(ex_supp) #resistance becomes support
        self.existing_resistances.extend(self.resistance_additions)
        self.existing_supports.extend(self.support_additions)
        self.existing_resistances = list(set(self.existing_resistances))
        self.existing_resistances.sort(reverse=True)
        self.existing_supports = list(set(self.existing_supports))
        self.existing_supports.sort()
        self.resistance_removals = list(set(self.resistance_removals) - set(self.existing_resistances))
        self.support_removals = list(set(self.support_removals) - set(self.existing_supports))
        self.resistance_removals.sort()
        self.support_removals.sort()
        print('curr resistances', self.existing_resistances)
        print('taken out resistances', self.resistance_removals)
        print('curr supports', self.existing_supports)
        print('taken out supports', self.support_removals)