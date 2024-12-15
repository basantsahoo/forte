#from infrastructure.fyers.authenication import get_access_token
#3from infrastructure.fyers.authenication_v3 import get_access_token
from infrastructure.fyers.auto_login import get_access_token
from fyers_api import fyersModel
from infrastructure.fyers.settings import app_id
from servers.server_settings import log_dir


class FyersFeed:
    """
    Fyers feed sinleton class for historical data & placing orders
    """
    _instance = None

    @staticmethod
    def getInstance():
        """Static Access Method"""
        if FyersFeed._instance is None:
            FyersFeed()
        return FyersFeed._instance

    def __init__(self):
        if FyersFeed._instance is not None:
            raise Exception ("This class is a singleton class !")
        else:
            self.fyer_access_token = None
            self.fyers = None
            FyersFeed._instance = self
            self.authenicate()

    def authenicate(self):
        self.fyer_access_token = get_access_token()
        self.fyers = fyersModel.FyersModel(client_id=app_id, token=self.fyer_access_token, log_path=log_dir)

    def get_hist_data(self, symbol,start_t,end_t):
        hist_data = {"symbol": symbol, "resolution": "1", "date_format": "0", "range_from": start_t,
                "range_to": end_t, "cont_flag": "1"}
        hist = self.fyers.history(hist_data)
        return hist
