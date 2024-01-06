def convert_to_option_ion(feed):
    feed['ion'] = '|'.join([str(feed['close']), str(feed['volume']), str(feed['oi'])])
    return feed

def convert_to_spot_ion(feed):
    feed['ion'] = '|'.join([str(feed['open']), str(feed['high']), str(feed['low']), str(feed['close'])])
    return feed
