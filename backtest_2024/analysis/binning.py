from pandas.core.dtypes.common import (
    is_integer
)
import numpy as np

bin_dict = {
    'day_put_profit': [-2.5, -2, -1.5, -1.4, -1.3, -1.2, -1.1, -1, -0.9, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2,
                       -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
}


def get_bins(df_i, grp, q=20):
    quantiles = np.linspace(0, 1, q + 1) if is_integer(q) else q
    x = df_i[grp].to_list()
    x_np = np.asarray(x)
    x_np = x_np[~np.isnan(x_np)]
    bins = bin_dict.get(grp, [])
    bins = bins or np.quantile(x_np, quantiles)
    return bins
