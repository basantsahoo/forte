from datetime import datetime, date
import pytz
import time
from helper import utils as helper_utils
from config import nifty_future_expiry_dates, bank_nifty_future_expiry_dates

class TradeDateTime:
    def __init__(self, date_time_input, time_zone=pytz.timezone('Asia/Kolkata')):
        self.date_string = None
        self.date_time_string = None
        self.time_string = None
        self.date_time = None
        self.ordinal = None
        self.weekday = None
        self.weekday_iso = None
        self.weekday_name = None
        self.epoc_time = None
        self.epoc_minute = None
        self.day_start_epoc = None
        self.day_end_epoc = None
        self.market_start_epoc = None
        self.market_end_epoc = None
        self.month = None
        self.time_zone = time_zone
        if type(date_time_input) == str:
            self.process_string_format(date_time_input)
        elif type(date_time_input) == datetime:
            self.date_time = date_time_input
        elif type(date_time_input) == int:
            self.date_time = datetime.fromtimestamp(date_time_input)
        self.convert()

    def process_string_format(self, date_time_input):
        if self.check_string_date_format(date_time_input):
            self.date_string =  date_time_input
            self.date_time = datetime.strptime(date_time_input, '%Y-%m-%d')
        elif self.check_string_date_time_format(date_time_input):
            self.date_time = datetime.strptime(date_time_input, '%Y-%m-%d %H:%M:%S')
        else:
            raise ValueError


    def check_string_date_format(self, date_str):
        try:
            return bool(datetime.strptime(date_str, '%Y-%m-%d'))
        except:
            return False

    def check_string_date_time_format(self, date_str):
        try:
            return bool(datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S'))
        except:
            return False

    @classmethod
    def from_ordinal(cls, ordinal):
        date_time = datetime.fromordinal(ordinal)
        return cls(date_time)

    @staticmethod
    def get_epoc_minute(epoc_time):
        return int(epoc_time / 60) * 60

    def convert(self):
        self.date_string = self.date_time.strftime('%Y-%m-%d')
        self.date_time_string = self.date_time.strftime('%Y-%m-%d %H:%M:%S')
        self.time_string = self.date_time.strftime('%H:%M:%S')
        self.ordinal = self.date_time.toordinal()
        self.weekday = self.date_time.weekday()
        self.weekday_iso = self.date_time.isoweekday()
        self.weekday_name = self.date_time.strftime('%A')
        self.month = self.date_time.strftime("%B")
        self.epoc_time = int(time.mktime(time.strptime(self.date_time_string, "%Y-%m-%d %H:%M:%S")))
        self.epoc_minute = self.get_epoc_minute(self.epoc_time)
        day_start = self.date_string + " " + '00:00:00'
        market_start_time = self.date_string + " " + '9:15:00'
        market_end_time = self.date_string + " " + '15:30:00'
        self.day_start_epoc = int(time.mktime(time.strptime(day_start, "%Y-%m-%d %H:%M:%S")))
        self.market_start_epoc = int(time.mktime(time.strptime(market_start_time, "%Y-%m-%d %H:%M:%S")))
        self.market_end_epoc = int(time.mktime(time.strptime(market_end_time, "%Y-%m-%d %H:%M:%S")))


class NearExpiryWeek:
    def __init__(self, trade_date_time=None, asset="NIFTY"):
        if trade_date_time is None:
            trade_date_time = TradeDateTime(date.today())
        fut_exp_dates = self.get_asset_expiry_dates(asset)
        expiry_week_end_day = min([x.ordinal for x in fut_exp_dates if x.ordinal >= trade_date_time.ordinal])
        expiry_week_start_day = max([x.ordinal for x in fut_exp_dates if x.ordinal < trade_date_time.ordinal]) + 1

        self.start_date = TradeDateTime.from_ordinal(expiry_week_start_day)
        self.end_date = TradeDateTime.from_ordinal(expiry_week_end_day)
        next_expiry = min([x.ordinal for x in fut_exp_dates if x.ordinal > expiry_week_end_day])
        self.next_expiry_end = TradeDateTime.from_ordinal(next_expiry)
        self.moth_end_expiry = self.next_expiry_end.month != self.end_date.month

    @staticmethod
    def get_asset_expiry_dates(asset):
        if helper_utils.get_nse_index_symbol(asset) == helper_utils.get_nse_index_symbol("NIFTY"):
            sym_future_expiry_dates = nifty_future_expiry_dates
        elif helper_utils.get_nse_index_symbol(asset) == helper_utils.get_nse_index_symbol("BANKNIFTY"):
            sym_future_expiry_dates = bank_nifty_future_expiry_dates
        elif helper_utils.get_nse_index_symbol(asset) == helper_utils.get_nse_index_symbol("FINNIFTY"):
            sym_future_expiry_dates = bank_nifty_future_expiry_dates
        else:
            sym_future_expiry_dates = []
        return [TradeDateTime(x) for x in sym_future_expiry_dates]


