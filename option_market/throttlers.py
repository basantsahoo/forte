from entities.trading_day import TradeDateTime
from option_market.building_blocks import OptionCell, OptionIon, SpotIon, SpotCell


class FeedThrottler:
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

    def update_ion_cell(self, trade_date, current_frame, instrument, ion):
        if instrument not in self.ion_dict:
            if ion.category == 'option':
                ion_cell = OptionCell(trade_date=trade_date, timestamp=current_frame, instrument=instrument, volume_delta_mode=self.matrix.volume_delta_mode)
            else:
                ion_cell = SpotCell(trade_date=trade_date, timestamp=current_frame, instrument=instrument, volume_delta_mode=self.matrix.volume_delta_mode)
            ion_cell.update_ion(ion)
            self.ion_dict[instrument] = ion_cell
        else:
            ion_cell = self.ion_dict[instrument]
            if self.aggregation_factor > 1:
                ion.volume = ion.volume + ion_cell.ion.volume
            ion_cell.update_ion(ion)

    def apply_closing_oi(self, ion, instrument):
        closing_oi = self.matrix.closing_oi[self.matrix.current_date].get(instrument, 0)
        if closing_oi:
            ion.past_closing_oi = closing_oi
        else:  # Set closing oi as current oi becuase data is not present earlier
            ion.past_closing_oi = ion.oi
            self.matrix.closing_oi[self.matrix.current_date][instrument] = ion.oi
        return ion

    def throttle(self, instrument_data_list):

        for instrument_data in instrument_data_list:
            trade_date = instrument_data['trade_date']
            self.current_date = trade_date
            self.check_time_to_push(instrument_data['timestamp'])
            epoc_minute = TradeDateTime.get_epoc_minute(instrument_data['timestamp'])
            current_frame = int(int(epoc_minute/(self.aggregation_factor * 60)) * self.aggregation_factor * 60)
            if current_frame >= self.last_frame_start:
                instrument = instrument_data['instrument']
                if instrument == 'spot':
                    ion = SpotIon.from_raw(instrument_data['ion'])
                else:
                    ion = OptionIon.from_raw(instrument_data['ion'])
                    ion = self.apply_closing_oi(ion, instrument)
                    """
                    closing_oi = self.matrix.closing_oi[self.matrix.current_date].get(instrument, 0)
                    if closing_oi:
                        ion.past_closing_oi = closing_oi
                    else: #Set closing oi as current oi becuase data is not present earlier
                        ion.past_closing_oi = ion.oi
                        self.matrix.closing_oi[self.matrix.current_date][instrument] = ion.oi
                    """
                self.update_ion_cell(trade_date, current_frame, instrument, ion)

    def check_time_to_push(self, next_frame):
        epoc_minute = TradeDateTime.get_epoc_minute(next_frame)
        current_frame = int(int(epoc_minute / (self.aggregation_factor * 60)) * self.aggregation_factor * 60)
        if self.last_frame_start is None or self.last_frame_start < current_frame:
            # print(current_frame)
            self.push()
            self.pushed_frame_start = self.last_frame_start
            self.last_frame_start = int(current_frame)

    def push(self):
        if self.ion_dict:
            self.matrix.add_cells(self.current_date, list(self.ion_dict.values()))
            self.ion_dict = {}

class SpotFeedThrottler(FeedThrottler):
    def push(self):
        #print('SpotFeedThrottler push++++++++++')
        if self.ion_dict:
            self.matrix.add_spot_cells(self.current_date, list(self.ion_dict.values()))
            self.ion_dict = {}


class OptionFeedThrottler(FeedThrottler):
    def push(self):
        #print('OptionFeedThrottler push++++++++++')
        if self.ion_dict:
            self.matrix.add_cells(self.current_date, list(self.ion_dict.values()))
            self.ion_dict = {}
            self.matrix.generate_signal()

