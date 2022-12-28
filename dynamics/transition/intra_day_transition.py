from db.market_data import (get_nth_day_profile_data, get_hist_ndays_profile_data)
from dynamics import profile as profile_utils
from itertools import chain, product
import calendar
import talib
import numpy as np
from collections import OrderedDict

pattern_names = talib.get_function_groups()['Pattern Recognition'] #['CDLHANGINGMAN']


def determine_day_open(open_candle, yday_profile):
    open_low = open_candle['open']
    open_high = open_candle['open']
    open_type = None
    if open_low >= yday_profile['high']:
        open_type = 'GAP_UP'
    elif open_high <= yday_profile['low']:
        open_type = 'GAP_DOWN'
    elif open_low >= yday_profile['va_h_p']:
        open_type = 'ABOVE_VA'
    elif open_high <= yday_profile['va_l_p']:
        open_type = 'BELOW_VA'
    else:
        open_type = 'INSIDE_VA'
    return open_type

def check_candle_patterns(df):
    op = df['open']
    hi = df['high']
    lo = df['low']
    cl = df['close']
    for pattern in pattern_names:
        # below is same as;
        # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
        df[pattern] = getattr(talib, pattern)(op, hi, lo, cl)
    return df

class DayFullStateGenerator:
    def __init__(self, symbol, day, yday_profile=None):
        self.symbol = symbol
        self.trade_day = day
        self.price_bands = {}
        self.price_bands_reverse = {}
        self.state_transition = []
        self.curr_state = ''
        self.state_queue = []
        self.factored_state_range = []
        self.max_size = 5
        self.slab_range = 0.001
        self.abs_max_state_considered = 0.03
        self.open_type = "UKN"
        self.features_cat = {'candle':'CDL_UNK'}
        self.yday_profile = get_nth_day_profile_data(symbol, self.trade_day, 1).to_dict('records')[0] if yday_profile is None else yday_profile
        self.features_cat['week_day'] = calendar.day_name[self.yday_profile['date'].weekday()]
        hist_data = get_hist_ndays_profile_data(symbol, self.trade_day, 15)
        df = check_candle_patterns(hist_data)
        for pattern in pattern_names:
            if df[pattern].to_list()[-1] > 0:
                self.features_cat['candle'] = pattern + "_UP"
            if df[pattern].to_list()[-1] < 0:
                self.features_cat['candle'] = pattern + "_DN"
        self.set_up_states()

    def set_open_type(self,open_candle):
        self.features_cat['open_type'] = determine_day_open(open_candle, self.yday_profile)

    def set_up_states(self):
        poc = self.yday_profile['poc_price']
        low_rng = np.arange(self.slab_range / 2, self.abs_max_state_considered, self.slab_range)
        low_rng = [x * -1 for x in low_rng]
        low_rng.sort()
        high_rng = np.arange(self.slab_range / 2, self.abs_max_state_considered, self.slab_range)
        total_range = list(low_rng) + list(high_rng)
        poc_idx = [round(len(total_range) / 2) - 1, round(len(total_range) / 2)]
        slabs = total_range
        self.price_bands[(0, round(poc * (1 + min(slabs))))] = 'D99'
        self.price_bands_reverse['D99'] = 0

        for i in range(0, len(total_range) - 1):
            if i < min(poc_idx):
                self.price_bands[round(poc * (1 + slabs[i])) + 0.001, round(poc * (1 + slabs[i + 1]))] = 'D' + str(min(poc_idx) - i)
                self.price_bands_reverse['D' + str(min(poc_idx) - i)] = round(poc * (1 + slabs[i]))
            elif i >= max(poc_idx):
                self.price_bands[round(poc * (1 + slabs[i])) + 0.001, round(poc * (1 + slabs[i + 1]))] = 'U' + str(i - max(poc_idx) + 1)
                self.price_bands_reverse['U' + str(i - max(poc_idx) + 1)] = round(poc * (1 + slabs[i + 1]))
            elif i == min(poc_idx):
                self.price_bands[round(poc * (1 + slabs[i])) + 0.001, round(poc * (1 + slabs[i + 1]))] = 'POC'
                self.price_bands_reverse['POC'] = poc

        self.price_bands[(round(poc * (1 + max(slabs))) + 0.001, 2 * poc)] = 'U99'
        self.price_bands_reverse['U99'] = 2 * poc
        self.factored_state_range = [round(poc * (1 + min(slabs))), round(poc * (1 + max(slabs)))]


    def get_slab_for_price(self, curr_price):
        price_level = "S_UKN"
        if curr_price < min(self.factored_state_range):
            price_level = "D99"
        elif curr_price > max(self.factored_state_range):
            price_level = "U99"
        else:
            for (band, level) in self.price_bands.items():
                if curr_price >= band[0] and curr_price <= band[1]:
                    price_level = level
                    # print(curr_price, price_level, band)
                    break
        return price_level

    def get_intermediate_states(self, start, end):
        #print('get_intermediate_states==', start, end)
        if start is None:
            return [end]
        else:
            state_seq = list(self.price_bands.values())
            tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            if not tr_seq:
                state_seq.reverse()
                tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            return tr_seq

    def update_state(self, curr_price):
        curr_band = self.get_slab_for_price(curr_price)
        self.curr_state = curr_band
        self.state_transition.append(curr_band)
        return curr_band

    def get_features(self):
        self.features_cat['observed_transitions'] = self.state_transition
        return self.features_cat



