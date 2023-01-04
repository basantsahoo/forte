import numpy as np
from research.strategies import BaseStrategy
from helper.utils import get_exit_order_type, pattern_param_match
from helper.utils import pattern_param_match
from trend.technical_patterns import pattern_engine
from statistics import mean

dt_between_highs_diff = 0.0005

class PriceActionPatternStrategy(BaseStrategy):
    def __init__(self, insight_book, pattern, order_type, exit_time, period, trend=None, min_tpo=None, max_tpo=None, record_metric=True):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = pattern + "_" + str(period) + "_" + order_type + "_" + str(exit_time)
        #print(self.id)
        self.pattern = pattern
        self.order_type = order_type
        self.insight_book = insight_book
        self.last_match = None
        self.exit_time = exit_time
        self.period = period
        self.record_metric = record_metric
        self.trend = trend

    #def




    def check_dt_pattern(self, df2):
        pecentile_th = 75
        pecentile_price_level = min(df2['Close']) + (max(df2['Close']) - min(df2['Close'])) * pecentile_th / 100
        sp_infl = np.where([df2.SPExt != ''])[1]
        sp_infl = sp_infl[:-1]  # ignoring last one as it keeps on changing -- added newly
        #print(sp_infl)
        ret_val = []
        if len(sp_infl) > 4 and df2.SPExt[sp_infl[-1]] == 'SPH': #minimum 4 inflex required excluding last one (To do when sharp fall after last inflex and last inflext takes long time)
            recent_infl_idx = np.where([df2.SPExt != ''])[1][-1]  # most recent
            recent_infl_price = df2.Close[recent_infl_idx]
            df_infl = df2.iloc[sp_infl,:]
            last_pattern_infl_idx = sp_infl[-1] #point 4
            last_pattern_infl_price = df2.Close[last_pattern_infl_idx]
            # Search all previous highs for possible match
            df_infl_high = df_infl[(df_infl['SPExt'] == 'SPH') & (df_infl.index < last_pattern_infl_idx)][['SPExt', 'Close']]
            itr = list(df_infl_high.index)
            itr.reverse()
            sph_idx_to_check = []
            for i in itr:
                if df_infl_high.Close[i]/last_pattern_infl_price > (1+dt_between_highs_diff):
                    break
                elif df_infl_high.Close[i]/last_pattern_infl_price > (1-dt_between_highs_diff):
                    sph_idx_to_check.append(i) #possible point 2

            # try to form pattern with all possible prev highs
            for idx in sph_idx_to_check:
                tmp_df_infl = df_infl[(df_infl.index > idx) & (df_infl.index < last_pattern_infl_idx)]
                minima = min(tmp_df_infl.Close)
                # Third point found
                #minima_idx = np.where([tmp_df_infl.Close == minima])[1]
                minima_idx = tmp_df_infl[tmp_df_infl['Close'] == minima].index[0] #point 3
                #print('minima_idx', minima_idx)
                # Look for first point
                possible_first_df = df_infl[(df_infl.index < idx)]
                itr2 = list(possible_first_df.index)
                itr2.reverse() # search from last point

                idx_to_check = []
                for i in itr2:
                    #print('iteration', i)
                    # break if there is a point above second point
                    if possible_first_df.Close[i] > df2.Close[idx]: #minima:
                        break
                    else:
                        idx_to_check.append(i)  # possible point 2

                if len(idx_to_check) > 0:
                    first_point_price = min(possible_first_df.Close[idx_to_check])
                    height = last_pattern_infl_price - minima
                    print(first_point_price, minima, last_pattern_infl_price,recent_infl_price)
                    if (minima - first_point_price) >= height and recent_infl_price < minima:
                        first_point_idx = possible_first_df[possible_first_df['Close'] == first_point_price].index[0]
                        #print(first_point_idx)
                        ret_val = [[df2.Time[first_point_idx], df2.Time[idx], df2.Time[minima_idx],df2.Time[last_pattern_infl_idx], df2.Time[recent_infl_idx]],
                                  [first_point_price, df2.Close[idx], minima,  last_pattern_infl_price]]
                        print('occured at length', df2.shape[0])
                        print('total highs found', len(sph_idx_to_check))
                        print('highs ', df_infl_high)
                        print('first_point_price ', first_point_price)
                        print('recent_price ', recent_infl_price)
                        print([first_point_idx, last_pattern_infl_idx, [first_point_price, df2.Close[idx],minima, last_pattern_infl_price]])
            # find price near to last_price
        return ret_val

    def check_pattern(self, df2):
        if self.pattern == "DT":
            return self.check_dt_pattern(df2)
        pattern_config = pattern_engine[self.pattern]
        sp_infl = np.where([df2.SPExt != ''])[1]
        sp_infl = sp_infl[:-1] #ignoring last one as it keeps on changing -- added newly
        pat_points = pattern_config['len']
        pattern_infl = pattern_config['pattern']
        pattern_params = pattern_config['params']
        is_pattern_match = True
        if len(sp_infl) >= pat_points+2: #+2 added for trend
            pattern_sp_infl_idx = sp_infl[range(-pat_points, -0)]
            pat = df2.SPExt[pattern_sp_infl_idx]


            is_pattern_match = np.array_equal(pattern_infl, pat)
            if is_pattern_match:
                pattern_sp_infl_Lvl = df2.Close[pattern_sp_infl_idx].tolist()
                prev_trend_sp_infl_Lvl = df2.Close[sp_infl[range(-pat_points - 2, -pat_points)]]
                curr_trend = 'UP' if mean(prev_trend_sp_infl_Lvl) < pattern_sp_infl_Lvl[0] else 'DOWN'
                if self.trend is not None and (curr_trend != self.trend):
                    is_pattern_match = False
                elif len(pattern_params) != pat_points:
                    # print("Pattern Definition not correct")
                    is_pattern_match = False
                    """
                    if pattern_sp_infl_idx[0] == 76:
                        print(pat)
                        print(is_pattern_match)
                    """
                else:
                    itr = range(0, pat_points)
                    for j in itr:
                        tmprat = [pattern_sp_infl_Lvl[j] / myval for myval in pattern_sp_infl_Lvl]
                        tmppar = pattern_params[j]
                        is_pattern_match = pattern_param_match(pat_points, tmppar, tmprat)
                        if not is_pattern_match:
                            # print("Exiting Loop because match didnt found")
                            break
                #print('pattern+', is_pattern_match)
                if is_pattern_match and 'curval' in pattern_config.keys():
                    close = df2['Close'][-1]
                    tmprat = [close / myval for myval in pattern_sp_infl_Lvl]
                    tmppar = pattern_config['curval']
                    is_pattern_match = pattern_param_match(pat_points, tmppar, tmprat)
                #print('currval+', is_pattern_match)
                """
                if is_pattern_match:
                    print(pattern_sp_infl_idx)
                """
        else:
            is_pattern_match = False
        output = []
        if is_pattern_match:
            start_ind = sp_infl[-pat_points]
            end_ind = sp_infl[-1]
            output = [df2.Time[start_ind], df2.Time[end_ind], df2.Close[sp_infl[range(-pat_points, -0)]].tolist()]
        return output

    def evaluate(self):
        self.close_existing_positions()
        pattern_df = self.insight_book.get_inflex_pattern_df(self.period).dfstock_3
        #print(pattern_df)
        if pattern_df is not None:
            pattern_match_idx = self.check_pattern(pattern_df)
            if len(pattern_match_idx) > 0 and len(self.insight_book.market_data.items()) < 375-self.exit_time:
                if pattern_match_idx[0][3] != self.last_match:
                    self.last_match = pattern_match_idx[0][3]
                    #print('going to trigger')
                    self.strategy_params['pattern_time'] = pattern_match_idx[0]
                    self.trigger_entry(self.order_type)

    def close_existing_positions(self):
        last_candle = self.insight_book.last_tick
        for order in self.existing_orders:
            if last_candle['timestamp'] - order[1] >= self.exit_time*60:
                self.trigger_exit(order[0])


class PatternAggregator(BaseStrategy):
    def __init__(self, insight_book=None, min_tpo=None, max_tpo=None, record_metric=False):
        BaseStrategy.__init__(self, insight_book, min_tpo, max_tpo)
        self.id = 'PATTERN_AGGR'
        self.is_aggregator = True
        self.individual_strategies = []
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 10, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 15, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 20, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 30, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 45, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 60, 1, 'UP'))

        """
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 10, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 15, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 20, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 30, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 45, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "BUY", 60, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 10, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 15, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 20, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 30, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 45, 1, 'UP'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DT', "SELL", 60, 1, 'UP'))

        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 10, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 15, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 20, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 30, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 45, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "BUY", 60, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 10, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 15, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 20, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 30, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 45, 1, 'DOWN'))
        self.individual_strategies.append(PriceActionPatternStrategy(insight_book, 'DB', "SELL", 60, 1, 'DOWN'))
        """
    def evaluate(self):
        for strategy in self.individual_strategies:
            strategy.evaluate()

    def get_signal_generator_from_id(self, strat_id):
        strategy_signal_generator = None
        for signal_generator in self.individual_strategies:
            if signal_generator.id == strat_id:
                strategy_signal_generator = signal_generator
                break
        return strategy_signal_generator

