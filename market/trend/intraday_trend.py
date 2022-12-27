import numpy as np
import math
from helper.utils import get_pivot_points, get_overlap
import matplotlib.pyplot as plt
from sklearn.metrics import auc
from statistics import mean
from scipy import stats
from scipy.optimize import curve_fit
import talib
import pandas as pd
from itertools import compress
from trend.candle_rank import candle_rankings

candle_names = talib.get_function_groups()['Pattern Recognition']
#print(len(candle_names))
#print(candle_names)

class IntradayTrendCalculator:
    def __init__(self, insight_book):
        self.insight_book = insight_book
        self.first_hour_trend = 0
        self.whole_day_trend = 0
        self.five_min_trend = 0
        self.fifteen_min_trend = 0
        self.five_min_ex_first_hr_trend = 0
        self.fifteen_min_ex_first_hr_trend = 0
        self.print_calc = False
        self.hurst_exp_15 = -100
        self.hurst_exp_5 = -100
        self.ret_trend = -100
        self.trend_params = {}
        self.candles_in_range = 0


    def get_hurst_exponent(self, time_series, max_lag=10):
        """Returns the Hurst Exponent of the time series"""
        #print(time_series)
        max_lag = min(max_lag, len(time_series))
        lags = range(2, max_lag)
        # variances of the lagged differences

        tau = [np.std(np.subtract(time_series[lag:], time_series[:-lag])) for lag in lags]
        tau_idx = [not (np.isnan(x) or x == 0) for x in tau]
        filtered_tau = [i for (i, v) in zip(tau, tau_idx) if v]
        filtered_lags = [i for (i, v) in zip(lags, tau_idx) if v]
        # calculate the slope of the log plot -> the Hurst Exponent
        reg = np.polyfit(np.log(filtered_tau), np.log(filtered_lags), 1)
        return reg[0]

    def calculate_trend(self, candles, sub_period=3):
        _chunks = [candles[i:i + sub_period] for i in range(0, len(candles), sub_period)]
        _chunks = [_chunk for _chunk in _chunks if len(_chunk) > 1]
        candle_returns = []
        total_returns = []
        res = 0
        for _chunk in _chunks:
            total_return = abs(_chunk[-1][3]/_chunk[0][1] - 1)
            total_returns.append(total_return)
            candle_ret = [(1+abs(candle[3]/candle[1] - 1)) for candle in _chunk]
            cum_ret = np.prod(candle_ret) - 1
            candle_returns.append(cum_ret)
        try:
            res = sum(total_returns)/sum(candle_returns)
        except:
            pass
        return res


    def calculate_trend_my_exp(self, candles, max_sub_period=10):
        sub_periods = range(2, max_sub_period)
        mu = []
        for sub_period in sub_periods:
            _chunks = [candles[i:i + sub_period] for i in range(0, len(candles)-sub_period)]
            _chunks = [_chunk for _chunk in _chunks if len(_chunk) > 1]
            rets = []
            for _chunk in _chunks:
                total_return = abs(_chunk[-1][3]/_chunk[0][0] - 1)
                candle_ret = [(1+abs(candle[3]/candle[0] - 1)) for candle in _chunk]
                cum_ret = np.prod(candle_ret) - 1
                rets.append(total_return/cum_ret)
            mu.append(mean(rets))
        reg = np.polyfit(np.log(sub_periods), mu, 2)
        market_auc = round(auc(sub_periods, mu)/(sub_periods[-1]-sub_periods[0]), 2)
        quadratic_comp = np.poly1d([reg[0], 0, reg[2]])
        linear_comp = np.poly1d([0, reg[1], reg[2]])
        slope, intercept, q_r_value, p_value, std_err = stats.linregress(mu, quadratic_comp(np.log(sub_periods)))
        slope, intercept, l_r_value, p_value, std_err = stats.linregress(mu, linear_comp(np.log(sub_periods)))
        trend_auc = 0.5 * (mu[-1] + mu[0])
        self.trend_params = {'quad':round(reg[0], 4), 'lin':round(reg[1], 4), 'quad_r2':round(q_r_value ** 2, 2), 'lin_r2':round(l_r_value ** 2, 2), 'market_auc': round(market_auc, 4), 'trend_auc': round(trend_auc, 4), 'auc_del': round(market_auc-trend_auc, 4), 'mu_0': round(mu[0], 2), 'mu_n':round(mu[-1], 2)}
        def exp_func(x,  b, c):
            a = 1
            return a * np.exp(-b * x) + c

        popt, pcov = curve_fit(exp_func, np.log(sub_periods), mu)
        self.trend_params['exp_b'] = round(popt[0],4)
        self.trend_params['exp_c'] = round(popt[1],4)



    def calculate_measures(self):
        price_list = list(self.insight_book.market_data.values())
        if len(price_list) < 15:
            return

        chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
        chunks_15_ohlc = [[x[0]['open'], max([y['high'] for y in x]), min([y['low'] for y in x]), x[-1]['close']] for x in chunks_15]
        chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
        chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]
        series_15_close = [x[3] for x in chunks_15_ohlc]
        series_5_close = [x[3] for x in chunks_5_ohlc]
        first_hr = price_list[0:60]
        first_hr_ohlc = [first_hr[0]['open'], max([y['high'] for y in first_hr]), min([y['low'] for y in first_hr]), first_hr[-1]['close']]
        self.five_min_trend = self.get_candle_trend(chunks_5_ohlc)
        self.fifteen_min_trend = self.get_candle_trend(chunks_15_ohlc)
        if len(price_list) <= 60:
            self.first_hour_trend = (0.25 * self.fifteen_min_trend + 0.75 * self.five_min_trend)
        else:
            self.whole_day_trend = (0.25 * self.fifteen_min_trend + 0.75 * self.five_min_trend)
            self.five_min_ex_first_hr_trend = self.get_candle_trend(chunks_5_ohlc[12::])
            self.fifteen_min_ex_first_hr_trend = self.get_candle_trend(chunks_15_ohlc[4::])
            in_range_candles = 0
            for candle in chunks_15_ohlc[4::]:
                ol = get_overlap([min(candle[0], candle[3]), max(candle[0], candle[3])], [first_hr_ohlc[2], first_hr_ohlc[1]])
                body = abs(candle[0] - candle[3])
                ol_pct = ol/(body if body > 0 else 1)
                #print(ol_pct)
                if ol_pct >= 0.67:
                    in_range_candles += 1
                #print(in_range_candles)
            self.candles_in_range = round(in_range_candles/len(chunks_15_ohlc[4::]),2)
            self.ret_trend = round(self.calculate_trend(chunks_15_ohlc[4::]), 2)
            self.calculate_trend_my_exp(chunks_5_ohlc)  # 15 mins used for eod
            self.hurst_exp_15 = round(self.get_hurst_exponent(series_15_close), 2)
            self.hurst_exp_5 = round(self.get_hurst_exponent(series_5_close), 2)
        #self.check_candle_patterns(chunks_5_ohlc)

    def check_candle_patterns(self,chunks_ohlc):
        print('test candle pattern')
        df = pd.DataFrame(chunks_ohlc)
        df.columns = ['open', 'high', 'low', 'close']

        df = df.iloc[-5:, :]

        op = df['open']
        hi = df['high']
        lo = df['low']
        cl = df['close']

        for candle in candle_names:
            # below is same as;
            # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
            df[candle] = getattr(talib, candle)(op, hi, lo, cl)
        df['candlestick_pattern'] = np.nan
        df['candlestick_match_count'] = np.nan
        for index, row in df.iterrows():

            # no pattern found
            if len(row[candle_names]) - sum(row[candle_names] == 0) == 0:
                df.loc[index, 'candlestick_pattern'] = "NO_PATTERN"
                df.loc[index, 'candlestick_match_count'] = 0
            # single pattern found
            elif len(row[candle_names]) - sum(row[candle_names] == 0) == 1:
                # bull pattern 100 or 200
                if any(row[candle_names].values > 0):
                    pattern = list(compress(row[candle_names].keys(), row[candle_names].values != 0))[0] + '_Bull'
                    df.loc[index, 'candlestick_pattern'] = pattern
                    df.loc[index, 'candlestick_match_count'] = 1
                # bear pattern -100 or -200
                else:
                    pattern = list(compress(row[candle_names].keys(), row[candle_names].values != 0))[0] + '_Bear'
                    df.loc[index, 'candlestick_pattern'] = pattern
                    df.loc[index, 'candlestick_match_count'] = 1
            # multiple patterns matched -- select best performance
            else:
                # filter out pattern names from bool list of values
                patterns = list(compress(row[candle_names].keys(), row[candle_names].values != 0))
                container = []
                for pattern in patterns:
                    if row[pattern] > 0:
                        container.append(pattern + '_Bull')
                    else:
                        container.append(pattern + '_Bear')
                rank_list = [candle_rankings[p] for p in container if p in candle_rankings]
                if len(rank_list) == len(container):
                    rank_index_best = rank_list.index(min(rank_list))
                    df.loc[index, 'candlestick_pattern'] = container[rank_index_best]
                    df.loc[index, 'candlestick_match_count'] = len(container)
        # clean up candle columns
        #print(df.head().T)
        df.drop(candle_names, axis=1, inplace=True)

    def get_candle_trend(self,chunks_ohlc):
        candle_size_trends = []
        candle_direction_trends = []
        overlap_trends = []
        return_trends = []
        for i in range(len(chunks_ohlc)):
            candle = chunks_ohlc[i]
            # print(candle)
            open = candle[0]
            high = candle[1]
            low = candle[2]
            close = candle[3]
            body = abs(close - open)
            length = high - low
            tail = length - body
            mid = 0.5 * (high + low)
            ut = high - max(close, open)
            lt = min(close, open) - low
            if body >= 0.7 * length:
                if close > open:
                    candle_size_trends.append(1)
                else:
                    candle_size_trends.append(-1)
            elif body >= 0.3 * length:
                if ut > 2 * lt:
                    if close < open:
                        candle_size_trends.append(-1)
                    else:
                        candle_size_trends.append(0)
                elif lt > 2 * ut:
                    if open < close:
                        candle_size_trends.append(1)
                    else:
                        candle_size_trends.append(0)
                else:
                    candle_size_trends.append(0)
            elif ut > 2.5 * lt:
                candle_size_trends.append(-1)
            elif lt > 2.5 * ut:
                candle_size_trends.append(1)
            else:
                candle_size_trends.append(0)
            if i > 0:
                prev_candle = chunks_ohlc[i - 1]
                prev_mid = 0.5 * (prev_candle[1] + prev_candle[2])
                dir = 0
                if mid > (1 + 0.0009) * prev_mid:
                    dir = 1
                elif mid < (1 - 0.0009) * prev_mid:
                    dir = -1
                candle_direction_trends.append(dir)
                curr_range = list(range(int(math.floor(low)), int(math.ceil(high)) + 1, 1))
                prev_range = list(range(int(math.floor(prev_candle[2])), int(math.ceil(prev_candle[1])) + 1, 1))
                overlap = list(set(curr_range) & set(prev_range))
                overlap_pct = len(overlap) / len(prev_range)
                if overlap_pct < 0.5:
                    overlap_trends.append(dir)
                else:
                    overlap_trends.append(0)
                if close < prev_candle[3]:
                    return_trends.append(-1)
                else:
                    return_trends.append(1)
        trend = 0.25 * (sum(candle_size_trends) + sum(candle_direction_trends) + sum(overlap_trends) + sum(
            return_trends)) / len(chunks_ohlc)
        return trend
