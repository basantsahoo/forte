import pytz
from datetime import datetime
import numpy as np
symbol_map = {'NIFTY': {'index':'NIFTY 50', 'option_chain': 'NIFTY', 'fyers_index': 'NSE:NIFTY50-INDEX', 'td_index':'NIFTY 50'},
              'BANKNIFTY': {'index':'NIFTY BANK', 'option_chain': 'BANKNIFTY', 'fyers_index': 'NSE:NIFTYBANK-INDEX', 'td_index':'NIFTY BANK'}
              }
order_type_dict = {'LONG': 1, 'SHORT': -1, 'BUY': 1, 'SELL': -1, 1: 1, -1: -1}
instr_type_dict = {'LONG': 'CE', 'SHORT': 'PE', 'BUY': 'CE', 'SELL': 'PE'}
exit_order_type_dict = {'LONG': 'SHORT', 'SHORT': 'LONG', 'BUY': 'SELL', 'SELL': 'BUY', 1: -1, -1: 1}

tz_ist = pytz.timezone('Asia/Kolkata')

def normalize_symbol(symbol):
    if "BANK" in symbol:
        return "NIFTYBANK"
    elif "NIFTY" in symbol:
        return "NIFTY50"


def root_symbol(symbol):
    suffix = "-I" if "-I" in symbol else ""
    if "BANK" in symbol:
        return "BANKNIFTY" + suffix
    elif "NIFTY" in symbol:
        return "NIFTY" + suffix


def get_fyers_symbol(symbol):
    normalized_symbol = normalize_symbol(symbol)
    return "NSE:" + normalized_symbol + "-INDEX"


def get_options_feed_room(symbol):
    _symbol = root_symbol(symbol)
    return _symbol+"_OPTIONS"


def get_nse_index_symbol(symbol):
    return symbol_map[root_symbol(symbol)]['index']


def get_oc_symbol(symbol):
    return symbol_map[root_symbol(symbol)]['option_chain']


def get_fyers_index_symbol(symbol):
    return symbol_map[root_symbol(symbol)]['fyers_index']

def get_td_index_symbol(symbol):
    return symbol_map[root_symbol(symbol)]['td_index']

def standardize_feed(feed):
    feed['symbol'] = root_symbol(feed['symbol'])
    feed['timestamp'] = feed['timestamp'] if type(feed['timestamp']) == int else int(datetime.fromisoformat(feed['timestamp'] + '+05:30').timestamp())
    if 'ltp' not in feed:
        feed['ltp'] = feed['close']
    if 'close' not in feed:
        feed['close'] = feed['ltp']
    if 'min_volume' not in feed:
        feed['min_volume'] = feed.get('volume', 0)
    return feed


def day_from_epoc_time(epoch_tick_time):
    tick_date_time = datetime.fromtimestamp(epoch_tick_time)
    return tick_date_time.strftime('%Y-%m-%d')


def get_broker_order_type(order_type):
    return order_type_dict[order_type]


def get_exit_order_type(order_type):
    return exit_order_type_dict[order_type]


def get_lot_size(index):
    return 50 if index == 'NIFTY' else 25 if index == 'BANKNIFTY' else 0


def get_overlap(overlap_of, compared_with):
    overlap_of.sort()
    compared_with.sort()
    return max(0, min(overlap_of[1], compared_with[1]) - max(overlap_of[0], compared_with[0]))

def compare_day_activity(compare_day, against_day):
    resp = {}
    compare_day_range = [compare_day['low'], compare_day['high']]
    against_day_range = [against_day['low'], against_day['high']]
    overlap = [max(compare_day_range[0], against_day_range[0]), min(compare_day_range[1], against_day_range[1])] if min(compare_day_range[1], against_day_range[1]) > max(compare_day_range[0], against_day_range[0]) else []
    # compare day calculations
    higher_price_region = [against_day_range[1], compare_day_range[1]] if compare_day_range[1] > against_day_range[1] else []
    lower_price_region = [compare_day_range[0], against_day_range[0]] if compare_day_range[0] < against_day_range[0] else []
    resp['cd_support_pressure'] = round((min(compare_day['open'], compare_day['close']) - compare_day['low']) / (compare_day['high'] - compare_day['low']), 2)
    resp['cd_resistance_pressure'] = round((compare_day['high'] - max(compare_day['open'], compare_day['close'])) / (compare_day['high'] - compare_day['low']), 2)
    resp['cd_new_business_pressure'] = round(1 - resp['cd_support_pressure'] - resp['cd_resistance_pressure'], 2)
    resp['cd_type'] = 1 if (compare_day['close'] - compare_day['open']) > 0 else -1
    resp['cd_retest_fract'] = round(((overlap[1] - overlap[0]) if len(overlap) else 0) / (compare_day['high'] - compare_day['low']), 2)
    # against day calculations
    resp['ad_support_pressure'] = round((min(against_day['open'], against_day['close']) - against_day['low']) / (against_day['high'] - against_day['low']), 2)
    resp['ad_resistance_pressure'] = round((against_day['high'] - max(against_day['open'], against_day['close'])) / (against_day['high'] - against_day['low']), 2)
    resp['ad_new_business_pressure'] = round(1 - resp['ad_support_pressure'] - resp['ad_resistance_pressure'], 2)
    resp['ad_retest_fract'] = round(((overlap[1] - overlap[0]) if len(overlap) else 0) / (against_day['high'] - against_day['low']), 2)
    resp['ad_type'] = 1 if (against_day['close'] - against_day['open']) > 0 else -1
    resp['gap'] = round(((compare_day['open'] - against_day['high']) if compare_day['open'] > against_day['high'] else (compare_day['open'] - against_day['low']) if compare_day['open'] < against_day['low'] else 0) / against_day['poc_price'], 4)
    resp['cd_close_rat'] = round((compare_day['close'] / against_day['poc_price'] - 1) * 100, 2)
    level_keys = ['high', 'low', 'poc_price', 'va_h_p', 'va_l_p']
    for k in level_keys:
        level_range = [against_day[k] * (1 - 0.0015), against_day[k] * (1 + 0.0015)]
        ol = get_overlap(level_range, [compare_day['low'], compare_day['high']])
        resp['ad_'+k] = int(ol > 0)
    return resp


def get_pivot_points(data_ohlc):

    try:
        data_ohlc['Pivot'] = round((data_ohlc['high'] + data_ohlc['low'] + data_ohlc['close'])/3, 0)
        data_ohlc['R1'] = round((2*data_ohlc['Pivot']) - data_ohlc['low'], 0)
        data_ohlc['S1'] = round((2*data_ohlc['Pivot']) - data_ohlc['high'], 0)
        data_ohlc['R2'] = round((data_ohlc['Pivot']) + (data_ohlc['high'] - data_ohlc['low']), 0)
        data_ohlc['S2'] = round((data_ohlc['Pivot']) - (data_ohlc['high'] - data_ohlc['low']), 0)
        data_ohlc['R3'] = round((data_ohlc['R1']) + (data_ohlc['high'] - data_ohlc['low']), 0)
        data_ohlc['S3'] = round((data_ohlc['S1']) - (data_ohlc['high'] - data_ohlc['low']), 0)
        data_ohlc['R4'] = round((data_ohlc['R3']) + (data_ohlc['R2'] - data_ohlc['R1']), 0)
        data_ohlc['S4'] = round((data_ohlc['S3']) - (data_ohlc['S1'] - data_ohlc['S2']), 0)
    except:
        pass
    #print('get_pivot_points++++++++++++++++++++++++++++++++++++++++++++++', data_ohlc)
    return data_ohlc


def generate_random_ivs():
    tz = pytz.timezone('Asia/Kolkata')
    now = tz.localize(datetime.now(), is_dst=None)
    now = now.replace(hour=9, minute=15, second=0, microsecond=0)
    start_time = int(now.timestamp())
    #print(start_time)
    period_in_minutes = 6.25 * 60 + 1

    mu = 0.0005
    sigma = 0.0001
    dt = 1 / period_in_minutes
    np.random.seed(100)

    iv_0 = 0.23
    returns = np.random.normal(loc=mu * dt, scale=sigma, size=int(period_in_minutes))
    ivs = iv_0 * (1 + returns).cumprod()
    return ivs

def pattern_param_match(pat_points,tmppar,tmprat):
    pattern_match = True
    if len(tmppar) != pat_points:
        print("Pattern Definition not correct")
        pattern_match = False
        #break
    else:
        itrk = range(0,len(tmppar))
        for k in itrk:
            #print(type(tmppar[k]))
            if ((type(tmppar[k]) is int) or (type(tmppar[k]) is float) or (type(tmppar[k]) is np.float64)):
                if tmppar[k] != 1024:
                    if tmppar[k]<0:
                        pattern_match = True if tmprat[k]<=(1+tmppar[k]) else False
                    elif tmppar[k] ==0:
                        pattern_match = True if tmprat[k]==(1+tmppar[k]) else False
                    else:
                        pattern_match = True if tmprat[k]>=(1+tmppar[k]) else False
            elif(type(tmppar[k]) is list):
                pattern_match = True if((tmprat[k]<=(1+tmppar[k][1])) and (tmprat[k]>=(1+tmppar[k][0]))) else False
            else:
                print("Pattern Defination type is not correct")
                pattern_match =  False
            if(not pattern_match):
                break
    return pattern_match


def get_time_to_expiry(expiry_dt, curr_time=None):
    expiry_dt = tz_ist.localize(expiry_dt)
    expiry_dt = expiry_dt.replace(hour=15, minute=30, second=0)
    if curr_time is None:
        curr_time = datetime.now(tz_ist)
    else:
        if curr_time.tzinfo is None:
            curr_time = curr_time.replace(tzinfo=tz_ist)
    diff_sec = (expiry_dt - curr_time).total_seconds()
    return diff_sec

def get_time_to_expiry_from_day_end(expiry_dt):
    expiry_dt = tz_ist.localize(expiry_dt) #.replace(tzinfo=tz_ist)
    expiry_dt = expiry_dt.replace(hour=15, minute=30, second=0)
    curr_time = datetime.now(tz_ist)
    curr_time = curr_time.replace(hour=15, minute=15, second=0)
    diff_sec = (expiry_dt - curr_time).total_seconds()

    return diff_sec

def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    check_time = check_time or datetime.now(tz_ist).time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def get_epoc_minute(time_stamp):
    epoch_tick_time = time_stamp
    epoch_minute = int(epoch_tick_time / 60) * 60
    return epoch_minute

def get_epoc_from_iso_format(iso_ts):
    epoch_tick_time = int(datetime.fromisoformat(iso_ts + '+05:30').timestamp())
    return epoch_tick_time


def convert_to_candle(lst):

    candle = {'timestamp': lst[0]['timestamp'], 'open': lst[0]['open'], 'high': max([y['high'] for y in lst]),
      'low': min([y['low'] for y in lst]), 'close': lst[-1]['close']}
    return candle

def locate_point(df, threshold):
    above = len(np.array(df.index[df.Close > threshold]))
    below = len(np.array(df.index[df.Close <= threshold]))
    pct = (1 - above / (above + below)) * 100
    return pct


def get_option_strike(ltp, money_ness, level, kind):
    atm_strike = round(ltp / 100) * 100
    level = -100 * level if kind == 'PE' else level * 100
    otm_strike = atm_strike + level
    itm_strike = atm_strike - level
    strike = otm_strike if money_ness == 'OTM' else itm_strike if money_ness == 'ITM' else atm_strike
    return strike


def determine_day_open(open_candle, profile): ## this is definitive
    open_low = open_candle['open']
    open_high = open_candle['open']
    if open_low >= profile['high']:
        open_type = 'GAP_UP'
    elif open_high <= profile['low']:
        open_type = 'GAP_DOWN'
    elif open_low >= profile['va_h_p']:
        open_type = 'ABOVE_VA'
    elif open_high <= profile['va_l_p']:
        open_type = 'BELOW_VA'
    else:
        open_type = 'INSIDE_VA'
    return open_type


def determine_level_reach(level, candle):
    level_range = [level * (1 - 0.00015), level * (1 + 0.00015)]
    ol = get_overlap(level_range, [candle['low'], candle['high']])
    return ol > 0
