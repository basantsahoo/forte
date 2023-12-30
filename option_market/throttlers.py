from entities.trading_day import TradeDateTime
from option_market.building_blocks import Cell, Ion


class TickPriceThrottler:
    def __init__(self, matrix, feed_speed, throttle_speed=0):
        self.matrix = matrix
        self.feed_speed = feed_speed if feed_speed > 1 else 1
        self.throttle_speed = throttle_speed if throttle_speed > 1 else 1
        self.aggregation_factor = self.throttle_speed/feed_speed
        #print(self.aggregation_factor)
        self.pushed_frame_start = None
        self.last_frame_start = None
        self.ion_dict = {}
        self.current_date = None

    def update_ion_cell(self, current_frame, instrument, ion):
        if instrument not in self.ion_dict:
            ion_cell = Cell(timestamp=current_frame, instrument=instrument)
            ion_cell.update_ion(ion)
            self.ion_dict[instrument] = ion_cell
        else:
            ion_cell = self.ion_dict[instrument]
            if self.aggregation_factor > 1:
                ion.volume = ion.volume + ion_cell.ion.volume
            ion_cell.update_ion(ion)



    def throttle(self, instrument_data_list):
        for instrument_data in instrument_data_list:
            trade_date = instrument_data['trade_date']
            self.current_date = trade_date
            epoc_minute = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            current_frame = int(int(epoc_minute/(self.aggregation_factor * 60)) * self.aggregation_factor * 60)
            if self.last_frame_start != current_frame:
                #print(current_frame)
                self.push()
                self.pushed_frame_start = self.last_frame_start
                self.last_frame_start = current_frame
            instrument = instrument_data['instrument']
            ion = Ion.from_raw(instrument_data['ion'])
            self.update_ion_cell(current_frame, instrument, ion)

    def push(self):
        self.matrix.add_cells(self.current_date, list(self.ion_dict.values()))
        self.ion_dict = {}
        self.matrix.generate_signal()


"""
class PriceThrottler:
    def __init__(self, matrix, feed_speed, throttle_speed=0):
        self.matrix = matrix
        self.feed_speed = feed_speed if feed_speed > 1 else 1
        self.throttle_speed = throttle_speed if throttle_speed > 1 else 1
        self.aggregation_factor = self.throttle_speed/feed_speed
        #print(self.aggregation_factor)
        self.pushed_frame_start = None
        self.last_frame_start = None
        self.ion_dict = {}
        self.current_date = None

    def update_ion_cell(self, current_frame, instrument, ion):
        if instrument not in self.ion_dict:
            ion_cell = Cell(timestamp=current_frame, instrument=instrument)
            ion_cell.update_ion(ion)
            self.ion_dict[instrument] = ion_cell
        else:
            ion_cell = self.ion_dict[instrument]
            if self.aggregation_factor > 1:
                ion.volume = ion.volume + ion_cell.ion.volume
            ion_cell.update_ion(ion)



    def throttle(self, instrument_data_list):
        for instrument_data in instrument_data_list:
            trade_date = instrument_data['trade_date']
            self.current_date = trade_date
            epoc_minute = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            current_frame = int(int(epoc_minute/(self.aggregation_factor * 60)) * self.aggregation_factor * 60)
            if self.last_frame_start != current_frame:
                #print(current_frame)
                self.push()
                self.pushed_frame_start = self.last_frame_start
                self.last_frame_start = current_frame
            instrument = instrument_data['instrument']
            ion = Ion.from_raw(instrument_data['ion'])
            self.update_ion_cell(current_frame, instrument, ion)

    def push(self):
        self.matrix.add_cells(self.current_date, list(self.ion_dict.values()))
        self.ion_dict = {}
        self.matrix.generate_signal()
"""
