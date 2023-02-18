from research.queues.process_logger import ProcessLoggerMixin
from research.config import switch_log
def get_switch(manager, switch_info):
    switch_type = switch_info['type']
    if switch_type in ['DistToSL']:
        return DistToSL(manager, **switch_info)
    else:
        raise Exception("Switch is not defined")


class DistToSL(ProcessLoggerMixin):
    def __init__(self, manager, **kwargs):
        self.manager = manager
        self.id = kwargs['id']
        self.switch_eval = kwargs['switch_eval']
        self.thresholds = {'high': None, 'low': None, 'open': None, 'close': None, 'entry': None}
        self.dispatch_signal = kwargs.get("dispatch_signal", {})
        self.display_id = self.manager.strategy.id + ' Switch id== ' + repr(self.id)
        self.log_enabled = kwargs.get('switch_log', switch_log)

    def set_threshold(self, th_type, th):
        self.log("THRESHOLD  LOG", "Switch class==", self.__class__.__name__, "threshold type==", th_type, 'value ==', th, 'old value ', self.thresholds[th_type])
        self.thresholds[th_type] = th

    def get_signal(self):
        if self.dispatch_signal:
            signal = {'category': 'STRAT', 'indicator': 'EMA_BREAK_DOWN_5_ENTRY', 'strength': 1, 'signal_time': None, 'notice_time': None, 'info': self.thresholds.copy()}
            return signal
        else:
            return {}

    def evaluate(self):

        high = self.thresholds['high']
        low = self.thresholds['low']
        open = self.thresholds['open']
        close = self.thresholds['close']
        entry = self.thresholds['entry']
        res = eval(self.switch_eval)
        print(self.switch_eval, res)
        print("high====", high)
        print("close====", close)
        return res

    def flush(self):
        self.thresholds = {'high': None, 'low': None, 'open': None, 'close': None, 'entry': None}