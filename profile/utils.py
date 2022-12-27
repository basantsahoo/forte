import numpy as np
from itertools import compress
import json
from config import price_range, tick_steps

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)

def get_next_highest_index(lst, val):
    lst.sort()
    index = -1
    for i in range(len(lst)):
        if lst[i] >= val:
            index = i
            break
    return index


def get_next_lowest_index(lst, val):
    lst.sort()
    #print(range(len(lst) - 1, -1, -1))
    index = -1
    for i in range(len(lst) - 1, -1, -1):
        if lst[i] <= val:
            index = i
            break
    return index


def calculate_balanced_target(poc_price, high, low):
    area_above_poc = high - poc_price
    area_below_poc = poc_price - low
    if area_above_poc >= area_below_poc:
        bt = poc_price - area_above_poc
    else:
        bt = poc_price + area_below_poc
    return bt


def mid_max_idx(array):
    if len(array) == 0:
        return None
    # Find candidate maxima
    maxima_idxs = np.argwhere(array == np.amax(array))[:, 0]
    if len(maxima_idxs) == 1:
        return maxima_idxs[0]
    elif len(maxima_idxs) <= 1:
        return None

    # Find the distances from the midpoint to find
    # the maxima with the least distance
    midpoint = len(array) / 2
    v_norm = np.vectorize(np.linalg.norm)
    maximum_idx = np.argmin(v_norm(maxima_idxs - midpoint))
    return maxima_idxs[maximum_idx]


def calculate_value_area(tpo_sum_arr, poc_idx, value_area_pct):
    #print(tpo_sum_arr, poc_idx, value_area_pct)
    total_tpos = np.sum(tpo_sum_arr)
    desired_tpo_count = np.round(total_tpos * value_area_pct)
    running_count = tpo_sum_arr[poc_idx]
    low_idx = poc_idx
    high_idx = poc_idx
    while running_count < desired_tpo_count:
        #print('running loop,', running_count, desired_tpo_count)
        last_min = low_idx
        last_max = high_idx

        next_low_idx = np.clip(low_idx - 1, 0, len(tpo_sum_arr) - 1)
        next_high_idx = np.clip(high_idx + 1, 0, len(tpo_sum_arr) - 1)

        low_count = tpo_sum_arr[next_low_idx] if next_low_idx != last_min else 0
        high_count = tpo_sum_arr[next_high_idx] if next_high_idx != last_max else 0

        if not high_count and not low_count:
            low_idx = next_low_idx
            high_idx = next_high_idx

        elif not high_count or (low_count and low_count > high_count):
            running_count += low_count
            low_idx = next_low_idx
        elif not low_count or (high_count and low_count <= high_count):
            running_count += high_count
            high_idx = next_high_idx
    return [low_idx, high_idx]


def get_extremes(print_matrix, price_bins, min_co_ext):
    # print(price_bins)
    # print(np.transpose(print_matrix))
    single_print = False
    extreme_low = False
    extreme_high = False
    result = {
        'ext_low': extreme_low,
        'ext_high': extreme_high,
        'sin_print': single_print,
        'low_ext_val': [],
        'high_ext_val': [],
        'sin_print_val': []
    }

    tpo_passed_sum = np.sum(print_matrix, axis=1)
    tpo_passed_letters = list(compress(tpo_passed_sum, list(map(lambda i: i > 0, tpo_passed_sum))))
    # convert to Price bin * TPO
    print_matrix_t = np.transpose(print_matrix)

    if len(tpo_passed_letters) <= 1:
        pass
    elif len(tpo_passed_letters) == 2:
        pass
    else:

        occured_tpos = ~np.all(print_matrix_t == 0, axis=0).A1
        occured_price_bins = ~np.all(print_matrix_t == 0, axis=1).A1
        # filter unoccured tpos and prices
        print_matrix_t = print_matrix_t[:, occured_tpos]
        print_matrix_t = print_matrix_t[occured_price_bins]

        possible_low_extremes = []
        # iterate over all price bins
        for tick_slab_idx in range(print_matrix_t.shape[0]):
            tick_slab = print_matrix_t[tick_slab_idx].A1
            total_visits = sum(tick_slab)
            # Break when more than 2 tpos found for same price. it's not an extreme anymore
            if total_visits <= 2:
                possible_low_extremes.append(tick_slab_idx)
            else:
                break
            """
                consecutive check to be done
                any(i == j for i, j in zip(tick_slab, tick_slab[1:]))
            """
        if len(possible_low_extremes) >= min_co_ext:
            extreme_low = True
        possible_high_extremes = []
        for tick_slab_idx in range(print_matrix_t.shape[0] - 1, 0, -1):
            tick_slab = print_matrix_t[tick_slab_idx].A1
            total_visits = sum(tick_slab)
            if total_visits <= 2:
                possible_high_extremes.append(tick_slab_idx)
            else:
                break
        if len(possible_high_extremes) >= min_co_ext:
            extreme_high = True

        """
        look at single prints from one direction excluding tail from that direction
        Low will find high single prints and vice versa
        take intersetion to find middle ones 
        """
        single_print_l = []
        single_print_h = []
        looking_at_low_tail = True
        for tick_slab_idx in range(1,print_matrix_t.shape[0]-1):
            tick_slab = print_matrix_t[tick_slab_idx].A1
            total_visits = sum(tick_slab)
            if total_visits == 1:
                if not looking_at_low_tail:
                    single_print_l.append(tick_slab_idx)
            else:
                looking_at_low_tail = False
        looking_at_high_tail = True
        for tick_slab_idx in range(print_matrix_t.shape[0]-2,1,-1):
            tick_slab = print_matrix_t[tick_slab_idx].A1
            total_visits = sum(tick_slab)
            if total_visits == 1:
                if not looking_at_high_tail:
                    single_print_h.append(tick_slab_idx)
            else:
                looking_at_high_tail = False
        single_print_vals = list(set(single_print_l).intersection(set(single_print_h)))
        #print(single_print_l)
        #print(single_print_h)
        #print(single_print_vals)
        if len(single_print_vals) > 0:
            single_print = True

            """
                consecutive check to be done
                any(i == j for i, j in zip(tick_slab, tick_slab[1:]))
            """
        """
        print(price_bins)
        print(occured_price_bins)
        print(possible_low_extremes)
        """
        result = {
            'ext_low': extreme_low,
            'ext_high': extreme_high,
            'sin_print': single_print,
            'low_ext_val': np.array(price_bins)[occured_price_bins][possible_low_extremes] if extreme_low else [],
            'high_ext_val': np.array(price_bins)[occured_price_bins][
                possible_high_extremes] if extreme_high else [],
            'sin_print_val': np.array(price_bins)[occured_price_bins][single_print_vals] if single_print else []
        }
    return result

def get_distribution(history, extremes):
    # print(extremes)
    if extremes['ext_low']:
        freq = 0
        for time, candle in history.items():
            if candle['high'] < max(extremes['low_ext_val']):
                freq += 1
        extremes['le_f'] = freq

    if extremes['ext_high']:
        # tmp = np.zeros(len(extremes['high_ext_val']))
        freq = 0
        for time, candle in history.items():
            if candle['low'] > min(extremes['high_ext_val']):
                freq += 1
        extremes['he_f'] = freq

    if extremes['sin_print']:
        # tmp = np.zeros(len(extremes['sin_print_val']))
        freq = 0
        for time, candle in history.items():
            if candle['low'] > min(extremes['sin_print_val']) and candle['high'] < (
                    max(extremes['sin_print_val']) + 0.25):
                freq += 1
        extremes['sp_f'] = freq
    return extremes


def get_tick_size(price):
    idx = get_next_highest_index(price_range, price)
    tick_size = tick_steps[idx]
    return tick_size

