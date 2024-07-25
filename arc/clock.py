import time

class Clock:
    def __init__(self, interval=60):
        self.interval = interval
        self.start_frame = None
        self.current_frame = None
        self.next_frame = None
        self.frame_change_subscriptions = []

    def initialize(self, start_time):
        self.start_frame = int(start_time/self.interval)*self.interval

    def initialize_from_trade_day(self, trade_day):
        start_str = trade_day + " 09:15:00"
        start_ts = int(time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S")))
        self.initialize(start_ts)


    def set_frame(self, current_time):
        self.current_frame = int(current_time / self.interval) * self.interval
        self.next_frame = self.current_frame + self.interval

    def check_frame_change(self, input_time_stamp):
        if self.current_frame is None:
            self.set_frame(input_time_stamp)
        else:
            frame = int(input_time_stamp / self.interval) * self.interval
            if frame > self.current_frame:
                last_frame = self.current_frame
                self.set_frame(input_time_stamp)
                for change_subscription in self.frame_change_subscriptions:
                    change_subscription(last_frame, frame)


    def on_day_change(self, trade_day):
        print('*******************************on_day_change***********************')
        self.initialize_from_trade_day(trade_day)
        self.check_frame_change(self.start_frame)

    def subscribe_to_frame_change(self, callback):
        self.frame_change_subscriptions.append(callback)