from backtest_2024.analysis.descriptive_analysis import group_wise_summary
from backtest.settings import reports_dir
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd


def load_back_test_results():
    df = pd.read_csv(reports_dir + 'weekly_metrices_t.csv')
    return df


def print_summary(df_i):
    with PdfPages(reports_dir + 'weekly_descrpitive_analysis.pdf') as report:
        filter = {}
        group_wise_summary(report, df_i, 'abs_weekly_close_to_close', 'lw_p_shape', filter=filter)
        # Conclusion : No mean difference in last week shape
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'open_type', filter=filter)
        # Conclusion : ABOVE VA and Below VA has higher mean, Gap down has lower mean
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'day_0_p_shape', filter=filter)
        # Conclusion : B shape has higher mean,
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'day_0_w_poc_dir', filter=filter)
        # Conclusion : 1  has higher mean,
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'day_1_p_shape', filter=filter)
        # Conclusion : B shape has higher mean,
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'day_1_w_poc_dir', filter=filter)
        # Conclusion : 1  has higher mean,
        filter = {'day_0_w_poc_dir':1}
        group_wise_summary(report, df_i, 'weekly_close_to_close', 'day_1_w_poc_dir', filter=filter)
        # Conclusion : 1  has higher mean,

def basic_statistics(df):
    print("Total no of days pattern matched ====", len(df['day'].unique()))
    print("Total no of  pattern matched ====", len(df['entry_time'].unique()))
    print("Trades per day", len(df['entry_time'].unique())/len(df['day'].unique()))
    print("Premium earned", df['realized_pnl'].sum())


def get_cleaned_results():
    df = load_back_test_results()
    df['strategy'] = 'test'
    df['abs_weekly_close_to_close'] = df['weekly_close_to_close'].apply(lambda x : abs(x))
    df = df[df['abs_weekly_close_to_close'] < 0.06]

    return df


def run():
    df = get_cleaned_results()
    print_summary(df)

