import sys
from pathlib import Path
project_path = str(Path(__file__).resolve().parent.parent)
print(project_path)
sys.path.insert(1, project_path)

import pandas as pd
from entities.trading_day import TradeDateTime, NearExpiryWeek
import numpy as np
from helper.utils import get_nse_index_symbol

def get_average_volume_for_day(symbol, t_day):
    def get_avg_volume_data(symbol):
        df = pd.read_csv(project_path + "/" + get_nse_index_symbol(symbol) + '_avg_volume.csv')
        return df

    def date_diff(td_1, td_2):
        return (td_2.end_date.date_time - td_1.date_time).days

    df = get_avg_volume_data(symbol)
    df['kind'] = df['instrument'].apply(lambda x: x[-2::])
    aggregate_df_1 = df.groupby(['date', 'kind'])['avg_volume'].aggregate('sum').reset_index()
    aggregate_df_1['expiry_date'] = aggregate_df_1['date'].apply(lambda x: NearExpiryWeek(TradeDateTime(x), symbol))
    aggregate_df_1['date'] = aggregate_df_1['date'].apply(lambda x: TradeDateTime(x))
    aggregate_df_1['days_to_expiry'] = aggregate_df_1.apply(lambda x: date_diff(x['date'], x['expiry_date']), axis=1)
    aggregate_df_1['month_end_expiry'] = aggregate_df_1['expiry_date'].apply(lambda x: int(x.moth_end_expiry))
    df2 = aggregate_df_1[['kind', 'avg_volume', 'days_to_expiry', 'month_end_expiry']]

    aggregate_df = df2.groupby(['kind', 'days_to_expiry', 'month_end_expiry'])['avg_volume'].aggregate('mean')
    aggregate_df = aggregate_df.reset_index()
    aggregate_df['avg_volume'] = aggregate_df['avg_volume'].apply(lambda x: np.round(x, 0))

    trade_date = TradeDateTime(t_day)
    near_expiry = NearExpiryWeek(trade_date, symbol)
    days_to_expiry = date_diff(trade_date, near_expiry)
    month_end = int(near_expiry.moth_end_expiry)
    aggregate_df_f = aggregate_df[aggregate_df['days_to_expiry'] == days_to_expiry][aggregate_df['month_end_expiry'] == month_end]
    if not aggregate_df_f.shape[0]: #For Saturday and Sunday, we don't have data
        aggregate_df_f = aggregate_df[aggregate_df['days_to_expiry'] == 6][aggregate_df['month_end_expiry'] == month_end]
    return aggregate_df_f.to_dict('records')
