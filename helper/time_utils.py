from datetime import datetime


def date_string_from_epoc(epoch_time):
    dt = datetime.fromtimestamp(epoch_time)
    return dt.strftime('%Y-%m-%d')


def time_string_from_epoc(epoch_time):
    dt = datetime.fromtimestamp(epoch_time)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def epoch_to_ordinal(epoch_time):
    dt = datetime.fromtimestamp(epoch_time).date()
    return dt.toordinal()

def get_epoc_minute(time_stamp):
    epoch_tick_time = time_stamp
    epoch_minute = int(epoch_tick_time / 60) * 60
    return epoch_minute

def get_epoc_from_iso_format(iso_ts):
    epoch_tick_time = int(datetime.fromisoformat(iso_ts + '+05:30').timestamp())
    return epoch_tick_time
