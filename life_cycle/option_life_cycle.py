from helper.time_utils import get_epoc_from_iso_format, get_epoc_minute
class OptionLifeCycle:
    def __init__(self, symbol):
        self.symbol = symbol
        self.minute_data = {}

    def minute_data_input(self, minute_data):
        pass
