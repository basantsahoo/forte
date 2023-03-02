import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
sys.path.insert(1, project_path)

from db.market_data import get_prev_week_minute_data_by_start_day, get_curr_week_minute_data_by_start_day
from dynamics.profile.weekly_profile import WeeklyMarketProfileService
from dynamics.profile.market_profile import HistMarketProfileService
from datetime import datetime, date
from servers.server_settings import reports_dir
import pandas as pd
import numpy as np
import traceback
from config import default_symbols
from helper.utils import determine_day_open, determine_level_reach, get_overlap, get_percentile, candle_reversal_score
from dynamics.profile.utils import get_next_lowest_index, get_next_highest_index
from helper.time_utils import epoch_to_ordinal


def extract_metrices(processed_data):
    metrices = {
        'open': processed_data['open'],
        'high': processed_data['high'],
        'low': processed_data['low'],
        'close': processed_data['close'],
        'poc_price': processed_data['poc_price'],
        'va_l_p': processed_data['value_area_price'][0],
        'va_h_p': processed_data['value_area_price'][1],
        'va_l_poc_mid': 0.5 * (processed_data['value_area_price'][0] + processed_data['poc_price']),
        'va_l_low_mid': 0.5 * (processed_data['value_area_price'][0] + processed_data['low']),
        'va_h_poc_mid': 0.5 * (processed_data['value_area_price'][1] + processed_data['poc_price']),
        'va_h_high_mid': 0.5 * (processed_data['value_area_price'][1] + processed_data['high']),
        'balance_target': processed_data['balance_target'],
        'h_a_l': processed_data['h_a_l'],
        'low_ext_val': processed_data['profile_dist']['low_ext_val'],
        'high_ext_val': processed_data['profile_dist']['high_ext_val'],
        'sin_print_val': processed_data['profile_dist']['sin_print_val'],
        'p_shape': processed_data['profile_dist']['p_shape'],
        #'p_bin_len': processed_data['profile_dist']['p_bin_len'],
        'range': processed_data['high'] - processed_data['low'],
    }
    return metrices


def relative_profile_position(daily_metrices, last_week_metrices):
    profile_pos = {
        'poc_dir': np.sign(daily_metrices['poc_price'] - last_week_metrices['poc_price']),
        'poc_pos': get_percentile(daily_metrices['poc_price'], [last_week_metrices['high'], last_week_metrices['low']])
    }
    return profile_pos


def calculate_weekly_metrices(symbol, day, week_start_day, start_time):
    t_day = datetime.strptime(day, '%Y-%m-%d') if type(day) == str else day
    t_day_ordinal = t_day.toordinal()
    recent_week_start_str = datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d')
    final_metrics = {}

    # Last week
    df_last_week = get_prev_week_minute_data_by_start_day(symbol, recent_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df_last_week['symbol'] = symbol
    df_last_week['ltp'] = df_last_week['close']
    last_week_recs = df_last_week.to_dict('records')
    lw_processor = WeeklyMarketProfileService()
    lw_processor.set_trade_date_from_time(last_week_recs[0]['timestamp'], last_week_recs[-1]['timestamp'])
    lw_processor.process_input_data(last_week_recs)
    lw_processor.calculateMeasures()
    lw_processed_data = lw_processor.get_profile_data()[0]
    last_week_metrices = extract_metrices(lw_processed_data)

    # Current week
    df_curr_week = get_curr_week_minute_data_by_start_day(symbol, recent_week_start_str, week_start_day=week_start_day, start_time=start_time)
    df_curr_week['ordinal_date'] = df_curr_week['timestamp'].apply(lambda x:epoch_to_ordinal(x))
    curr_week_dates = df_curr_week['ordinal_date'].unique()
    curr_week_dates.sort()

    curr_week_high = max(df_curr_week.high)
    curr_week_low = min(df_curr_week.low)
    df_curr_week['symbol'] = symbol
    df_curr_week['ltp'] = df_curr_week['close']

    curr_week_daily_recs = {}
    for idx in range(len(curr_week_dates)):
        daily_recs = df_curr_week[df_curr_week['ordinal_date'] == curr_week_dates[idx]].to_dict('records')
        curr_week_daily_recs[idx] = daily_recs

    curr_week_recs = df_curr_week.to_dict('records')
    print('start day ====', datetime.fromtimestamp(curr_week_recs[0]['timestamp']))
    first_candle = curr_week_recs[0].copy()
    # Current Week open
    first_candle['open'] = first_candle['close']
    final_metrics['start_date'] = datetime.fromtimestamp(curr_week_recs[0]['timestamp'])
    for key in last_week_metrices.keys():
        final_metrics['lw_' + key] = last_week_metrices[key]
    final_metrics['open_type'] = determine_day_open(first_candle, last_week_metrices)

    for day_idx in curr_week_daily_recs.keys():
        processor = HistMarketProfileService()
        processor.process_input_data(curr_week_daily_recs[day_idx])
        processor.calculateMeasures()
        daily_profile_data = processor.get_profile_data()[0]
        daily_metrices = extract_metrices(daily_profile_data)
        t_metrices = {}
        if day_idx == 0:
            t_metrices['p_shape'] = daily_metrices['p_shape']
            t_metrices['range'] = daily_metrices['range']
            profile_pos = relative_profile_position(daily_metrices, last_week_metrices)
            t_metrices = {**t_metrices, **profile_pos}
        elif day_idx == 1:
            prev_processor = HistMarketProfileService()
            prev_processor.process_input_data(curr_week_daily_recs[day_idx-1])
            prev_processor.calculateMeasures()
            prev_daily_profile_data = prev_processor.get_profile_data()[0]
            prev_daily_metrices = extract_metrices(prev_daily_profile_data)

            t_metrices['p_shape'] = daily_metrices['p_shape']
            t_metrices['range'] = daily_metrices['range']
            profile_pos = relative_profile_position(daily_metrices, prev_daily_metrices)
            t_metrices = {**t_metrices, **profile_pos}
            t_metrices['reversal'] = candle_reversal_score(prev_daily_metrices, daily_metrices)

        for key in t_metrices.keys():
            final_metrics['day_' + str(day_idx) + "_" + key] = t_metrices[key]

    processor = WeeklyMarketProfileService()
    processor.set_trade_date_from_time(curr_week_recs[0]['timestamp'], curr_week_recs[-1]['timestamp'])
    processor.process_input_data(curr_week_recs)
    processor.calculateMeasures()
    processed_data = processor.get_profile_data()[0]
    print_matrix = processed_data['print_matrix']
    price_bins = processed_data['price_bins']

    lk_keys = ['open', 'high', 'low', 'close', 'poc_price', 'va_l_p', 'va_l_poc_mid', 'va_l_low_mid', 'va_h_poc_mid', 'va_h_high_mid', 'va_h_p', 'balance_target']
    week_metrices = dict({
        'open': 0,
        'high': 0,
        'low': 0,
        'close': 0,
        'poc_price': 0,
        'va_l_p': 0,
        'va_l_poc_mid': 0,
        'va_l_low_mid': 0,
        'va_h_poc_mid': 0,
        'va_h_high_mid': 0,
        'va_h_p': 0,
        'balance_target': 0
    })
    for rec in curr_week_recs:
        for l_key in lk_keys:
            level = last_week_metrices[l_key]
            level_reach = determine_level_reach(level, rec)
            if level_reach:
                week_metrices[l_key] += 1
    #print(price_bins)
    visits = print_matrix.sum(axis=0).tolist()[0]
    for l_key in lk_keys:
        #print('l_key', l_key, last_week_metrices[l_key])
        level = last_week_metrices[l_key]
        pb_idx_low = get_next_lowest_index(price_bins, level)
        pb_idx_high = get_next_highest_index(price_bins,level)
        #print(pb_idx_low, pb_idx_high)
        #print(visits[pb_idx_low], visits[pb_idx_high])
        level_reach = (pb_idx_low >= 0) and (pb_idx_high >= 0)
        if level_reach:
            week_metrices[l_key + "_tpo"] = max(visits[pb_idx_low], visits[pb_idx_high])
        else:
            week_metrices[l_key + "_tpo"] = 0

    final_metrics = {**final_metrics, **week_metrices}
    last_candle = curr_week_recs[-1].copy()
    last_candle['open'] = last_candle['close']
    final_metrics['close_type'] = determine_day_open(last_candle, last_week_metrices)
    final_metrics['prev_week_close_to_open'] = first_candle['open'] / last_week_recs[-1]['close'] - 1
    final_metrics['weekly_close_to_close'] = last_candle['close']/last_week_recs[-1]['close'] - 1
    final_metrics['weekly_open_to_close'] = last_candle['close'] / first_candle['open'] - 1
    final_metrics['weekly_close_to_high'] = curr_week_high / last_week_recs[-1]['close'] - 1
    final_metrics['weekly_close_to_low'] = curr_week_low / last_week_recs[-1]['close'] - 1

    return final_metrics


def generate_historical_weekly_profile_chart(ticker, filtered_days, week_start_day, start_time):
    metrices = []
    for day in filtered_days:
        metric = calculate_weekly_metrices(ticker, day, week_start_day, start_time)
        metrices.append(metric)
    df = pd.DataFrame(metrices)
    df.to_csv(reports_dir + 'weekly_metrices.csv')

def generate(tickers=[], days_past=7):
    dateToday = datetime.strptime('2022-12-26', '%Y-%m-%d')#date.today()
    curr_ordinal = dateToday.toordinal()
    last_ordinal = curr_ordinal-days_past
    trade_days = list(range(curr_ordinal, last_ordinal, -7))
    trade_days = [datetime.strftime(datetime.fromordinal(t_day_ordinal), '%Y-%m-%d') for t_day_ordinal in trade_days]
    print(trade_days)

    if len(tickers) == 0:
        tickers = default_symbols #[x.split(":")[1] for x in default_symbols]

    for ticker in tickers:
        generate_historical_weekly_profile_chart(ticker, trade_days, week_start_day="Friday", start_time="9:15:00")


def run():
    print(default_symbols)
    tickers = default_symbols[0:1]
    generate(tickers=tickers, days_past=7)

run()
