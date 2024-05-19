from itertools import combinations, product
from backtest_2024.analysis.binning import get_bins


def generate_range_from_bins(bins):
    ranges = []

    for i in range(len(bins) - 1):
        start = bins[i]
        end = bins[i + 1]
        ranges.append((start, end))
    return ranges



def search_grid(df_i, target, grp_list, r, filter={}):

    for key, value in filter.items():
        df_i = df_i[df_i[key] == value]
    print(len(df_i['day'].unique()))
    column_range_dict = {}
    comb_of_columns = list(combinations(grp_list, r))
    #print(comb_grps)
    for grp in grp_list:
        bins = get_bins(df_i, grp)
        ranges = generate_range_from_bins(bins)
        column_range_dict[grp] = [{'col': grp, 'low': min(rng), 'high': max(rng)} for rng in ranges ]
    #print(range_dict)
    results = []
    for comb_grp in comb_of_columns:
        print('+++++++++++++')
        print(comb_grp)
        list_of_ranges = [ column_range_dict[grp] for grp in comb_grp]
        all_possible_comb_range_of_comb_grp = list(product(*list_of_ranges))
        #print(all_possible_comb_range_of_comb_grp)
        for comb_col_range in all_possible_comb_range_of_comb_grp:
            df_tmp = df_i.copy()
            for col_range in comb_col_range:
                df_tmp = df_tmp[df_tmp[col_range['col']] >= col_range['low']]
                df_tmp = df_tmp[df_tmp[col_range['col']] < col_range['high']]
            aggregate_df = df_tmp.groupby(['strategy']).agg({target: ['count', 'mean', 'min', 'max', lambda series: len([x for x in series if x > 0])]})
            aggregate_df.columns = ['count', 'pnl_avg', 'pnl_min', 'pnl_max', '+ve']
            aggregate_df = aggregate_df.reset_index().round(3)
            aggregate_df['acc'] = aggregate_df['+ve'] / aggregate_df['count']
            aggregate_df['acc'] = aggregate_df['acc'].round(2)
            if aggregate_df.shape[0] > 0:
                aggregate_rec = aggregate_df.to_dict('records')[0]
                aggregate_rec['day_count'] = len(df_tmp['day'].unique())
                for i in range(len(comb_col_range)):
                    col_range = comb_col_range[i]
                    aggregate_rec['col_' + str(i)] = col_range['col']
                    aggregate_rec['col_' + str(i) + '_low'] = col_range['low']
                    aggregate_rec['col_' + str(i) + '_high'] = col_range['high']
                results.append(aggregate_rec)
    return results

def param_search(data_set, target, r=3, exclude_variables=[]):
    print('perform_analysis_strategies descriptive++++++++')
    cols =  [x for x in data_set.columns if x not in exclude_variables]
    data_set = data_set[cols]

    data_set['root_strategy'] = data_set['strategy'].apply(lambda x: x.split("_")[0])
    root_strategies = list(set(data_set['root_strategy'].to_list()))
    root_strategies.sort()
    final_results = []
    for root_strategy in root_strategies:
        strategies = list(set(data_set[data_set['root_strategy'] == root_strategy]['strategy'].to_list()))
        strategies.sort()
        for strategy in strategies:
            print('analysing strategy++++++++++++++++++++++++++++++++++++++++++++', strategy)
            df_i = data_set[data_set['strategy'] == strategy]
            filter = {}
            grp_list = ['day_put_profit', 'day_call_profit', 'day_total_profit', 'vol_rat', 'pcr_minus_1', 'put_call_vol_scale_diff', 'call_entrant', 'put_entrant', 'transition', 'near_put_oi_share', 'far_put_oi_share', 'near_call_oi_share', 'far_call_oi_share']
            results = search_grid(df_i, target, grp_list, r, filter={})
            final_results = final_results + results
            #group_wise_summary(report, df_i, target, 'regime', filter=filter)
    return final_results
