from entities.base import Signal
from entities.trading_day import TradeDateTime


class TimeBook:
    def __init__(self, market_book, interval=1):
        self.market_book = market_book
        self.interval = interval
        self.start_frame = None
        self.current_frame = None
        self.next_frame = None

    def set_frame(self, current_time):
        self.current_frame = int(current_time / self.interval) * self.interval
        self.next_frame = self.current_frame + self.interval

    def check_frame_change(self, input_time_stamp):
        if self.current_frame is None:
            self.set_frame(input_time_stamp)
        else:
            frame = int(input_time_stamp / self.interval) * self.interval
            if frame > self.current_frame:
                d_t = TradeDateTime(self.current_frame).weekday_name + "_" + TradeDateTime(self.current_frame).time_string[:-3]
                d_t = d_t.upper().replace(":", "_")

                signal = Signal(asset='GLOBAL', category='TIME_SIGNAL', instrument=None,
                                indicator=d_t, strength=1, signal_time=self.current_frame,
                                notice_time=self.current_frame, signal_info={}, period="1min")
                #print('time_signal=====', signal.__dict__)
                self.market_book.pattern_signal('GLOBAL', signal)
                self.set_frame(input_time_stamp)
