from dynamics.profile.volume_profile import VolumeProfileService
import numpy as np
from itertools import compress
import pandas as pd
from db.market_data import get_daily_tick_data
from db.db_engine import get_db_engine
from config import default_symbols
import helper.utils as helper_utils
"""
# for connecting to fyers for historical data
from data_feed.historical_data import HistoricalDataFetcher
hist_fetcher = HistoricalDataFetcher()
"""

 #['NSE:NIFTY50-INDEX']

def get_last_calc_date(symbol):
    engine = get_db_engine()
    conn = engine.connect()
    qry = """select distinct date as pending from minute_data where symbol = '{0}'
            and date not in (
            select date  from daily_profile where symbol = '{0}'
            ) and YEAR(date) >=2022""".format(symbol)
    df = pd.read_sql_query(qry, con=conn)
    pending_dates = df['pending'].to_list() if df['pending'].to_list() else []
    #print(pending_dates)
    conn.close()
    return pending_dates


def process(trade_days=[], symbols=[], debug=False):
    engine = get_db_engine()
    conn = engine.connect()
    #print(default_symbols)
    if len(symbols) == 0:
        symbols = [helper_utils.get_nse_index_symbol(symbol) for symbol in default_symbols]

    for symbol in symbols:
        tmp_trade_days = trade_days
        if len(tmp_trade_days) == 0:
            tmp_trade_days = get_last_calc_date(symbol)
        IDX = 0
        for trade_day in tmp_trade_days:
            IDX += 1
            df = get_daily_tick_data(symbol, trade_day)
            df['symbol'] = symbol
            hist_data = df.to_dict('records')
            #print(hist_data)
            if hist_data:
                if IDX == 1:
                    #print(hist_data)
                    pass

                try:
                    start_epoch_tick_time = hist_data[0]['timestamp']
                    processor = VolumeProfileService()
                    processor.process_hist_data(hist_data)
                    processor.day_setup(start_epoch_tick_time)
                    processor.calculateProfile()
                    data = processor.market_profile
                    #print(data)
                    if debug: #Just display
                        """
                        print(data['print_matrix'].shape)
                        print(data['price_bins'].shape)
                        print(data)
                        print(processor.tpo_brackets)
                        """
                        print_matrix_t = np.transpose(data['print_matrix'])
                        finals = []
                        for itr in range(print_matrix_t.shape[0]):
                            tpo_array = print_matrix_t[itr].A1
                            #print(tpo_array)
                            price = format(round(data['price_bins'][itr],2), "."+str(2)+"f")
                            #print(price)
                            total = int(sum(tpo_array))
                            #print(total)
                            tpos_occured = list(compress(processor.tpo_letters, tpo_array))
                            tpo_str = ",".join(tpos_occured)
                            finals.append([price, total, tpo_str])
                        finals.reverse()

                        for i in finals:
                            print(str(i[0]) + ' | ' + str(i[1]).rjust(2,' ') + ' | '  + i[2])
                    else:	# store in DB
                        rec = {
                            'symbol':symbol,
                            'date':trade_day,
                            'open': data['open'],
                            'high': data['high'],
                            'low': data['low'],
                            'close': data['close'],
                            'volume': data.get('volume', 0),
                            'poc_price': data['poc_price'],
                            'poc_idx': data['poc_idx'],
                            'poc_len': data['poc_len'],
                            'va_l_idx': data['value_area'][0],
                            'va_h_idx': data['value_area'][1],
                            'va_l_p': data['value_area_price'][0],
                            'va_h_p': data['value_area_price'][1],
                            'balance_target': data['balance_target'],
                            'below_poc': data['below_poc'],
                            'above_poc': data['above_poc'],
                            'ib_l': data['initial_balance'][0],
                            'ib_h': data['initial_balance'][1],
                            'ib_l_acc': data['initial_balance_acc'][0],
                            'ib_h_acc': data['initial_balance_acc'][1],
                            'ib_l_idx': data['initial_balance_idx'][0],
                            'ib_h_idx': data['initial_balance_idx'][1],
                            'ext_low': data['profile_dist']['ext_low'],
                            'ext_high': data['profile_dist']['ext_high'],
                            'sin_print': data['profile_dist']['sin_print'],
                            'le_f': data['profile_dist'].get('le_f', None),
                            'he_f': data['profile_dist'].get('he_f', None),
                            'sp_f': data['profile_dist'].get('sp_f', None),
                            'h_a_l': data['h_a_l'],
                            'ht': data['ht'],
                            'lt': data['lt']
                        }
                        #print(rec)
                        df = pd.DataFrame([rec])
                        df.to_sql('daily_profile', conn, if_exists="append", index=False)
                except Exception as e:
                    print(trade_day, symbol)
                    print(e)
    conn.close()

def run():
    #process(trade_days=["2024-04-15"])
    process()

#run()



