import numpy as np
import math
from research.strategies import BaseStrategy
from helper.utils import get_pivot_points, get_overlap
import matplotlib.pyplot as plt
from sklearn.metrics import auc
from statistics import mean
from scipy import stats
from scipy.optimize import curve_fit

class IntradayTrendCalculator:
    def __init__(self, story_book):
        self.story_book = story_book
        self.first_hour_trend = 0
        self.whole_day_trend = 0
        self.five_min_trend = 0
        self.fifteen_min_trend = 0
        self.hourly_5_min_candle_trend = []
        self.hourly_15_min_candle_trend = []
        self.five_min_ex_first_hr_trend = 0
        self.fifteen_min_ex_first_hr_trend = 0
        self.print_calc = False
        self.hurst_exp = -100
        self.ret_trend = -100
        self.poly_fit = -100
        self.trend_params = {}
        self.auc = 0
        self.candles_in_range = 0

    def evaluate(self):
        price_list = list(self.story_book.market_data.values())
        if len(price_list) < 15:
            pass
        else:
            chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
            chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
            chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x
                             in chunks_5]
            chunks_15_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x
                              in chunks_15]
            self.five_min_trend = self.get_candle_trend(chunks_5_ohlc)
            self.fifteen_min_trend = self.get_candle_trend(chunks_15_ohlc)
            """
            if self.print_calc:
                 self.print_calc = False
            """

            hourly_chunk_5 = [chunks_5_ohlc[i:i + 12] for i in range(0, len(chunks_5_ohlc), 12)]
            hourly_chunk_15 = [chunks_15_ohlc[i:i + 4] for i in range(0, len(chunks_15_ohlc), 4)]
            self.hourly_5_min_candle_trend = []

            for hourly_chunk in hourly_chunk_5:
                hourly_trend = self.get_candle_trend(hourly_chunk)
                self.hourly_5_min_candle_trend.append(hourly_trend)

            self.hourly_15_min_candle_trend = []
            for hourly_chunk in hourly_chunk_15:
                hourly_trend = self.get_candle_trend(hourly_chunk)
                self.hourly_15_min_candle_trend.append(hourly_trend)

            trend = (0.75 * self.fifteen_min_trend + 0.25 * self.five_min_trend)
            if len(price_list) <= 60:
                self.first_hour_trend = trend
            else:
                self.whole_day_trend = trend
                self.five_min_ex_first_hr_trend = self.get_candle_trend(chunks_5_ohlc[12::])
                self.fifteen_min_ex_first_hr_trend = self.get_candle_trend(
                    chunks_15_ohlc[4::])

    def get_hurst_exponent(self, time_series, max_lag=10):

        """Returns the Hurst Exponent of the time series"""
        lags = range(2, max_lag)
        # variances of the lagged differences
        tau = [np.std(np.subtract(time_series[lag:], time_series[:-lag])) for lag in lags]
        # calculate the slope of the log plot -> the Hurst Exponent
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        return reg[0]

    def calculate_trend(self, candles, sub_period=3):
        _chunks = [candles[i:i + sub_period] for i in range(0, len(candles), sub_period)]
        _chunks = [_chunk for _chunk in _chunks if len(_chunk) > 1]
        candle_returns = []
        total_returns = []
        for _chunk in _chunks:
            total_return = abs(_chunk[-1][3]/_chunk[0][1] - 1)
            total_returns.append(total_return)
            candle_ret = [(1+abs(candle[3]/candle[1] - 1)) for candle in _chunk]
            cum_ret = np.prod(candle_ret) - 1
            candle_returns.append(cum_ret)

        return sum(total_returns)/sum(candle_returns)

    def get_random_dates(self):
        from datetime import date, timedelta
        import random
        # initializing dates ranges
        test_date1, test_date2 = date(2015, 6, 3), date(2015, 7, 1)
        K = 21
        # getting days between dates
        dates_bet = test_date2 - test_date1
        total_days = dates_bet.days
        res = []
        for idx in range(K):
            res.append(test_date1 + timedelta(days=idx))
        return res

    def calculate_trend_my_exp(self, candles, max_sub_period=10):
        sub_periods = range(2, max_sub_period)
        mu = []
        for sub_period in sub_periods:
            _chunks = [candles[i:i + sub_period] for i in range(0, len(candles)-sub_period)]
            _chunks = [_chunk for _chunk in _chunks if len(_chunk) > 1]
            rets = []

            for _chunk in _chunks:
                #print(_chunk)
                total_return = abs(_chunk[-1][3]/_chunk[0][0] - 1)
                #print(total_return)
                candle_ret = [(1+abs(candle[3]/candle[0] - 1)) for candle in _chunk]
                #print(candle_ret)
                cum_ret = np.prod(candle_ret) - 1
                #print(cum_ret)
                #print(total_return/cum_ret)
                rets.append(total_return/cum_ret)
            #print(mean(rets))
            mu.append(mean(rets))
        """
        import pandas as pd
        df = pd.DataFrame(candles)
        df.columns = ['open', 'high', 'low', 'close']
        df.index = self.get_random_dates()
        df.index = pd.to_datetime(df.index)
        #print(df)
        import mplfinance as mpl
        mpl.plot(
            df,
            type="candle",
            mav=(3, 6, 9),
        )
        """

        reg = np.polyfit(np.log(sub_periods), mu, 2)
        #self.poly_fit = [round(mu[0],2), round(mu[-1]), round(reg[0],3), round(reg[1],3) ,round(reg_2[0],3)]

        #sps = [(x - 2) / max_sub_period for x in sub_periods]
        market_auc = round(auc(sub_periods, mu)/(sub_periods[-1]-sub_periods[0]), 2)

        quadratic_comp = np.poly1d([reg[0], 0, reg[2]])
        linear_comp = np.poly1d([0, reg[1], reg[2]])
        slope, intercept, q_r_value, p_value, std_err = stats.linregress(mu, quadratic_comp(np.log(sub_periods)))
        slope, intercept, l_r_value, p_value, std_err = stats.linregress(mu, linear_comp(np.log(sub_periods)))

        """
        plt.plot(sp_infl, pattern_sp_infl_lvl)
        plt.plot(sp_infl, trendpoly(sp_infl))
        plt.show()

        """
        trend_auc = 0.5 * (mu[-1] + mu[0])
        self.trend_params = {'quad':reg[0], 'lin':reg[1], 'quad_r2':q_r_value ** 2, 'lin_r2':l_r_value ** 2, 'market_auc': market_auc, 'trend_auc': trend_auc, 'mu_0': mu[0], 'mu_n':mu[-1]}

        def exp_func(x,  b, c):
            a = 1
            return a * np.exp(-b * x) + c

        popt, pcov = curve_fit(exp_func, np.log(sub_periods), mu)
        self.trend_params['exp_b'] = popt[0]
        self.trend_params['exp_c'] = popt[1]

        """
        print('popt', popt)
        trendpoly = np.poly1d(reg)
        plt.plot(np.log(sub_periods), mu)
        #plt.plot(np.log(sub_periods), trendpoly(np.log(sub_periods)))
        plt.plot(np.log(sub_periods), exp_func(np.log(sub_periods), *popt), 'r-', label='fit:  b=%5.3f, c=%5.3f' % tuple(popt))
        plt.show()
        #print(list(sub_periods))
        #print(sps)
        """
        
        
        """
        plt.title(self.story_book.trade_day)
        plt.show()
        """




    def evaluate2(self):
        #print('evaluate2', self.print_calc)
        if self.print_calc:
            self.print_calc = False
            price_list = list(self.story_book.market_data.values())
            chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
            chunks_15_ohlc = [[x[0]['open'], max([y['high'] for y in x]), min([y['low'] for y in x]), x[-1]['close']] for x
                              in chunks_15]
            first_hr = price_list[0:60]
            remaining = price_list[60::]
            remaining_series = [x[3] for x in chunks_15_ohlc]
            he = self.get_hurst_exponent(remaining_series)
            print('hurst exponent++++++++++', he)
            first_hr_ohlc = [first_hr[0]['open'], max([y['high'] for y in first_hr]), min([y['low'] for y in first_hr]), first_hr[-1]['close']]
            first_hr_range = first_hr_ohlc[1] - first_hr_ohlc[2]
            in_range_candles = 0
            for candle in chunks_15_ohlc[4::]:
                ol = get_overlap([min(candle[0], candle[3]), max(candle[0], candle[3])], [first_hr_ohlc[2], first_hr_ohlc[1]])
                body = abs(candle[0] - candle[3])
                ol_pct = ol/(body if body > 0 else 1)

                #print(ol_pct)
                if ol_pct >= 0.67:
                    in_range_candles += 1
                #print(in_range_candles)
            print(self.story_book.trade_day, ' total candles in range' , in_range_candles/len(chunks_15_ohlc[4::]))
            ret_trend = self.calculate_trend(chunks_15_ohlc[4::])
            print('return trend', ret_trend)


    def calculate_measures(self):
        #print('evaluate2', self.print_calc)
        if self.print_calc:
            self.print_calc = False
            price_list = list(self.story_book.market_data.values())
            chunks_15 = [price_list[i:i + 15] for i in range(0, len(price_list), 15)]
            chunks_15_ohlc = [[x[0]['open'], max([y['high'] for y in x]), min([y['low'] for y in x]), x[-1]['close']] for x in chunks_15]
            chunks_5 = [price_list[i:i + 5] for i in range(0, len(price_list), 5)]
            chunks_5_ohlc = [[x[0]['open'], max(y['high'] for y in x), min(y['low'] for y in x), x[-1]['close']] for x in chunks_5]

            first_hr = price_list[0:60]
            remaining_series = [x[3] for x in chunks_15_ohlc]

            first_hr_ohlc = [first_hr[0]['open'], max([y['high'] for y in first_hr]), min([y['low'] for y in first_hr]), first_hr[-1]['close']]
            first_hr_range = first_hr_ohlc[1] - first_hr_ohlc[2]
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
            self.hurst_exp = round(self.get_hurst_exponent(remaining_series),2)
            self.ret_trend = round(self.calculate_trend(chunks_15_ohlc[4::]),2)
            self.calculate_trend_my_exp(chunks_15_ohlc[4::])  #15 mins used for eod

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
        """
        if self.print_calc:
            print(chunks_ohlc)
            print(candle_size_trends)
            print(candle_direction_trends)
            print(overlap_trends)
            print(return_trends)
        """
        # trend = 0.25 * (np.sign(sum(candle_size_trends)) + np.sign(sum(candle_direction_trends)) + np.sign(sum(overlap_trends)) + np.sign(sum(return_trends)))
        trend = 0.25 * (sum(candle_size_trends) + sum(candle_direction_trends) + sum(overlap_trends) + sum(
            return_trends)) / len(chunks_ohlc)
        return trend
        # print(trend)
    def signal(self):
        if not self.direction_calculated:
            self.calculate_direction()
        #print('signal')
