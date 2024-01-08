import pandas as pd
from entities.trading_day import TradeDateTime

def convert_to_option_ion(feed):
    feed['ion'] = '|'.join([str(feed['close']), str(feed['volume']), str(feed['oi'])])
    return feed


def convert_to_spot_ion(feed):
    feed['ion'] = '|'.join([str(feed['open']), str(feed['high']), str(feed['low']), str(feed['close'])])
    return feed


def convert_hist_option_feed(feed, trade_day):
    symbol = feed['symbol']
    recs = feed['data']
    f_recs = []
    for rec in recs:
        fdd = {
            'instrument': str(rec['strike']) + "_" + rec['type'],
            'timestamp': TradeDateTime.get_epoc_minute(rec['ltt']),
            'trade_date': trade_day,
            'close': rec['ltp'],
            'volume': rec['volume'],
            'oi': rec['oi'],
            'asset': symbol
        }
        f_recs.append(fdd)

    b_df = pd.DataFrame(f_recs)
    b_df.sort_values(by=['timestamp'])
    hist_recs = b_df.to_dict("records")
    return {'feed_type': 'option', 'asset': symbol, 'data': hist_recs}


def convert_hist_spot_feed(feed, trade_day):
    symbol = feed['symbol']
    recs = feed['hist']
    f_recs = []
    for ts, rec in recs.items():
        fdd = {
            'instrument': 'spot',
            'timestamp': TradeDateTime.get_epoc_minute(int(ts)),
            'trade_date': trade_day,
            'open': rec['open'],
            'high': rec['high'],
            'low': rec['low'],
            'close': rec['ltp'],
            'volume': rec['volume'],
            'asset': symbol
        }
        f_recs.append(fdd)

    b_df = pd.DataFrame(f_recs)
    b_df.sort_values(by=['timestamp'])
    hist_recs = b_df.to_dict("records")
    return {'feed_type': 'spot', 'asset': symbol, 'data': hist_recs}
